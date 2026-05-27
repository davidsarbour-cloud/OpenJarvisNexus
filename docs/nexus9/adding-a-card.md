# Adding a new world card

Worked example: adding a **GITHUB ACTIVITY** card to the Cyberdeck
world that shows your commit count today + last commit message.

The whole loop is 4 files, ~80 lines of code, and the result auto-
pushes over WS without you wiring any polling.

## 1. Define the data source (backend)

Pick the cheapest source you can. For "commits today" we can shell out
to `git`. Drop a function in `backend/world_cards_router.py`:

```python
def _github_activity_snapshot() -> dict:
    """Commits authored today on the current branch + last subject."""
    import subprocess
    try:
        # Today's commits
        count = subprocess.check_output(
            ["git", "log", "--since=midnight", "--author=David", "--oneline"],
            text=True, cwd=str(BACKEND_DIR.parent),
        ).strip().split("\n")
        n = len([line for line in count if line])
        # Last subject (always have one)
        last = subprocess.check_output(
            ["git", "log", "-1", "--format=%s"],
            text=True, cwd=str(BACKEND_DIR.parent),
        ).strip()
        status = "active" if n > 0 else "standby"
        return {
            "status": status,
            "metrics": [
                {"label": "commits today",  "value": str(n)},
                {"label": "last",           "value": last[:40] + "…" if len(last) > 40 else last},
            ],
        }
    except Exception:
        return {"status": "standby", "metrics": [{"label": "error", "value": "—"}]}
```

Add the key to the response payload in the existing
`world_cards_snapshot()` function:

```python
@router.get("/v1/world/cards/snapshot")
def world_cards_snapshot() -> dict[str, Any]:
    return {
        # ...existing keys...
        "github_activity": _github_activity_snapshot(),
        "generated_at": datetime.now().isoformat(),
    }
```

That's the entire backend side. The existing `snapshot/world-cards`
publisher (every 6 s) will already pick this up and broadcast it —
no extra wiring.

## 2. Extend the frontend type (frontend)

`frontend/src/lib/apiLive.ts` — add the new key to the snapshot type:

```ts
export interface WorldCardsSnapshotData {
  // ...existing keys...
  github_activity: WorldCardSnapshot;
  generated_at:    string;
}
```

`tsc` now knows the shape; the existing `FunctionalSatellites.LiveSatellite`
component is generic on the snapshot key, so no other type changes
needed.

## 3. Register the card in the target world

`frontend/src/pages/WorldCyberdeckPage.tsx`:

```tsx
import { Github } from 'lucide-react';   // or any LucideIcon
// ...existing imports
const GithubActivity = () =>
  <LiveSatellite title="GITHUB ACTIVITY" colorKey="cyberdeck" snapshotKey="github_activity" />;

type CardType =
  | 'signal' | 'load' | 'beacon' | 'amplifier' | 'airesearch'
  | 'gpu' | 'errorlog' | 'ratelimits' | 'telegram' | 'routing'
  | 'github';   // ← new

const CARD_REGISTRY: Record<CardType, CardDef> = {
  // ...existing entries
  github: {
    label: 'GITHUB ACTIVITY',
    sub:   'Commits today + last subject',
    icon:  Github,
    Card:  GithubActivity,
  },
};
```

That's it — `<WorldShell>` discovers the new card from the registry,
the bottom ADD-CARD bar renders the new button automatically, and
clicking it adds the card to whichever dock has fewer cards already.

## 4. Validate

```pwsh
# Backend reload (uvicorn picks up the change on save)
curl http://localhost:8000/v1/world/cards/snapshot | jq .github_activity

# Frontend TS check
cd frontend && npx tsc -b --noEmit

# Live: refresh /world/cyberdeck, open ADD CARD, click GITHUB ACTIVITY
# The card appears and starts ticking (6s cadence via WS push).
```

## Patterns to copy vs avoid

**Copy**:
- Use `LiveSatellite` when the card just displays metrics from the
  world-cards snapshot. It auto-binds to the WS topic.
- Use `NamedSatellite` for placeholder cards (no live data yet) — they
  show a styled "STANDBY" state, useful while building.
- Return `{ status, metrics: [{label, value}, …] }` from your snapshot
  fetcher. The render component is shape-validated against `WorldCardSnapshot`.

**Avoid**:
- Don't add a new HTTP poll endpoint just for one card. Extend
  `/v1/world/cards/snapshot` instead — one round-trip serves all.
- Don't write a custom React component if `LiveSatellite` covers it.
  ~100 lines of duplicated CSS is the trap WorldShell was built to
  prevent.
- Don't put per-second-changing data in a `world-cards` topic — its
  cadence is 6 s. For 1–2 s cadence, add a dedicated topic in
  `backend/snapshot_publisher.py` (see how `snapshot/system-metrics`
  is wired) and have a separate fetcher in `apiLive.ts`.

## Adding a card with its own snapshot cadence

If the data really must update faster than 6 s (system metrics, real-
time price feeds), do this instead:

1. Backend — add a new publisher entry in `start_publishers()` with
   the desired cadence:
   ```python
   ("snapshot/github-rate",  _github_rate_snapshot,  2.0),
   ```
2. Frontend — call your own typed `fetchGithubRate()` and pass
   `wsTopic: 'snapshot/github-rate'` to `useLiveMetric`:
   ```ts
   const { data } = useLiveMetric(
     fetchGithubRate,
     { intervalMs: 2000, wsTopic: 'snapshot/github-rate' },
   );
   ```

Same singleton bus → still O(1) sockets no matter how many topics.

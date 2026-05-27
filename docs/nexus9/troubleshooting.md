# Troubleshooting

Triage for the issues that have actually bitten David on this machine.
Sorted by symptom.

## "The HUD shows MOCK data and no live updates"

The RightPanel's badge in the top-right reads either **WS LIVE**,
**HTTP LIVE**, or **MOCK**. MOCK means both the WebSocket and the HTTP
poll failed.

```pwsh
# Is the backend actually reachable?
curl http://localhost:8000/v1/info
# 200 → backend up · connection refused → uvicorn not running
```

If 200 but you still see MOCK:

```pwsh
# Is the snapshot publisher actually publishing?
curl "http://localhost:8000/v1/events/recent?limit=5"
# Look for source="snapshot/agents" or similar.
# Empty → uvicorn hasn't started its _lifespan task → restart it.
```

If the events look fine over HTTP but the SPA still doesn't get them
live, the WebSocket itself is the problem:

- Open devtools → Network → WS filter → look for `/ws/events`.
- Status `Switching Protocols` (101) = healthy.
- Status `Pending` forever = a proxy / firewall is eating the upgrade
  (Windows Defender? Tauri webview misconfig?).
- Status `Failed` with a CORS hint = your origin isn't in the
  allow-list (see CORS section below).

## "The splash overlay (NexusBootIntro) plays every refresh"

Two possible causes:

1. **Backend is restarting on every reload.** Check the uvicorn log —
   does it print `[Nexus9] Startup complet` on every page refresh?
   That means `--reload` is watching too aggressively. The
   `backend/main.py` reload-include pattern should be narrow, not
   `--reload-dir .`. Limit reload to source files only.

2. **localStorage is being cleared.** Open devtools → Application →
   localStorage → look for `nexus9.intro.boot-id`. If it disappears
   on refresh, you're in incognito or a Tauri webview with
   ephemeral storage. Either expected (incognito) or a Tauri config
   bug (`tauri.conf.json` → set persistent storage).

To force-replay the intro on demand:

```js
localStorage.removeItem('nexus9.intro.boot-id');
location.reload();
```

## "CORS error in the console"

```text
Access to fetch at 'http://192.168.1.42:8000/v1/info' from origin
'http://192.168.1.42:5173' has been blocked by CORS policy
```

The IP isn't in the allow-list. Either:

- Set `NEXUS9_CORS_ORIGINS` in `backend/.env`:
  ```ini
  NEXUS9_CORS_ORIGINS=http://192.168.1.42:5173,http://192.168.1.42:8000
  ```
  Restart uvicorn. Log line `[CORS] N allowed origins (+M from env)`
  confirms it picked them up.

- Or use `localhost`/`127.0.0.1` instead of the LAN IP — those are
  in the default allow-list.

`allow_origins=["*"]` is **not** an option since this fork uses
`allow_credentials=True`; the CORS spec forbids the combination.

## "Port 8000 / 5173 / 11434 already in use"

```pwsh
# Find what's holding the port (Windows)
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
Get-Process -Id <PID> | Select-Object Name, Path
```

Common culprits:

- **8000** held by a stale uvicorn from a previous run, or by the
  `nexus_backend` Docker container if you ran `docker compose up`
  earlier. Stop the container: `docker stop nexus_backend`.
- **5173** held by another Vite dev server (rare; usually means an
  IDE auto-launched it). Kill it or use `npm run dev -- --port 5174`.
- **11434** held by a system Ollama. Don't double-start — only one
  `ollama serve` per machine.

## "Ollama is up but qwen3:14b is slow / falls off GPU"

Symptom: first chat takes 8+ seconds, subsequent are fast. Or token
rate drops from ~40 tok/s to ~3 tok/s (CPU fallback).

Fixes:

1. **`OLLAMA_NUM_CTX`** in `backend/.env` should be **4096**, not
   the default 8192. 8192 spills the model partially to CPU on a
   4070 SUPER.
2. **Keep-alive**: the Ollama heartbeat (every 4 min between 7h–23h)
   keeps the model in VRAM. If you're outside that window the first
   request reloads ~6 s. Override the schedule in
   `backend/main.py` `_ollama_heartbeat()` if your day-night cycle
   is different.
3. **Don't disable qwen3 thinking** — the model is configured with
   thinking enabled for code/research quality. Trying to suppress it
   destroys answer quality (see memory:
   `feedback_nexus9_ollama_tuning.md`).

```pwsh
# Live check
curl http://localhost:11434/api/show -d '{"name": "qwen3:14b"}' | jq .details
# parameter_size: "14B" — confirms the right model is loaded
```

## "pytest fails with ModuleNotFoundError: trimesh / playwright / fastapi"

You're using the wrong venv. The repo has two:

```text
C:\OpenJarvisNexus\.venv               ← lightweight, for tooling
C:\OpenJarvisNexus\backend\.venv       ← full runtime, has every dep
```

```pwsh
# Always run backend tests with backend/.venv:
C:\OpenJarvisNexus\backend\.venv\Scripts\python.exe -m pytest backend/

# pre-commit hooks also need to be invoked via the backend venv
# (or pip install ruff in the .venv at the repo root)
```

The new tests (`test_boot_endpoint.py`, `test_snapshot_publisher.py`)
gracefully skip when those heavy deps aren't installed, so they're
green in the minimal-CI job and run for real locally.

## "Frontend tests pass locally but fail in CI"

Common cause: an unstaged file (often a new component) referenced by
the code you committed. CI checks out only what's in git; your local
working tree has the unstaged file masking the broken import.

```pwsh
git status --short
# look for ?? frontend/src/components/.../NewCard.tsx
# if WorldXPage imports it, you need to git add + commit.
```

Also runs the prod build, which is stricter than `npm run dev`. If
your local `npm run dev` is fine but `npm run build` fails locally
too, that's the bug to chase.

## "npm run build fails with PWA precache error"

```text
Configure "workbox.maximumFileSizeToCacheInBytes" to change the limit
  the default value is 2 MiB.
Assets exceeding the limit:
  - world/vault.png is 6.02 MB, …
```

A heavy PNG is in the precache glob. The fix is already shipped:
`vite.config.ts` `workbox.globIgnores` skips `world/*.png` and
`agents/*.png` (the WebP versions are precached instead). If you
added a new heavy asset, extend that ignore list — don't raise the
limit, because that bloats the SW cache and slows first install.

## "Vite dev shows a blank screen after a refactor"

Usually a HMR boundary that crossed a circular import. Check the
browser console first; if it just says "ChunkLoadError: Failed to
fetch dynamically imported module", clear `frontend/.vite/` and
restart:

```pwsh
Remove-Item -Recurse frontend/.vite
cd frontend
npm run dev
```

## "Docker desktop says nexus_chromadb is unhealthy"

Probably hit a port conflict (8001) or a corrupted volume.

```pwsh
docker logs nexus_chromadb --tail 50
# look for "address already in use" or "DB corruption"

# Nuclear option (loses local vectors, will re-index on next boot):
docker compose down chromadb
docker volume rm openjarvisnexus_nexus_chroma_data
docker compose up -d chromadb
```

If you re-index, expect a 30–60 s warm-up while the embedding model
pulls every brain note.

## "The brain (vault) is empty / no notes in /brain"

The vault root is **not** `backend/vault_notes/`. It's
`backend/BRAIN/BRAIN/` (yes, nested). If you mistakenly created
`vault_notes/`, the auto-indexer never sees it.

```pwsh
ls backend/BRAIN/BRAIN/ -Recurse -Filter *.md | Measure-Object
# expect N > 0
```

Trigger a re-index manually:

```bash
curl -X POST http://localhost:8000/v1/brain/reindex
```

## "Pre-commit hook fails / fights me on every commit"

The pre-commit chain runs `ruff` (auto-fixes!) + `jscpd` (>5%
duplication = block).

- **Ruff auto-fix**: after the first failure, re-stage the fixed files
  and re-commit. Never `--amend`.
- **jscpd block**: the most common cause is a half-staged refactor —
  the hook stashes your unstaged changes, runs against the staged
  state, and sees duplication that your local working tree doesn't
  have. Stage the full refactor (or split into logically self-
  contained commits) and re-try.
- **Never bypass with `--no-verify`** unless you've been explicitly
  told to. See memory: `feedback_minimal_changes.md`.

## "GitHub Actions workflow `Deploy Documentation` fails"

The mkdocs build succeeds; the deploy step fails with
`HttpError: Not Found`. This is a one-time UI toggle in the repo
settings, not a code fix:

> Settings → Pages → Source → "GitHub Actions" (radio button)

After that the next push will deploy. Site URL is
<https://davidsarbour-cloud.github.io/OpenJarvisNexus/>.

## When nothing works

```pwsh
# Full reset (nuclear). Loses local Docker volumes + node_modules.
docker compose down -v
Remove-Item -Recurse -Force frontend/node_modules
Remove-Item -Recurse -Force frontend/dist
Remove-Item -Recurse -Force backend/__pycache__

# Then: backend venv recreate
Remove-Item -Recurse -Force backend/.venv
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Frontend
cd ../frontend
npm install

# Re-launch
cd ..
.\START_ALL.bat
```

If that doesn't fix it, capture the backend startup log (everything
between `[CORS]` and `Startup complet`) and the first 50 lines of the
browser devtools console — those two together name the layer that's
broken in 9 cases out of 10.

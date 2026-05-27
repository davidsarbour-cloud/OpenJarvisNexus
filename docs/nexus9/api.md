# API reference

Catalog of every endpoint the SPA actually calls. Auto-generated
Swagger lives at <http://localhost:8000/docs> with full schemas; this
page is the human-readable index with curl examples you can paste.

> All examples assume `BASE=http://localhost:8000`. Replace with your
> LAN IP or tunnel host as needed (CORS allow-list permitting).

## Identity & boot

### `GET /v1/info`

Server identity. Used by the SPA on first paint.

```bash
curl $BASE/v1/info
# { "name": "Nexus9 Backend", "version": "9.0.0", "phase": 4,
#   "model": "claude-haiku-4-5", "host": "nexus_backend" }
```

### `GET /v1/boot/info`

Per-uvicorn-process uuid. The frontend `NexusBootIntro` keys off
this to decide whether to replay the splash overlay. New uuid on every
backend restart → splash plays once at the next page load.

```bash
curl $BASE/v1/boot/info
# { "boot_id": "af6513c4d9cd46db83f0218f47be14e1",
#   "started_at": "2026-05-27T04:42:47+00:00" }
```

## Live data (WS-pushed snapshots)

Each of these has a matching `snapshot/<topic>` event broadcast over
`/ws/events` at the cadence noted. `useLiveMetric({ wsTopic })` on the
frontend uses the HTTP endpoint for the first paint + 60s fallback only.

| Endpoint | WS topic | Cadence | Purpose |
|---|---|---|---|
| `GET /v1/agents` | `snapshot/agents` | 8 s | Agent roster + status + provider/model |
| `GET /v1/budget` | `snapshot/budget` | 8 s | Per-session Claude cost + budget guard |
| `GET /v1/models` | `snapshot/models` | 30 s | Claude + Ollama model picker (filters out embed-only models) |
| `GET /v1/crew/jobs` | `snapshot/jobs` | 6 s | CrewAI job queue |
| `GET /v1/daily/status` | `snapshot/scheduled` | 60 s | APScheduler job list with next-run timestamps |
| `GET /v1/system/metrics` | `snapshot/system-metrics` | 2 s | CPU / RAM / VRAM / net |
| `GET /v1/health/deep` | `snapshot/health` | 10 s | Per-service health checks |
| `GET /v1/docker/containers` | `snapshot/docker` | 8 s | `nexus_*` container roster |
| `GET /v1/chromadb/stats` | `snapshot/chromadb` | 12 s | Vector store stats |
| `GET /v1/world/cards/snapshot` | `snapshot/world-cards` | 6 s | 13-key payload for every world card |

### `GET /v1/agents` example

```bash
curl $BASE/v1/agents | jq .
# {
#   "agents": [
#     { "id": "jarvis",  "name": "JARVIS",  "status": "online",  "role": "Orchestrator", "provider": "anthropic", "model": "claude-haiku-4-5", "description": "..." },
#     { "id": "ultron",  "name": "ULTRON",  "status": "idle",    "role": "Defense",      "provider": "anthropic", "model": "claude-sonnet-4-6" },
#     { "id": "qwen",    "name": "QWEN",    "status": "online",  "role": "Reasoner",     "provider": "ollama",    "model": "qwen3:14b" },
#     ...
#   ]
# }
```

### `GET /v1/world/cards/snapshot` example

```bash
curl $BASE/v1/world/cards/snapshot | jq 'keys'
# [
#   "approval_queue", "container_logs", "daily_digest", "disk_usage",
#   "error_log", "generated_at", "gpu_temp", "model_routing",
#   "morning_brief", "orphan_alert", "stl_output", "telegram_activity",
#   "token_budget", "vault_growth"
# ]

curl $BASE/v1/world/cards/snapshot | jq '.gpu_temp'
# { "status": "active",
#   "metrics": [
#     { "label": "temp",  "value": "62°C" },
#     { "label": "util",  "value": "78%"  },
#     { "label": "vram",  "value": "9.3 GB / 12 GB" }
#   ] }
```

## Chat

### `POST /v1/chat/completions`

The main entry point. Routes between Claude and Ollama based on:
- the `!claude` / `!local` prefix (overrides),
- the message content (heuristic in `chat_router.should_use_claude()`),
- the budget guard (`BUDGET_MAX_USD` in `.env`).

```bash
curl -X POST $BASE/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Liste les containers Docker en cours",
    "stream": false
  }' | jq .
# {
#   "choices": [{ "message": { "content": "..." } }],
#   "model": "qwen3:14b",                   ← Ollama branch
#   "usage": { "input_tokens": 412, "output_tokens": 87 }
# }
```

When the budget is exhausted the response is structurally identical but
`model: "bloqué"` and the content is the budget-block message. The
frontend `SkillActivator` checks for this and renders a warning UI.

## Skills

### `GET /v1/skills/list`

Returns the catalog injected into the chat system prompt every turn.

```bash
curl $BASE/v1/skills/list | jq '.skills | length'
# 13

curl $BASE/v1/skills/list | jq '.skills[] | {name, kind, description}'
```

### `POST /v1/skills/get`

Load a single skill's protocol (Hermes) or step list (TOML).

```bash
curl -X POST $BASE/v1/skills/get \
  -H "Content-Type: application/json" \
  -d '{"name": "systematic-debugging"}' | jq .
```

## Forge (STL pipeline)

### `POST /v1/forge/mission`

Trigger a STL mission inline. Used by the `QuickForgeCard` in the
Forge world dashboard.

```bash
curl -X POST $BASE/v1/forge/mission \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "dragon en posture héroïque, base hexagonale, 150mm",
    "engine": "auto",
    "target_size_mm": 150
  }' | jq .
# { "mission_id": "M-20260527-014532", "status": "queued",
#   "engine": "meshy", "eta_seconds": 240 }
```

### `GET /v1/forge/mission/{id}`

```bash
curl $BASE/v1/forge/mission/M-20260527-014532 | jq .
# { "mission_id": "...", "status": "complete",
#   "stl_path": "C:/.../forge_output/dragon_M-…stl",
#   "preview_png": "..." }
```

## Events / WebSocket

### `WS /ws/events`

Long-lived. Sends one frame on connect:

```json
{
  "type":        "hello",
  "subscribers": 4,
  "history":     [/* last 50 events */]
}
```

Then a frame per published event:

```json
{
  "type": "event",
  "data": {
    "ts":     "2026-05-27T04:42:47.123+00:00",
    "level":  "info",
    "source": "snapshot/agents",
    "msg":    "snapshot",
    "data":   { /* the actual payload */ }
  }
}
```

Plus periodic `{ "type": "ping", "ts": ... }` keepalives.

### `GET /v1/events/recent?limit=N`

Replay the last N events (max 200). Useful for HTTP-only debugging
without opening a WebSocket.

```bash
curl "$BASE/v1/events/recent?limit=20" | jq '.events[].source' | sort -u
# "JARVIS"
# "NEXUS9"
# "SCHEDULER"
# "SKILL"
# "snapshot/agents"
# "snapshot/budget"
# "snapshot/jobs"
# ...
```

### `POST /v1/events/publish`

Inject a custom event into the hub. Used by the `SkillActivator`
modal on successful manual skill activation.

```bash
curl -X POST $BASE/v1/events/publish \
  -H "Content-Type: application/json" \
  -d '{
    "level":  "info",
    "source": "MANUAL",
    "msg":    "deploy script finished",
    "note":   "02_Daily/2026-05-27/deploy-log.md"
  }'
# { "ok": true, "delivered": 3, "subscribers": 4 }
```

`note` is optional; if present the RightPanel alert row becomes
clickable and opens the path via `obsidian://open?vault=BRAIN&file=…`.

## Brain / vault

### `POST /v1/vault/query`

Vector + keyword hybrid search over the indexed Obsidian vault.

```bash
curl -X POST $BASE/v1/vault/query \
  -H "Content-Type: application/json" \
  -d '{"query": "stl etsy listing", "limit": 5}' | jq .
```

### `GET /v1/brain/stats`

```bash
curl $BASE/v1/brain/stats | jq .
# { "notes": 412, "tags": 87, "last_index_at": "2026-05-27T03:55:00", ... }
```

## Authentication

None in dev. The CORS allow-list (see [Architecture](architecture.md))
is the only ambient access control. For prod, slap a reverse proxy
with basic-auth or an OAuth gateway in front of `:8000`. No endpoint
is internally authenticated yet — adding that is on the roadmap.

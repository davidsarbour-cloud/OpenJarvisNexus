# Nexus9 quickstart

From a cold machine to a running HUD. Aimed at David's Windows 11
dev box; macOS/Linux is the same with path adjustments.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12 | The `backend/.venv` is pinned to 3.12. Mismatched minors will fail on `trimesh` / `playwright` wheels. |
| Node | 22+ | Frontend builds with Vite 6; older Node = warnings. |
| Ollama | latest | Native install, not in Docker — Nexus9 talks to `http://localhost:11434`. |
| Docker Desktop | recent | For `chromadb`, `bruce`, `frontend`, `telegram` containers. Optional in dev (chromadb is the only one the HUD needs). |
| Git | 2.40+ | nothing special. |

## One-shot start (recommended)

```pwsh
.\START_ALL.bat
```

That script launches, in order, with bounded waits:

1. **Ollama** native (`ollama serve` if not already running) and pre-loads `qwen3:14b`
2. **chromadb** container (single Docker dependency)
3. **Backend** uvicorn on `:8000` from `backend/.venv`
4. **Frontend** Vite dev server on `:5173` (HMR enabled)
5. **Brain vault graph sidecar** (optional, separate window)

The HUD is at <http://localhost:5173>. The backend Swagger is at
<http://localhost:8000/docs>. If you opened a browser before everything
finished booting, the splash overlay (`NexusBootIntro`) will play once
and unmount itself.

## Manual start (each piece)

If you want to see each layer separately (better for debugging):

```pwsh
# 1) Ollama
ollama serve                                # background OK
ollama pull qwen3:14b                       # one-time
ollama pull nomic-embed-text                # one-time

# 2) ChromaDB (only Docker dep)
docker compose up -d chromadb

# 3) Backend (FastAPI on :8000)
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 4) Frontend (Vite dev server on :5173)
cd frontend
npm install                                 # first time only
npm run dev
```

When the backend boots you should see this in its log:

```text
[CORS] 7 allowed origins
[Daily] Scheduler démarré — STL research 21:00, brain re-index 03:55
[Ollama] Heartbeat démarré — qwen3:14b restera chaud 07h-23h.
[Snapshots] 10 publishers started.
[Nexus9] Startup complet — client HTTP partagé prêt.
```

Snapshot publishers stream every 2 – 60 s; the WebSocket
`/ws/events` is live and will start broadcasting to any tab open.

## First chat

1. Open <http://localhost:5173>
2. Wait for the splash overlay to finish (≤ 10 s)
3. Use the chat overlay (`⌘K` / `Ctrl+K` → "Chat") or visit `/chat`
4. Type: `bonjour jarvis` → Ollama answers locally (`qwen3:14b`,
   ~40 tok/s on a 4070 SUPER)
5. Type: `!claude analyse ce repo` → forces Claude routing (only if
   budget allows; see `BUDGET_MAX_USD` in `backend/.env`)

## Env vars that actually matter

Drop in `backend/.env` (gitignored):

```ini
# REQUIRED
ANTHROPIC_API_KEY=sk-ant-...
BUDGET_MAX_USD=30                # cap per-session Claude spend

# OPTIONAL — extend CORS without code change
NEXUS9_CORS_ORIGINS=http://192.168.1.42:5173,https://nexus9.tail.example.com

# OPTIONAL — Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:14b
OLLAMA_NUM_CTX=4096              # keeps qwen3:14b 100% on GPU

# OPTIONAL — Etsy / Shopify / Telegram (only if you use those routes)
ETSY_ACCESS_TOKEN=...
SHOPIFY_SHARED_SECRET=...
TELEGRAM_BOT_TOKEN=...
```

## Verifying the stack

```pwsh
# Backend reachable?
curl http://localhost:8000/v1/info

# WebSocket pushing snapshots?
curl http://localhost:8000/v1/events/recent?limit=5

# Ollama healthy?
curl http://localhost:11434/api/tags

# ChromaDB up?
curl http://localhost:8000/v1/chromadb/stats
```

If any of those 404 or hang, jump to [Troubleshooting](troubleshooting.md).

## Building for production

```pwsh
cd frontend
npm run build              # outputs to dist/ (served by FastAPI as static)
```

After `npm run build`, FastAPI serves the SPA at <http://localhost:8000/>
directly — no separate Vite process needed. The build emits a service
worker that precaches every WebP avatar / world hero (multi-MB PNGs are
intentionally skipped — see `vite.config.ts` `workbox.globIgnores`).

For the Tauri desktop bundle:

```pwsh
cd frontend
npm run tauri build
```

## Running tests

```pwsh
# Backend
cd backend
.\.venv\Scripts\python.exe -m pytest -q
# 21 passed, 12 deselected (markers: live/cloud excluded)

# Frontend
cd frontend
npm test
# 24 passed across 4 files
```

## Useful slash entry points

| URL | What |
|---|---|
| `/` | Command Center HUD (cards + alerts feed + bottom panel) |
| `/orbital` | 3D orbital view of the agent constellation |
| `/chat` | Full-screen JARVIS chat |
| `/agent-network` | Force-directed agent graph (click a node → detail panel with avatar) |
| `/world/jarvis` | JARVIS world — ACTIVATE skills + AUTO scheduled |
| `/world/forge` | Forge world — STL pipeline cards |
| `/world/commerce` | Commerce world — Etsy/Shopify cards |
| `/world/cyberdeck` | Security / observability cards |
| `/world/vault` | Knowledge (Chroma, brain, scheduled) |
| `/world/docker` | Container roster + system health |
| `/brain` | Brain hub (notes, search, tags) |
| `/vault-graph` | Force-directed vault graph (links between notes) |
| `/dashboard` | Energy / savings dashboard |

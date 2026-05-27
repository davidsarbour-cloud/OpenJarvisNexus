# Nexus9 documentation

David Arbour's Command Center fork of OpenJarvis. Upstream framework
docs still live under [`../architecture/`](../architecture/overview.md)
and [`../development/`](../development/contributing.md) — these pages
are about what Nexus9 adds on top.

## Read in this order

1. **[Architecture](architecture.md)** — high-level diagram, live data
   fabric (snapshot publishers + wsBus + useLiveMetric), boot intro
   flow, asset pipeline, key endpoints. Start here.
2. **[Quickstart](quickstart.md)** — from cold machine to running HUD
   in under 10 minutes. Windows-first; the same steps work on macOS
   and Linux with path tweaks.
3. **[Adding a world card](adding-a-card.md)** — the most common
   "add something to the HUD" workflow: declare data → expose
   endpoint → push via snapshot → render with `useLiveMetric`.
4. **[Adding a skill](adding-a-skill.md)** — two flavours: TOML
   auto-exec (deterministic tool chains) and Hermes protocols (markdown
   playbooks the LLM reads + follows).
5. **[API reference](api.md)** — endpoint catalog with copy-paste curl
   examples. Pair with the auto-generated Swagger at
   `http://localhost:8000/docs` for live exploration.
6. **[Troubleshooting](troubleshooting.md)** — Windows-specific
   gotchas, port conflicts, Ollama issues, CORS, build failures.

## What does Nexus9 do?

| Layer | Tech | What it does |
|---|---|---|
| **Frontend** | React 19 · TS 5.7 · Vite 6 · Tauri 2 | Command Center HUD, 3D Orbital View, 6 world dashboards, agent network graph, chat overlay |
| **Backend** | Python 3.12 · FastAPI · APScheduler | Routing (Claude vs Ollama), agent orchestration, skill execution, brain indexing, /ws/events hub |
| **Inference** | Claude API · Ollama (local) | Haiku/Sonnet/Opus for Claude · qwen3:14b · deepseek-r1:7b · nomic-embed |
| **Memory** | ChromaDB · Obsidian vault | Vector search + markdown notes auto-linked back to the brain |
| **Scheduler** | APScheduler crons | Daily skills (docker-health 03:00, blogwatcher 06:00, polymarket 21:00), weekly skills (ideation Fri 14:00, codebase-inspection Sun 02:00, polymarket digest Sun 18:00) |

## Major patterns introduced by this fork

- **`WorldShell`** — single generic 3-column dashboard component used
  by 5 of the 6 world pages. Each page is a ~45-line wrapper.
- **`snapshot_publisher`** — 10 asyncio loops pushing snapshots over a
  single shared WS instead of N HTTP polls per card. Idle traffic
  dropped from ~140 req/min to ~0.
- **`wsBus`** — singleton WebSocket multiplexer on the frontend.
  Every `useLiveMetric({ wsTopic })` shares the same socket.
- **`BOOT_ID` + `NexusBootIntro`** — process-scoped uuid that drives a
  splash overlay replayed once per uvicorn boot, with video → styled
  placeholder fallback chain.
- **Brain-linked alerts** — scheduled skill completions publish a
  clickable event into `/ws/events` carrying the Obsidian note path,
  so the RightPanel feed opens the note on click via
  `obsidian://open?vault=BRAIN&file=…`.

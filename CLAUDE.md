# CLAUDE.md — NEXUS9 System Constitution

---

## USER

**David Arbour** — French, direct, concrete.
Stack: Python, FastAPI, React/TypeScript, Docker, Ollama.
Etsy: D3Dprintix (3D printing).
Respond in French unless code/technical output.

---

## CORE PRINCIPLE

Nexus9 = modular AI headquarters. Fixed agents, fixed models, fixed hierarchy.
Architecture MUST remain modular and scalable.

---

## SKILLS INDEX

skills/agents.md           — all agent specs
skills/routing.md          — mission routing + Superpowers mapping
skills/architecture.md     — ports, files, env vars
skills/stl-pipeline.md     — D3Dprintix STL pipeline (FORGE)
skills/design.md           — Nexus9 visual identity
skills/session-protocol.md — session logs + Telegram commands
skills/session-history.md  — historique sessions
skills/superpowers.md      — Superpowers bridge (port 8082)
skills/obsidian-skills.md  — Obsidian Skills bridge (port 8081)
skills/vault-graph.md      — Vault Graph Sync (port 8083, planet VAULT)

---

## QUICK AGENT REFERENCE

| Agent | Model | Trigger |
|-------|-------|---------|
| JARVIS | claude-haiku-4-5 | every message |
| ULTRON | claude-sonnet-4-6 | !ultron, strategy |
| QWEN | ollama/qwen3:14b | !qwen, bulk |
| CORTANA | deepseek-coder:6.7b | !cortana, code |
| BRUCE | OpenHands+qwen3:14b | !bruce, autonomous |
| NOVA | deepseek-r1:7b | !nova, complex code |
| FORGE | Meshy AI + local | !forge, STL, 3D |

---

## GLOBAL RULES

1. JARVIS orchestrates — always first touchpoint, never bypassed
2. Prefer local Ollama — free, fast, private
3. Haiku first, Sonnet only when quality matters
4. Never break existing functionality
5. .env never committed to git
6. Architecture stays modular

---

## ARCHITECTURE GUARDRAILS (backend)

Backend = `main.py` (bootstrap only: app, lifespan, CORS, SPA, `include_router`)
+ `app_state.py` (shared singletons) + one `*_router.py` per feature
(docker, speech, reports, memory, brain, daily, health, crew, orchestrate,
agents, chat). Shared services: `ollama_client`, `memory`, `budget_tracker`, `tools/*`.

### MUST FOLLOW
- No circular imports — routers import `app_state`, never `main`; `app_state` imports nothing back.
- Modular routers — one `APIRouter` per domain; wire in `main.py` via `include_router`.
- Single source of truth — shared state (Anthropic client, `_budget`, `_agents_status`, http client) lives ONLY in `app_state`.
- State isolation — feature state stays in its own router; cross-cutting state goes to `app_state`.
- Reusable services — talk to Ollama/memory/budget/tools through their service module, not ad-hoc.

### NEVER DO
- AI / chat logic in `main.py` (it belongs in `chat_router`).
- Duplicated shared state (no second `claude` client or `_budget`).
- Scattered direct Ollama calls — go through `ollama_client` (embeddings excepted).
- God-object `app_state` — if it grows past ~300 lines, split it.
- Router-to-router imports — share via `app_state`, never `from x_router import …`.

### PERFORMANCE
- Cache LLM clients — build the Anthropic client ONCE at startup (`app_state`).
- Keep routing lightweight — keyword routing, no LLM call to decide routing.
- No model loading inside a request — lazy-load + cache (Whisper/Kokoro), pre-warm in lifespan.
- Isolate expensive tasks — `to_thread`/executor for sync work, `BackgroundTasks` for jobs.

### Verify before committing backend changes
`python -m py_compile`, `ruff check --select F821` (no undefined names),
import-smoke (`import main` → 134 routes), pre-commit lint hook stays green.

---

## MONITORING — Docker Compose Profiles

Optional services gated behind `profiles:` in `docker-compose.yml`:

- **Prometheus** (`profile: monitoring`) — start with
  `docker compose --profile monitoring up -d prometheus` then it listens on `:9090`.
  Smoke test reports `prometheus down` until this profile is activated.
- **SonarQube** (`profile: quality`) — already up by default in your stack.
  SonarQube forces the admin password change on first login; the smoke test
  will report `401` until you do either:
  1. Reset the admin password back to `admin/admin`, **or**
  2. Generate a SonarQube token (UI → My Account → Security → Token) and
     export it: `setx SONARQUBE_TOKEN sqp_xxxxxxxxxxxx`. The backend prefers
     the token (sent as basic-auth username, empty password — Sonar's
     standard convention) and falls back to `SONARQUBE_USER`/`SONARQUBE_PASS`.

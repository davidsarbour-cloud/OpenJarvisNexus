# architecture.md — NEXUS9 Project Architecture

---

## SERVICES AND PORTS

| Service | Port | Start |
|---------|------|-------|
| Ollama | 11434 | 1_OLLAMA.bat |
| Backend FastAPI | 8000 | 2_BACKEND.bat |
| Frontend Vite | 5173 | 3_FRONTEND.bat |
| Telegram Bot | — | 4_TELEGRAM.bat |
| BRUCE (OpenHands) | 3000 | docker compose --profile bruce up bruce |
| NOVA inference | 9000 | uvicorn services/deepseek_sft/inference_server:app --port 9000 |
| Vault Graph Sync | 8084 | cd services/vault_graph && npm start |

---

## FILE STRUCTURE

C:\OpenJarvisNexus\
  backend\
    main.py               — FastAPI principale
    telegram_bot.py       — Bot Telegram
    memory.py             — Mémoire persistante JSON
    ollama_client.py      — Client Ollama local-first
    crew_factory.py       — Orchestration CrewAI
    crew_agents.py        — Builders agents
    jarvis_tools.py       — Tools CrewAI
    stl_agent.py          — Pipeline STL complet
    stl_researcher.py     — Researcher quotidien 21h
    config.json           — Personnalité Jarvis, routing
    memory.json           — Facts persistants (auto-generated)
    sessions.json         — Historique conversations (auto-generated)
    .env                  — Clés API — NE PAS COMMITTER
  frontend\               — React + TypeScript (port 5173)
  services\
    deepseek_sft\         — Fine-tuning QLoRA NOVA
  skills\                 — Modular skill files
  Nexus9.html             — UI principale Three.js
  docker-compose.yml      — Orchestration Docker
  CLAUDE.md               — Constitution système
  Jarvis.md               — Manuel orchestration JARVIS

---

## ENV VARIABLES (backend/.env)

ANTHROPIC_API_KEY       = sk-ant-...
CLAUDE_MODEL            = claude-haiku-4-5
CLAUDE_MODEL_GROS       = claude-sonnet-4-6
OLLAMA_HOST             = http://localhost:11434
OLLAMA_MODEL            = qwen3:14b
OLLAMA_CODER_MODEL      = deepseek-coder:6.7b
DEEPSEEK_MODEL          = deepseek-r1:7b
OPENHANDS_URL           = http://localhost:3000
TELEGRAM_BOT_TOKEN      = ...
MESHY_API_KEY           = ...
BLENDER_PATH            = C:\Program Files\...
BAMBU_STUDIO_PATH       = C:\Program Files\...

---

## DEVELOPMENT RULES

1. Never break existing — test /health before touching main.py
2. Imports are relative to backend/ — never add sys.path hacks
3. Frontend connects to http://localhost:8000 by default
4. All backend runs from backend/ directory
5. Comments in French in code, commit messages in French
6. 
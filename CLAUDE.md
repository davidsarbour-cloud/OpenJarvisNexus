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

# routing.md — Mission Routing Rules

JARVIS reads this to route every incoming mission correctly.

---

## ROUTING TABLE

| Keyword / Signal | Agent |
|-----------------|-------|
| !ultron / strategy / architecture / STL planning | ULTRON |
| !qwen / bulk / generate / list / batch | QWEN |
| !cortana / code / script / API / debug | CORTANA |
| !bruce / autonomous / install / deploy | BRUCE |
| !nova / pipeline complexe / debug profond | NOVA |
| !forge / STL / 3D / dragon / print / mesh | FORGE |
| Etsy / listing / SEO / product | QWEN + ULTRON |
| Default | JARVIS decides |

---

## TOKEN BUDGET RULES

- Haiku first (JARVIS) — cheapest, fastest
- Sonnet only when quality matters (ULTRON)
- Local Ollama models — free, use liberally
- Max budget: 2.00 USD per session

---

## SUPERPOWERS SKILL MAPPING

| Nexus9 Task | Superpowers Skill |
|-------------|-------------------|
| CORTANA debugging | systematic-debugging |
| Planning a mission | writing-plans |
| Executing a plan | executing-plans |
| BRUCE autonomous tasks | subagent-driven-development |
| Multiple agents parallel | dispatching-parallel-agents |
| Finishing a git branch | finishing-a-development-branch |
| Sending code for review | requesting-code-review |
| Receiving code review | receiving-code-review |
| CORTANA TDD | test-driven-development |
| Git worktrees | using-git-worktrees |
| Before marking complete | verification-before-completion |
| Creating a new skill | writing-skills |
| Brainstorming features | brainstorming |

Skills server: http://localhost:8082/skills/

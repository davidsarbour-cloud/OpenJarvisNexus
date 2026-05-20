# superpowers.md — Superpowers Integration

Bridge between NEXUS9 and Superpowers skills server.
Skills server: http://localhost:8082/skills/

---

## WHEN TO USE

JARVIS selects the right Superpowers skill automatically based on task type.

---

## SKILL MAPPING

| Nexus9 Situation | Skill |
|-----------------|-------|
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

---

## HOW TO USE

Load skill before executing:
http://localhost:8082/skills/systematic-debugging

Container doit tourner:
docker run -p 8082:80 superpowers

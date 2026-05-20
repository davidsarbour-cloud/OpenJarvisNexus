# obsidian-skills.md — Obsidian Skills Integration

Bridge between NEXUS9 and Obsidian Skills server.
Skills server: http://localhost:8081/skills/

---

## WHEN TO USE

Quand JARVIS ou un agent doit travailler avec des notes, markdown, canvas ou automatisation Obsidian.

---

## SKILL MAPPING

| Nexus9 Situation | Skill |
|-----------------|-------|
| Nettoyer contenu web pour notes | defuddle |
| Travailler avec canvas visuel JSON | json-canvas |
| Base de données dans Obsidian | obsidian-bases |
| Automatiser Obsidian via CLI | obsidian-cli |
| Markdown étendu Obsidian | obsidian-markdown |

---

## HOW TO USE

Load skill before executing:
http://localhost:8081/skills/defuddle

Container doit tourner:
docker run -p 8081:80 obsidian-skills

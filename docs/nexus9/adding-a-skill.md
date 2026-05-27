# Adding a new skill

Two flavours, very different ergonomics:

| Flavour | When | Author burden | Cost |
|---|---|---|---|
| **TOML auto-exec** | Deterministic tool chains (run a command, fetch metrics, restart a container) | Low — declare steps in TOML | ~free (no LLM call) |
| **Hermes protocol** | Reasoning-heavy playbooks (debug a bug, plan, ideate, audit a codebase) | Higher — write the markdown protocol | One LLM turn per use |

JARVIS sees both in its skill catalog (injected into the system prompt
on every chat turn) and decides which `skill_get` to call.

## Flavour 1: TOML auto-exec

Worked example: a `disk-cleanup` skill that prunes Docker images and
reports space reclaimed.

### 1. Define the steps

`backend/skills/disk-cleanup.toml`:

```toml
[skill]
name = "disk-cleanup"
description = "Prune unused Docker images and report space reclaimed."

[[skill.steps]]
tool_name = "docker_prune"
arguments_template = '{"keep_recent_days": 7}'
output_key = "pruned"

[[skill.steps]]
tool_name = "docker_disk_usage"
arguments_template = '{}'
output_key = "after"
```

Each step calls a `tool_name` that must exist in `backend/tools/`.
`arguments_template` is JSON (rendered against previous step outputs
via `{{output_key.field}}` if you need chaining). `output_key` is what
the next step sees.

### 2. Implement the tool (if missing)

Each TOML tool maps to a Python function in `backend/tools/*.py`
exposed via `TOOL_REGISTRY`. Existing tools cover docker / skill /
filesystem; for our example `docker_prune` would need a small wrapper:

```python
# backend/tools/docker_tools.py
def docker_prune(*, keep_recent_days: int = 7) -> dict:
    import subprocess
    out = subprocess.run(
        ["docker", "image", "prune", "-af", f"--filter=until={keep_recent_days * 24}h"],
        capture_output=True, text=True, timeout=60,
    )
    reclaimed = ""
    for line in out.stdout.splitlines():
        if line.lower().startswith("total reclaimed"):
            reclaimed = line.split(":", 1)[1].strip()
    return {"reclaimed": reclaimed, "stdout": out.stdout[-2000:]}

TOOL_REGISTRY["docker_prune"] = docker_prune
```

### 3. Add the skill button (optional)

If you want a one-click ACTIVATE button in `/world/jarvis`, append it
to the `SKILLS` array in
`frontend/src/components/JarvisWorld/JarvisSkillsSection.tsx`:

```tsx
{
  name: 'disk-cleanup',
  kind: 'toml',
  icon: HardDrive,
  description: 'Prune Docker images older than 7 days and report space reclaimed.',
  example: 'nettoie les images Docker',
  // No scheduledAuto → manual ACTIVATE only
},
```

### 4. Schedule it (optional)

If you want daily auto-execution, edit `backend/daily_tasks.py`
`create_scheduler()`:

```python
sched.add_job(
    lambda: skill_run("disk-cleanup"),
    CronTrigger(hour=4, minute=15),
    id="skill_disk_cleanup",
    name="Daily: disk-cleanup (04:15)",
    replace_existing=True,
)
```

The scheduler hook in `_lifespan` already publishes a completion event
to the WS hub for every cron job, so the RightPanel alerts feed picks
it up automatically (clickable → opens the brain note if one was
written by `_write_skill_brain_note`).

### 5. Reload + test

```pwsh
# Backend autoload picks up new TOML on file save.
# Force-touch if uvicorn missed it:
(Get-Item backend/skills/disk-cleanup.toml).LastWriteTime = Get-Date

curl http://localhost:8000/v1/skills/list | jq .
# expect "disk-cleanup" in the response
```

In the JARVIS chat: `nettoie les images Docker` → JARVIS calls
`skill_get("disk-cleanup")` → executes the steps → returns the
combined output. If you added the button, hit it from `/world/jarvis`.

## Flavour 2: Hermes protocol

Worked example: a `weekly-review` skill that summarises everything
shipped this week into a markdown brief.

### 1. Create the skill folder

```text
backend/skills/hermes/weekly-review/
  SKILL.md
```

### 2. Write the SKILL.md

The frontmatter is parsed by the loader; the body is what JARVIS reads
verbatim when `skill_get("weekly-review")` is called.

```markdown
---
name: weekly-review
description: 'Summarise everything shipped this week into a 5-bullet brief.'
version: 1.0.0
author: David Arbour
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, summary, weekly]
    related_skills: [plan, codebase-inspection]
---

# Weekly Review

When the user asks for a weekly review or a "what shipped" summary,
follow these steps:

1. **Survey commits** — run `git log --since='7 days ago' --oneline`
   on the repo root. Sort by commit type prefix (feat / fix / refactor /
   docs / perf / chore).

2. **Cluster by area** — group commits into 3–5 themes. Each theme
   should map to one of: backend · frontend · infra · docs · tests.

3. **Brief** — emit exactly this shape:

   ```markdown
   ## Week of {{ISO date Monday}}

   ### Highlights
   - <one-line per major shipped feature, 3–5 bullets>

   ### By area
   - **Backend:** <…>
   - **Frontend:** <…>
   - **Infra:** <…>

   ### Numbers
   - X commits · Y files changed · Z LOC delta
   ```

4. **Sanity check** — never invent commits. If the git log is empty,
   say "no commits this week" and stop.

5. **Persist** — write the result to
   `BRAIN/02_Daily/<today>/weekly-review.md` with frontmatter:
   ```yaml
   ---
   nexus9_skill: weekly-review
   nexus9_run_at: <ISO>
   tags: [weekly-review, automated]
   ---
   ```
```

The protocol is the contract; JARVIS will follow it verbatim. Keep
steps numbered, output shape explicit, and edge cases (empty git log)
called out. The model fills in the reasoning.

### 3. Register it in the catalog injection

The skill catalog is auto-discovered on backend boot via
`backend/tools/skill_tools._resolve_skills_dir()` — no manual
registration needed. Just verify it shows up:

```pwsh
curl http://localhost:8000/v1/skills/list | jq '.skills[] | select(.name=="weekly-review")'
```

### 4. Add to the AUTO schedule (optional)

If you want it to run automatically every Sunday evening, append a
cron job in `backend/daily_tasks.py`:

```python
sched.add_job(
    lambda: skill_run("weekly-review"),
    CronTrigger(day_of_week="sun", hour=20, minute=0),
    id="skill_weekly_review",
    name="Weekly: weekly-review (Sun 20:00)",
    replace_existing=True,
)
```

And add the corresponding entry to the frontend `SKILLS` array with
`scheduledAuto: 'weekly'` so it appears on the AUTO side of the JARVIS
world page.

## Gotchas

- **Routing**: Skills are catalogued in JARVIS's system prompt. They
  cost tokens every turn. Keep `description` tight (~80 chars). The
  frontend `_SKILL_LIST_KW` shortcut bypasses Claude when the user
  asks "what skills do you have?" — useful, doesn't burn budget.
- **Forcing Ollama**: The `SkillActivator` modal prepends `!local ` to
  every prompt so the chat router takes the Ollama branch (qwen3:14b
  handles every Hermes protocol fine). Don't change this unless you
  want each click to cost ~$0.01 in Claude tokens.
- **TOML chaining**: If `step[1].arguments_template` references
  `step[0]`'s output, the template engine substitutes via
  `{{output_key.field}}` syntax. Test in a small notebook first;
  template errors at runtime are obscure.
- **Hermes self-test**: Hermes skills don't have integration tests by
  default — the protocol is prose. Add a quick smoke in
  `backend/tests/test_skills_search.py` if you want CI coverage of
  the skill discovery path.

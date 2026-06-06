# Claude Code: Zero to Pro
### 30 Real Workflows, Power Prompts & Copy-Paste Configs

*A small, no-fluff field guide. Every entry is a real Claude Code feature with the exact
command, when to use it, a concrete example, and a pro tip. Work top to bottom — it goes
from your first session to building your own custom automations.*

> Claude Code is Anthropic's terminal coding agent. This pack assumes you've installed it
> and can run `claude` in a project folder. Everything here is copy-paste ready.

---

## HOW TO USE THIS PACK

1. Read a level, try the moves in a real project, then move to the next.
2. Anything in a `code block` is typed **into the Claude Code prompt** (or your shell when it starts with `claude`/`$`).
3. The **BONUS CONFIGS** at the end are files you paste into your repo — they make Claude Code yours.
4. Keep the **CHEAT SHEET** open in a second window.

---

# LEVEL 1 — BEGINNER
*Get productive in your first session.*

### 1. Start in the right folder
**What it does:** Claude Code reads the folder you launch it from as the project.
**When to use:** Always — first thing.
**Do this:**
```
$ cd my-project
$ claude
```
**Example:** Launch inside a Git repo so Claude can see your history and files.
**Pro tip:** Run `claude` from the repo root, not a subfolder — it needs to see the whole project to reason well.

---

### 2. Ask before you edit — describe, don't micromanage
**What it does:** Claude plans and edits across files from a plain-English goal.
**When to use:** Any change bigger than one line.
**Do this:**
```
Add input validation to the signup form: email must be valid, password >= 8 chars.
Show me the changed files when done.
```
**Example:** It finds the form component, edits it, and lists what changed.
**Pro tip:** State the **goal and the done-condition**, not the steps. "Show me the changed files when done" gives you a clean review point.

---

### 3. Generate your project memory with `/init`
**What it does:** Scans the codebase and writes a `CLAUDE.md` — persistent project context loaded every session.
**When to use:** Once per new project, then re-run after big structural changes.
**Do this:**
```
/init
```
**Example:** It documents your stack, scripts, and conventions so you never re-explain them.
**Pro tip:** Open the generated `CLAUDE.md` and trim it. Short and accurate beats long and stale.

---

### 4. Keep context clean with `/clear` and `/compact`
**What it does:** `/clear` wipes the conversation; `/compact` summarizes it to free up room while keeping the gist.
**When to use:** `/clear` when switching to an unrelated task; `/compact` mid-task when it slows or warns about context.
**Do this:**
```
/clear
```
```
/compact
```
**Example:** Finished the auth bug, now doing CSS? `/clear` first — a fresh head is faster and cheaper.
**Pro tip:** A stuffed context makes Claude slower and dumber. Clearing between tasks is the #1 beginner upgrade.

---

### 5. Review before you trust — Plan Mode
**What it does:** Claude analyzes and proposes changes **without touching files**.
**When to use:** Unfamiliar code, risky refactors, or when you want to approve the approach first.
**Do this:** Press **Shift+Tab** to cycle permission modes until you see **plan mode**, then ask your question.
**Example:** "How would you migrate this from JavaScript to TypeScript?" → you get a plan, not 40 silent edits.
**Pro tip:** Plan first, then switch to **accept-edits** mode to let it execute the approved plan hands-free.

---

### 6. Pull a file or error straight into the prompt
**What it does:** Claude reads files you point at and acts on pasted errors.
**When to use:** Debugging, or focusing it on one file.
**Do this:**
```
Here's the failing test output:
<paste the stack trace>
Find the cause and fix it.
```
**Example:** Paste a red CI log; it traces the failing line and patches it.
**Pro tip:** Reference a file by path (`src/api/user.ts`) and Claude opens it itself — you don't need to paste contents.

---

### 7. Undo is your safety net — commit early
**What it does:** Claude's edits are just file changes; Git is your undo.
**When to use:** Before letting Claude make a big change.
**Do this:**
```
$ git add -A && git commit -m "checkpoint before refactor"
```
Then in Claude: `Refactor the payments module to use the new API.`
**Pro tip:** A clean commit before each Claude task means `git reset --hard` instantly reverts anything you don't like. Fearless mode.

---

### 8. Switch models for the job with `/model`
**What it does:** Changes the model mid-session.
**When to use:** Heavier reasoning (Opus) for architecture; faster model for simple edits.
**Do this:**
```
/model
```
**Example:** Bump to Opus to design a tricky algorithm, drop back down for boilerplate.
**Pro tip:** Match the model to the task — you save money on easy work and get more horsepower where it matters.

---

# LEVEL 2 — INTERMEDIATE
*Daily pro workflows.*

### 9. Make Claude explain the codebase first
**What it does:** Turns Claude into an onboarding guide.
**When to use:** New repo, or inherited code you didn't write.
**Do this:**
```
Give me a map of this codebase: entry points, main modules, how a request flows
through the system. Keep it under 30 lines.
```
**Pro tip:** Cap the length ("under 30 lines"). You get a usable map instead of an essay.

---

### 10. Test-driven: let Claude write the test first
**What it does:** Claude writes a failing test, then code to pass it.
**When to use:** Bug fixes and new functions where correctness matters.
**Do this:**
```
Write a failing test that reproduces this bug, confirm it fails, then fix the code
until the test passes. Don't change the test to make it pass.
```
**Pro tip:** "Don't change the test to make it pass" stops the classic shortcut where the agent weakens the test instead of fixing the bug.

---

### 11. Resume yesterday's session with `/resume`
**What it does:** Reopens a previous conversation with its full context.
**When to use:** Continuing multi-day work.
**Do this:**
```
/resume
```
or from the shell:
```
$ claude --continue        # most recent session
$ claude --resume          # pick from a list
```
**Pro tip:** `--continue` is great in scripts to chain a follow-up onto the last run.

---

### 12. Scope the change so it doesn't sprawl
**What it does:** Constrains Claude to the files you want touched.
**When to use:** Big repos where a change could leak everywhere.
**Do this:**
```
Only modify files under src/billing/. Do not touch tests or config.
Add proration to the subscription upgrade flow.
```
**Pro tip:** Explicit guardrails ("only under X", "do not touch Y") keep diffs small and reviewable.

---

### 13. Ask for a diff review of your OWN changes
**What it does:** Claude reviews uncommitted work for bugs and smells.
**When to use:** Before you push.
**Do this:**
```
Review my uncommitted changes for bugs, edge cases, and anything I'd be embarrassed
to ship. Be specific with file and line.
```
**Pro tip:** There's also a bundled `/review` skill for PR-style reviews — type `/` to discover the skills your install ships with.

---

### 14. Grant access to a second directory
**What it does:** Lets Claude see a folder outside the current project.
**When to use:** Monorepos, or a sibling library you're editing together.
**Do this:**
```
/add-dir ../shared-lib
```
**Pro tip:** Add only what you need. More directories = more context = slower and pricier.

---

### 15. Make it ask less — accept-edits mode
**What it does:** Auto-approves file edits so you're not hitting "yes" constantly.
**When to use:** Once you trust the plan and want momentum.
**Do this:** Press **Shift+Tab** to switch to **accept-edits** mode.
**Pro tip:** Use it *after* plan mode approves the approach. Plan → accept-edits is the safe fast lane.

---

### 16. Manage memory live with `/memory`
**What it does:** Opens your `CLAUDE.md` and memory files to view/edit.
**When to use:** When Claude keeps forgetting a convention, or repeats a mistake.
**Do this:**
```
/memory
```
Or add a memory instantly by starting a line with `#`:
```
# Always use pnpm, never npm, in this repo.
```
**Pro tip:** The `#` shortcut is the fastest way to teach Claude a rule it'll remember next session.

---

# LEVEL 3 — ADVANCED
*Customize Claude Code so it works your way.*

### 17. Build a custom slash command
**What it does:** A reusable prompt you trigger with `/yourcommand`.
**When to use:** Any prompt you type more than twice.
**Do this:** Create `.claude/commands/pr.md`:
```markdown
---
description: Summarize my staged changes as a PR description
---
Write a concise pull-request title and description for the staged diff below.
Include a "Testing" section.

$ARGUMENTS
```
Then run it:
```
/pr
```
**Example:** `/pr` now generates a PR write-up from your staged changes every time.
**Pro tip:** `$ARGUMENTS` injects whatever you type after the command, so `/pr focus on the API changes` passes that note through.

---

### 18. Automate with a Hook (format on every edit)
**What it does:** Runs a shell command automatically at a lifecycle event — deterministic, no asking.
**When to use:** Auto-format, auto-lint, or block dangerous commands.
**Do this:** In `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "npx prettier --write \"$CLAUDE_FILE_PATHS\"" }
        ]
      }
    ]
  }
}
```
**Example:** Every time Claude edits a file, Prettier formats it — you never think about it again.
**Pro tip:** Run `/hooks` to add and inspect hooks interactively instead of hand-writing JSON.

---

### 19. Block dangerous commands with a Hook
**What it does:** A `PreToolUse` hook can **deny** an action by exiting with code 2.
**When to use:** Guardrails on a shared or production machine.
**Do this:** A script wired to `PreToolUse` on `Bash` that checks the command and:
```bash
# in your hook script
if echo "$INPUT" | grep -q "rm -rf /"; then
  echo "Blocked: refusing destructive command" >&2
  exit 2     # exit code 2 = block the tool call
fi
exit 0
```
**Pro tip:** Hooks enforce rules deterministically. `CLAUDE.md` only *asks* Claude nicely — a hook actually stops the action.

---

### 20. Create a specialized subagent
**What it does:** A focused helper with its own instructions and tool access, for one kind of job.
**When to use:** Recurring specialized work (reviewing, testing, searching) you want isolated from your main thread.
**Do this:**
```
/agents
```
Follow the prompts to create one (e.g. a "test-writer" agent). It saves a markdown file
under `.claude/agents/` with a `name`, `description`, and allowed `tools`.
**Example:** A `code-reviewer` subagent Claude delegates to automatically when you ask for a review.
**Pro tip:** Let `/agents` generate the file so you never fight the frontmatter format. Keep each agent's job narrow.

---

### 21. Connect a tool with MCP
**What it does:** MCP (Model Context Protocol) plugs external tools/data into Claude — GitHub, Postgres, Puppeteer, your own server.
**When to use:** When Claude needs live data or actions outside the filesystem.
**Do this:**
```
$ claude mcp add
```
…and follow the prompts, or commit a project `.mcp.json`:
```json
{
  "mcpServers": {
    "postgres": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
    }
  }
}
```
**Example:** With a Postgres MCP server, "show me the 5 newest users" runs a real query.
**Pro tip:** Use `/mcp` to see connected servers and their status. Commit `.mcp.json` to share servers with your team.

---

### 22. A CLAUDE.md that actually helps
**What it does:** Persistent project rules loaded every session.
**When to use:** Every serious project.
**Do this:** Keep it short and specific (full template in BONUS):
```markdown
## Commands
- Test: `pnpm test`
- Lint: `pnpm lint`
## Conventions
- TypeScript strict. No `any`.
- Use the existing `Result<T>` type for fallible functions.
```
**Pro tip:** Pull in other docs with `@import`: a line like `See @docs/architecture.md` loads that file's content as context.

---

### 23. Pre-approve safe tools to stop the prompts
**What it does:** A permission allowlist so trusted commands run without asking.
**When to use:** Commands you run constantly (your test runner, git status).
**Do this:** In `.claude/settings.json`:
```json
{
  "permissions": {
    "allow": ["Bash(pnpm test)", "Bash(git status)", "Read(./**)"],
    "deny":  ["Bash(curl *)"]
  }
}
```
**Pro tip:** Whitespace matters in rules: `Bash(git *)` matches commands that start with `git ` (note the space).

---

### 24. Tune reasoning depth
**What it does:** Trades speed for deeper thinking on hard problems.
**When to use:** Gnarly bugs and architecture vs. quick edits.
**Do this:** Ask explicitly:
```
Think carefully about the concurrency edge cases before you change anything.
```
**Pro tip:** Spend the deep thinking on *design*, not boilerplate. Over-thinking trivial edits just costs time.

---

# LEVEL 4 — PRO
*Automation, scripting, and scale.*

### 25. Run Claude headless from the shell
**What it does:** `claude -p` runs one prompt and exits — scriptable, no UI.
**When to use:** Cron jobs, git hooks, batch tasks.
**Do this:**
```
$ claude -p "Summarize today's changes in CHANGELOG style" > notes.md
```
**Pro tip:** Pipe input in: `cat error.log | claude -p "what's the root cause?"`.

---

### 26. Get machine-readable output
**What it does:** `--output-format json` returns structured results (result text, session id, cost).
**When to use:** When another script consumes Claude's output.
**Do this:**
```
$ claude -p "list TODOs in this repo as JSON" --output-format json
```
**Pro tip:** Use `stream-json` with `--verbose` to process output token-by-token in real time.

---

### 27. Lock down tools for automation
**What it does:** `--allowedTools` pre-approves exactly what a headless run may do.
**When to use:** CI/scripts where you can't click "yes".
**Do this:**
```
$ claude -p "run the test suite and report failures" --allowedTools "Bash(pnpm test),Read"
```
**Pro tip:** Grant the *minimum* tools the job needs. Never reach for the bypass flag in a script you don't fully control.

---

### 28. The "fresh checkout" reproducible run
**What it does:** A run that ignores your local CLAUDE.md, hooks, and plugins for a clean, repeatable result.
**When to use:** CI, benchmarks, debugging "works on my machine" config issues.
**Do this:**
```
$ claude -p "build and report errors" --output-format json
```
…on a clean clone, with project-committed settings only.
**Pro tip:** Keep automation config in the **project** `.claude/settings.json` (committed) so every machine and teammate runs the same way.

---

### 29. Chain Claude into Git hooks
**What it does:** Auto-generate commit messages or pre-commit reviews.
**When to use:** Standardize commits across a team.
**Do this:** In a `prepare-commit-msg` hook:
```bash
git diff --cached | claude -p "Write a concise conventional-commit message for this diff" >> "$1"
```
**Pro tip:** Start it as a suggestion (append, let the human edit) before making it fully automatic.

---

### 30. Recurring tasks with /loop and /schedule
**What it does:** `/loop` re-runs a prompt on an interval; `/schedule` sets up scheduled agent runs.
**When to use:** "Check the deploy every 5 minutes", nightly maintenance, recurring reports.
**Do this:**
```
/loop 5m check CI status and tell me if anything failed
```
**Pro tip:** For unattended jobs, combine headless mode (#25) with your OS scheduler (cron / Task Scheduler) for full control.

---

# BONUS — COPY-PASTE CONFIGS

### A. Drop-in `CLAUDE.md` template
```markdown
# Project: <name>

## Commands
- Install: `<cmd>`
- Dev: `<cmd>`
- Test: `<cmd>`
- Lint/format: `<cmd>`

## Architecture
- Entry point: `<path>`
- Key modules: `<paths>`
- See @docs/architecture.md

## Conventions
- <language> strict mode; no `any` / no unused.
- Error handling: <pattern>.
- Naming: <pattern>.

## Do NOT
- Don't edit generated files in `dist/`.
- Don't commit secrets; use `.env`.
```

### B. Format-on-edit hook (`.claude/settings.json`)
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "npx prettier --write \"$CLAUDE_FILE_PATHS\"" }
        ]
      }
    ]
  }
}
```

### C. Custom `/pr` command (`.claude/commands/pr.md`)
```markdown
---
description: Generate a PR title + description from staged changes
---
Write a concise pull-request title and description for the staged diff.
Include a short "Testing" section. Note: $ARGUMENTS
```

### D. Safe permissions starter (`.claude/settings.json`)
```json
{
  "permissions": {
    "allow": ["Read(./**)", "Bash(git status)", "Bash(git diff:*)"],
    "deny":  ["Bash(rm -rf *)", "Bash(curl *)"]
  }
}
```

### E. MCP server (`.mcp.json`)
```json
{
  "mcpServers": {
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "<your-token>" }
    }
  }
}
```

---

# CHEAT SHEET

### Essential slash commands
| Command | Does |
|---------|------|
| `/init` | Generate `CLAUDE.md` from your codebase |
| `/clear` | Wipe conversation (new task) |
| `/compact` | Summarize context to free room |
| `/memory` | View/edit memory & `CLAUDE.md` |
| `/model` | Switch model |
| `/config` | Open settings UI |
| `/agents` | Create/manage subagents |
| `/hooks` | Add/inspect hooks |
| `/mcp` | Manage MCP servers |
| `/add-dir` | Grant access to another folder |
| `/resume` | Reopen a past session |
| `/help` | List everything available |

### Permission modes (cycle with Shift+Tab)
| Mode | Behavior |
|------|----------|
| default | Asks before edits / commands |
| accept-edits | Auto-approves file edits |
| plan | Proposes changes, edits nothing |
| bypass | No checks — isolated containers only |

### Keyboard
| Key | Action |
|-----|--------|
| **Shift+Tab** | Cycle permission mode |
| **Esc** | Interrupt Claude |
| **Esc Esc** | Edit a previous message / rewind |
| **Ctrl+C** | Cancel current input |
| **↑** | Previous prompt from history |

### The mental model
- **CLAUDE.md** = persistent context (asks nicely)
- **Hooks** = deterministic automation (actually enforces)
- **Skills / commands** = reusable prompts on demand
- **Subagents** = focused specialists
- **MCP** = external tools & data

---

*Single-user license. Built for people who want Claude Code to feel like their own tool.*
*Questions: d3dprintix@outlook.com*

# Claude Agents Pack — 14 Specialized Subagents

Fourteen ready-to-use **Claude Code subagents**. Each is a real `.claude/agents/*.md`
file — a focused specialist with its own instructions, tools, and model. Claude
delegates to them automatically when the task fits, or you can invoke them on demand.
Drop them in and your Claude Code gets a whole team.

> **Skills vs Agents:** a *skill* is a command you trigger (`/commit-message`).
> An *agent* is a specialist Claude hands work to — it runs with its own focused
> system prompt and its own tool set. This pack is the agents.

## The team

| Agent | Role | Model |
|-------|------|-------|
| **code-reviewer** | Reviews diffs for bugs, edge cases, security | opus |
| **security-auditor** | Audits the codebase for vulnerabilities | opus |
| **debugger** | Root-cause debugging + regression test | opus |
| **performance-optimizer** | Finds & fixes bottlenecks, measured | opus |
| **architect** | Plans the approach & trade-offs before building | opus |
| **test-writer** | Writes thorough, meaningful tests | sonnet |
| **refactorer** | Cleans up code with zero behavior change | sonnet |
| **doc-writer** | READMEs, docstrings, API docs, guides | sonnet |
| **api-designer** | Consistent REST/GraphQL endpoints | sonnet |
| **database-expert** | Schema, queries, indexes, safe migrations | sonnet |
| **devops-engineer** | Docker, CI/CD, deploy config | sonnet |
| **frontend-specialist** | Components, styling, responsive UI | sonnet |
| **accessibility-auditor** | WCAG a11y review & fixes | sonnet |
| **explorer** | Fast read-only codebase search & mapping | haiku |

## Install (30 seconds)

**Per project** (share with your team):
1. Copy the `agents/` files into your project's `.claude/agents/` directory:
   ```
   your-project/.claude/agents/code-reviewer.md
   your-project/.claude/agents/debugger.md
   ...
   ```
2. Open Claude Code. Run `/agents` to see them listed.

**For all your projects** (just you): copy the files into `~/.claude/agents/` instead.

## Use

You usually don't have to do anything — Claude **delegates automatically** based on
each agent's `description` (e.g. it hands a review to `code-reviewer`). To invoke one
explicitly, just ask:
```
Have the security-auditor review the auth module.
Use the architect to plan how to add multi-tenant support.
```

## Customize

Each agent is plain markdown with a small header:
```yaml
---
name: code-reviewer
description: when Claude should use it
tools: Read, Grep, Glob, Bash   # what it's allowed to touch
model: opus                      # opus | sonnet | haiku (or remove to inherit)
---
<the agent's system prompt>
```
Edit the body to fit your standards, change the `model`, or restrict `tools`. The
read-only agents (reviewer, auditor, architect, explorer, a11y) can't modify files by
design — a safe default.

---

This pack includes **Master Resell Rights** — see `RESELL_LICENSE.txt` and
`RESELLER_KIT.md`. Questions: d3dprintix@outlook.com

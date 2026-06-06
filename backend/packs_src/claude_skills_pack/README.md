# Claude Skills Pack — 32 Real Dev Skills

Thirty-two ready-to-use **Claude Code skills**. Each is a real `SKILL.md` you drop
into your project — then trigger it by name with a slash command. They turn repetitive
dev chores into one command. No filler — every skill does something Claude Code can
genuinely do (git, code, tests, files).

## What's inside

**🏆 Flagship workflows** *(multi-step orchestrators — the headline skills)*
| Skill | Trigger | What it does |
|-------|---------|--------------|
| **ship-it** | `/ship-it` | Review → fix → test → commit → push → PR, end to end |
| **incident-debug** | `/incident-debug` | Reproduce → `git bisect` → root cause → fix → regression test |
| **legacy-rescue** | `/legacy-rescue` | Characterization tests around legacy code, then safe refactor |
| **feature-tdd** | `/feature-tdd` | Turn a spec into a tested, working feature, end to end |
| **audit-harden** | `/audit-harden` | Full security audit AND apply the fixes |
| **safe-upgrade** | `/safe-upgrade` | Bump a major dependency and fix every breakage, tests green |

**Git & workflow**
| Skill | Trigger | What it does |
|-------|---------|--------------|
| **commit-message** | `/commit-message` | Conventional Commits message from your staged diff |
| **pr-description** | `/pr-description` | PR title + description from your branch |
| **fix-conflicts** | `/fix-conflicts` | Resolve merge/rebase conflicts, keeping both sides' intent |
| **bisect-bug** | `/bisect-bug` | `git bisect` to find the commit that introduced a bug |
| **branch-cleanup** | `/branch-cleanup` | List & safely delete branches merged into main |
| **changelog-entry** | `/changelog-entry` | Keep-a-Changelog entry from commits since the last tag |

**Code quality & review**
| Skill | Trigger | What it does |
|-------|---------|--------------|
| **review-diff** | `/review-diff` | Bug/edge-case/security review of uncommitted changes |
| **security-scan** | `/security-scan` | Scan the whole repo for secrets, injection, unsafe input |
| **debug-error** | `/debug-error` | Paste an error → root cause + fix |
| **find-dead-code** | `/find-dead-code` | Locate unused functions, exports, and files |
| **lint-fix** | `/lint-fix` | Run the project's linter/formatter and fix issues |
| **safe-refactor** | `/safe-refactor` | Refactor with zero behavior change, verified by tests |
| **add-types** | `/add-types` | Add TypeScript types / Python type hints to a file |

**Testing**
| Skill | Trigger | What it does |
|-------|---------|--------------|
| **test-first** | `/test-first` | Write a failing test, then implement until it passes |
| **test-coverage** | `/test-coverage` | Find untested code and add meaningful tests |

**Docs & knowledge**
| Skill | Trigger | What it does |
|-------|---------|--------------|
| **explain-codebase** | `/explain-codebase` | Concise map of an unfamiliar repo |
| **add-docstrings** | `/add-docstrings` | Document a file's public API in the project's style |
| **readme-generator** | `/readme-generator` | Generate/update the project README from the real code |
| **adr** | `/adr` | Write an Architecture Decision Record with trade-offs |

**Project setup**
| Skill | Trigger | What it does |
|-------|---------|--------------|
| **gitignore-gen** | `/gitignore-gen` | `.gitignore` tailored to your stack |
| **dockerfile-gen** | `/dockerfile-gen` | Production-ready Dockerfile + `.dockerignore` |
| **ci-setup** | `/ci-setup` | GitHub Actions workflow: install, lint, test |
| **env-example** | `/env-example` | `.env.example` from every env var the code reads |
| **dependency-audit** | `/dependency-audit` | Find outdated/vulnerable deps & propose safe updates |
| **migration-writer** | `/migration-writer` | Write a DB migration matching your tool |
| **regex-builder** | `/regex-builder` | Build, explain & test a regex from plain English |

## Install (30 seconds)

**Per project** (recommended — share with your team):
1. Copy the `skills/` folders into your project's `.claude/skills/` directory:
   ```
   your-project/.claude/skills/commit-message/SKILL.md
   your-project/.claude/skills/pr-description/SKILL.md
   ...
   ```
2. Open Claude Code in that project.
3. Type `/` and you'll see the skills. Run one, e.g. `/review-diff`.

**For all your projects** (just you): copy the same folders into `~/.claude/skills/`
(your home directory's `.claude/skills/`) instead.

> The command name comes from the **folder name** (e.g. the `commit-message/` folder
> gives `/commit-message`). Keep each skill in its own folder with its `SKILL.md`.

## Use

Just type the slash command in Claude Code. Some accept an argument:
```
/test-first the date parser crashes on empty strings
/safe-refactor src/billing/proration.ts
/changelog-entry 1.4.0
```

## How they work

Each `SKILL.md` has a short YAML header (`name`, `description`) and a body of
instructions Claude follows when you trigger it. They tell Claude exactly which git
commands to run and what to produce — so you get consistent results every time.
Open any `SKILL.md` to read or tweak it; they're plain text, edit freely.

## Tips

- These work best in a **git** project (most read your diff or history).
- Edit any skill to match your team's conventions (commit style, changelog format).
- Combine them: `/test-first` → fix → `/review-diff` → `/commit-message` → `/pr-description`.

---

Single-user license. Redistribution or resale of these files is not permitted.
Questions: d3dprintix@outlook.com

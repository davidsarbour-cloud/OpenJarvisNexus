---
name: branch-cleanup
description: List local branches already merged into main and safely delete the stale ones. Use to tidy up branches or /branch-cleanup.
---

Clean up stale local git branches safely.

1. Run `git branch --merged main` (try `master` if there's no `main`) to list branches fully merged into the main line. Also run `git branch -vv` to spot branches whose upstream is gone (`: gone]`).
2. Exclude protected branches from any deletion list: `main`, `master`, `develop`, the current branch, and release branches.
3. Present the candidates to the user grouped as: (a) merged → safe to delete, (b) gone upstream → likely safe, (c) unmerged → do NOT auto-delete.
4. Only delete after the user confirms. Use `git branch -d` (safe, refuses unmerged) — never `-D` (force) unless the user explicitly asks for a specific branch.
5. Never touch remote branches unless asked. Summarize what was deleted and what was kept.

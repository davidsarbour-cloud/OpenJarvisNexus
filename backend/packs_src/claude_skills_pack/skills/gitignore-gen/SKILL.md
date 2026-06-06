---
name: gitignore-gen
description: Generate or improve a .gitignore tailored to the project's stack. Use when setting up a repo or /gitignore-gen.
---

Create a correct `.gitignore` for this project.

1. Detect the stack(s): language, framework, package manager, build tools, IDE files present in the repo.
2. Build a `.gitignore` covering: dependency dirs (node_modules, venv, target, vendor), build output (dist, build, *.pyc, __pycache__), env/secret files (.env, *.local), logs, OS cruft (.DS_Store, Thumbs.db), and editor folders (.vscode, .idea) — based on what actually applies here.
3. If a `.gitignore` already exists, merge in what's missing rather than overwriting — and flag any currently-tracked files that *should* be ignored (e.g. a committed `.env`).
4. Group entries with comment headers by category. Output the file content.
5. Warn the user if secrets or build artifacts are already committed (ignoring them now won't untrack them — they'd need `git rm --cached`).

---
name: explain-codebase
description: Produce a concise map of an unfamiliar codebase — entry points, main modules, and how a request flows through. Use when onboarding to a repo or running /explain-codebase.
---

Give a newcomer a usable map of this codebase — not an essay.

1. Identify the stack: look for package.json / pyproject.toml / go.mod / Cargo.toml / etc. and the README.
2. Find the entry points (main/index/app/cmd files, server bootstrap, CLI entry).
3. List the main modules/directories and what each is responsible for — one line each.
4. Trace one core flow end-to-end (e.g. "an HTTP request → router → handler → service → DB") in 4–6 steps.
5. Note the key commands (install, dev, test, build) from the config files.

Keep the whole map under ~30 lines. Prefer `file_path:line` references so the reader can jump in. Do not dump file contents.

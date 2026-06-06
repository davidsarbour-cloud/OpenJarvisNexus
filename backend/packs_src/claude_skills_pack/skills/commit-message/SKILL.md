---
name: commit-message
description: Write a clean Conventional Commits message from the current staged git diff. Use when the user asks for a commit message or runs /commit-message.
---

Generate a commit message for the **staged** changes.

1. Run `git diff --cached` to see what is staged. If nothing is staged, run `git diff` and say you're describing unstaged changes.
2. Write a message in **Conventional Commits** style:
   - First line: `type(scope): summary` — type is one of feat, fix, docs, refactor, test, chore, perf. Keep under 72 chars, imperative mood ("add", not "added").
   - Blank line, then a short body (2–4 bullets) explaining *what* and *why*, only if the change is non-trivial.
3. Do not invent changes you can't see in the diff. Describe only what's there.
4. Output ONLY the commit message in a code block, ready to copy.

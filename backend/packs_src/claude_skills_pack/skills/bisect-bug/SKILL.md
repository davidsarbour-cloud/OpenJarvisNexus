---
name: bisect-bug
description: Use git bisect to find the exact commit that introduced a bug. Use when a regression appeared and you need the culprit commit, or /bisect-bug.
argument-hint: "<how to tell if a commit is good or bad>"
---

Find the commit that introduced the regression via `git bisect`.

1. Get the test: from $ARGUMENTS, determine how to check whether a given commit is "good" (works) or "bad" (has the bug) — ideally a command that exits 0/non-0 (a test, a script, a build).
2. Ask the user for a known-good commit/tag (and the known-bad one, usually HEAD) if not provided.
3. Run the bisect:
   - `git bisect start`
   - `git bisect bad <bad>`
   - `git bisect good <good>`
   - At each step, run the check command, then `git bisect good` or `git bisect bad` accordingly. (If the check is scriptable, mention `git bisect run <cmd>` to automate it.)
4. When git reports the first bad commit, show it: `git show <sha>` — and explain what in that diff caused the bug.
5. Run `git bisect reset` to restore HEAD when done. Then propose the fix.

---
name: fix-conflicts
description: Resolve git merge or rebase conflicts in the working tree, preserving both sides' intent. Use during a conflicted merge/rebase or /fix-conflicts.
---

Resolve the current merge/rebase conflicts.

1. Run `git status` to list conflicted files, and `git diff` to see the conflict markers.
2. For each conflicted file, read the `<<<<<<<` / `=======` / `>>>>>>>` blocks and understand what *each* side was trying to do — check the surrounding code and recent commits if unclear.
3. Merge the intent of both sides — do not blindly pick one. The result must be correct, not just marker-free.
4. Remove all conflict markers. If a resolution is genuinely ambiguous, stop and ask the user which behavior they want rather than guessing.
5. After resolving, run the build/tests if available to confirm nothing broke.
6. Summarize each file's resolution. Do NOT run `git add`/`commit` unless the user asks — let them review first.

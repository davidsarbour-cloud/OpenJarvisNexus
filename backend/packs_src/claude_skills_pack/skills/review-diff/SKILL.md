---
name: review-diff
description: Review the current uncommitted changes for bugs, edge cases, and risky code before committing. Use when the user asks for a review or runs /review-diff.
---

Review the working-tree changes like a careful senior engineer.

1. Run `git diff` (and `git diff --cached`) to see all uncommitted changes.
2. Look specifically for:
   - **Bugs**: off-by-one, null/undefined, wrong operator, swapped args, await/async mistakes.
   - **Edge cases**: empty inputs, large inputs, concurrency, error paths not handled.
   - **Security**: injection, secrets in code, unsafe deserialization, path traversal.
   - **Regressions**: behavior changes that could break callers.
3. Report findings as a list. For each: `file:line` — what's wrong — suggested fix. Be specific.
4. Order by severity (blocking first). If you find nothing serious, say so plainly rather than inventing nitpicks.

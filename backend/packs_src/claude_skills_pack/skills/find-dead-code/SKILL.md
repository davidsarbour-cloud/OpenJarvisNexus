---
name: find-dead-code
description: Find unused functions, exports, variables, and files in the codebase. Use to spot dead code or /find-dead-code.
---

Locate dead (unused) code in this project.

1. Identify exported/public symbols (functions, classes, constants) and entry points.
2. For each candidate, search the codebase for references (`grep` the symbol name). A symbol with no references outside its own definition is likely dead.
3. Watch for false positives: dynamic usage (reflection, string-based dispatch, DI containers), public API meant for external consumers, test-only helpers, and framework entry points (routes, CLI commands, event handlers). When in doubt, flag as "possibly unused" rather than "dead".
4. Also note: unreachable branches, commented-out blocks, and orphaned files no module imports.
5. Report findings as a list: `file:line` — symbol — confidence (likely dead / possibly unused) — why. Recommend, don't delete — let the user confirm before removing anything.

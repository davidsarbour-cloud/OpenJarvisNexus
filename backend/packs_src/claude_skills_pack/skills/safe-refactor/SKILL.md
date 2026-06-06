---
name: safe-refactor
description: Refactor code within a tight scope without changing behavior, verified by tests. Use when the user wants to clean up code safely or runs /safe-refactor.
argument-hint: "<file or area to refactor>"
---

Refactor the target in $ARGUMENTS with zero behavior change.

1. First, read the target and its tests. If there are no tests covering it, say so and offer to add a characterization test before refactoring.
2. State the refactor plan in 2–3 bullets before editing (what improves, what stays identical).
3. Make the change in **small steps**, keeping the public interface and observable behavior identical.
4. Run the test suite after the change. If anything fails, the refactor is wrong — revert that step.
5. Do NOT add features, change behavior, or "improve" things outside the stated scope. Refactor means same behavior, cleaner code.
6. Summarize what changed and confirm tests still pass.

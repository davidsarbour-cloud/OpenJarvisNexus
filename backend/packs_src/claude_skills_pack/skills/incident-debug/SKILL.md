---
name: incident-debug
description: Full incident workflow for a regression — reproduce, find the commit that caused it, fix the root cause, and add a regression test. Use for "this used to work" bugs or /incident-debug.
argument-hint: "<describe the broken behavior>"
---

Run the complete regression workflow for the bug in $ARGUMENTS (ask if empty).

1. **Reproduce** — establish a reliable way to trigger the bug: a failing test, a script, or exact steps with expected vs actual. Confirm you can reproduce it before going further.
2. **Locate the cause** — if it's a regression, use `git bisect` against the reproduce check to find the first bad commit (`git bisect start` / `bad` / `good`, run the check each step, `git bisect reset` when done). Otherwise trace the code path from the symptom to the source.
3. **Root cause** — explain in 1–2 sentences *why* the commit/code causes the bug. Don't fix until you can name the cause.
4. **Fix** — apply the minimal correct fix (the cause, not the symptom).
5. **Regression test** — add a test that fails without the fix and passes with it, so this exact bug can't return silently.
6. **Verify** — run the full suite; confirm the new test passes and nothing else broke.

End with: reproduce method, culprit (commit/code), root cause, the fix, and the regression test added.

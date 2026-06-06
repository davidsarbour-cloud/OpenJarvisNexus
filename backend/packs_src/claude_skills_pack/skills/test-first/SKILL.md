---
name: test-first
description: Write a failing test that reproduces a bug or specifies a feature, confirm it fails, then implement until it passes. Use for TDD-style fixes or /test-first.
argument-hint: "<what to test / the bug>"
---

Drive the change test-first. The target is described in $ARGUMENTS (ask if empty).

1. Locate the existing test setup (test framework, where tests live, how they run). Match the project's conventions.
2. Write a **failing** test that captures the desired behavior or reproduces the bug. Make it precise.
3. Run the test suite and confirm the new test fails for the *right* reason. Show the failure.
4. Implement the minimal code change to make it pass — do not weaken the test to pass it.
5. Re-run the suite; confirm the new test passes and you didn't break others.
6. Summarize: the test added, the fix made, and the passing result.

---
name: test-coverage
description: Find untested code and add meaningful tests for it. Use to raise coverage or /test-coverage.
argument-hint: "[file or module to focus on]"
---

Find weakly-tested code and add real tests.

1. Detect the test framework and how tests run. If a coverage tool exists (`pytest --cov`, `jest --coverage`, `go test -cover`), run it to find untested lines; otherwise reason about which functions lack tests by reading the code and the existing tests.
2. Focus on $ARGUMENTS if given; otherwise prioritize core logic and error paths (not trivial getters).
3. Write tests that assert real behavior and cover the meaningful cases: happy path, edge cases (empty/large/boundary), and error handling. Match the project's test style and helpers.
4. Tests must be genuine — do not write assertions that always pass or that just restate the implementation. Each test should be able to *fail* if the code breaks.
5. Run the suite to confirm the new tests pass. Report what you added and the coverage gain if measurable.

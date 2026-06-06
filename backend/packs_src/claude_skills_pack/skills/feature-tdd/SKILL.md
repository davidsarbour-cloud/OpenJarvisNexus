---
name: feature-tdd
description: Turn a feature spec into working, tested code end-to-end using test-driven development. Use to build a new feature properly or /feature-tdd.
argument-hint: "<the feature to build>"
---

Build the feature described in $ARGUMENTS (ask for the spec if empty) test-first.

1. **Clarify the spec** — restate the feature as concrete, checkable acceptance criteria. If anything critical is ambiguous, ask before coding.
2. **Plan** — identify the files to create/change and the public interface. Keep it minimal — only what the spec needs.
3. **Red** — write tests for the acceptance criteria (happy path + key edge/error cases). Run them; confirm they fail for the right reason.
4. **Green** — implement the minimal code to make the tests pass. Match the project's conventions and reuse existing utilities.
5. **Refactor** — clean up the implementation with tests staying green.
6. **Integrate** — wire the feature in (routes, exports, config) and run the FULL suite to confirm no regressions.
7. Summarize: criteria covered, files changed, and the passing tests. Don't gold-plate — stop when the spec is met.

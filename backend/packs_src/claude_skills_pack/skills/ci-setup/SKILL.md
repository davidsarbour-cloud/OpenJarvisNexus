---
name: ci-setup
description: Scaffold a GitHub Actions CI workflow that installs, lints, and tests the project. Use to add CI or /ci-setup.
---

Create a CI workflow for this project (default: GitHub Actions).

1. Detect the stack, package manager, and the real install/lint/test/build commands from the project config.
2. Write `.github/workflows/ci.yml` that:
   - Triggers on push and pull_request to the main branch
   - Uses the correct setup action and pins the language version (read it from the project if specified)
   - Caches dependencies for speed
   - Runs install → lint → test (→ build if applicable), each as a clear step
3. Use a matrix only if the project targets multiple versions/OSes (don't over-engineer).
4. Use the actual commands — don't invent script names that aren't in the project. If a step (lint/test) doesn't exist yet, note it as a TODO rather than referencing a missing command.
5. Output the workflow file and a one-line summary of what it runs.

---
name: lint-fix
description: Run the project's linter/formatter and fix the issues it reports. Use to clean up lint errors or /lint-fix.
---

Lint the project and fix what it flags.

1. Detect the tooling from config files: ESLint (.eslintrc), Prettier, Ruff/flake8/black (pyproject/setup.cfg), gofmt/golangci-lint, rustfmt/clippy, etc.
2. Run the linter to get the actual list of issues. Run the auto-fixer first where it exists (`eslint --fix`, `ruff --fix`, `black .`, `gofmt -w`).
3. For issues the auto-fixer can't handle, fix them by hand — but only real issues, and without changing behavior.
4. Re-run the linter to confirm it's clean (or down to issues that need a human decision — list those).
5. Do not disable rules to silence errors unless the user asks. Summarize what was fixed.

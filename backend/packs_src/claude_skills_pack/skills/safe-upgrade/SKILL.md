---
name: safe-upgrade
description: Upgrade a major dependency and fix every breakage it causes, with tests green at the end. Use for a risky version bump or /safe-upgrade.
argument-hint: "<package to upgrade>"
---

Upgrade the dependency in $ARGUMENTS (ask which one if empty) safely.

1. **Baseline** — confirm the test suite is GREEN before you start. If it's already red, stop and say so — you can't tell upgrade breakage from pre-existing failures otherwise.
2. **Read the changelog** — find the target version's breaking changes / migration guide (the package's CHANGELOG or release notes). List the breaking changes that affect this codebase.
3. **Bump** — update the version in the manifest/lockfile and install.
4. **Fix breakages** — work through compile/type/test errors caused by the upgrade, applying the migration steps. Search the codebase for every usage of changed APIs — don't miss call sites.
5. **Verify** — run the full suite (and the app/build if feasible) until green. Re-run the type checker and linter.
6. **Report** — old → new version, the breaking changes handled, the files touched, and the green suite. Flag anything that needs manual QA (behavior that tests don't cover). Do this as its own commit so it's easy to review or revert.

---
name: dependency-audit
description: Check for outdated and vulnerable dependencies and propose safe updates. Use for a dependency review or /dependency-audit.
---

Audit this project's dependencies.

1. Detect the package manager from lockfiles: npm/pnpm/yarn (package.json), pip/poetry/uv (requirements/pyproject), cargo, go modules, etc.
2. Run the native audit/outdated command for that ecosystem, e.g.:
   - Node: `npm outdated` and `npm audit`
   - Python: `pip list --outdated` (and `pip-audit` if available)
   - Rust: `cargo outdated`, Go: `go list -m -u all`
3. Summarize: which packages are outdated (current → latest), and which have known vulnerabilities (severity).
4. Recommend updates in order of priority: security fixes first, then majors that need care (flag breaking-change risk), then safe minors/patches.
5. Do NOT bulk-upgrade blindly. Propose the changes; apply only what the user approves, and run tests after.

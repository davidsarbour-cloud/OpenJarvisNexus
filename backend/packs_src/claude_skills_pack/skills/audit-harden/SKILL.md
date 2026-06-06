---
name: audit-harden
description: Full security audit of the codebase AND apply the fixes, with tests to confirm nothing broke. Use to harden a project or /audit-harden.
---

Audit this project for security issues and fix them.

1. **Audit** — scan for: hardcoded secrets, injection (SQL/shell/eval), unvalidated input reaching filesystem/network (path traversal, SSRF), unsafe deserialization, secrets logged or sent to clients, missing authn/authz checks, and known-vulnerable dependencies (run the ecosystem's audit tool).
2. **Triage** — rank findings by severity (critical → low) with `file:line` and the concrete risk. Show this list before changing anything.
3. **Fix, highest severity first** — apply the real fix for each (parameterized queries, input validation, move secrets to env, escape output, pin/upgrade deps). For each fix, explain what it prevents.
4. **Don't break behavior** — run the test suite after the fixes; if something breaks, the fix needs adjusting, not the test.
5. **Verify** — re-check that each finding is actually resolved.
6. Confirm with the user before changes that could alter runtime behavior (auth tightening, dependency majors). End with a before/after summary of findings fixed vs deferred.

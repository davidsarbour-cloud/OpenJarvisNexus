---
name: security-scan
description: Scan the codebase for common security issues — secrets, injection, unsafe input handling. Use for a security pass or /security-scan.
---

Audit this project for security problems like a security reviewer.

1. **Secrets**: grep for hardcoded keys, tokens, passwords, connection strings (e.g. `api_key`, `secret`, `password`, `BEGIN PRIVATE KEY`, `AKIA`). Flag anything that looks real and check it isn't committed.
2. **Injection**: look for string-built SQL queries, shell commands built from user input, `eval`/`exec`, and unescaped HTML rendering.
3. **Input handling**: unvalidated user input reaching the filesystem (path traversal), network (SSRF), or deserialization.
4. **Auth/secrets handling**: secrets logged, sent to the client, or stored in plaintext.
5. **Dependencies**: note obviously outdated/risky packages (suggest running the audit tool for the stack).

Report each finding as: severity — `file:line` — the issue — the fix. Be concrete. If the project is clean on a check, say so. Do not invent vulnerabilities.

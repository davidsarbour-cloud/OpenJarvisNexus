---
name: env-example
description: Generate a .env.example by finding every environment variable the code reads. Use to document config or /env-example.
---

Build a complete `.env.example` for this project.

1. Search the codebase for every environment variable access: `process.env.X`, `os.environ[...]` / `os.getenv`, `Deno.env`, `std::env::var`, framework config loaders, etc.
2. Collect the full set of variable names (dedupe). Cross-check any existing `.env` / `.env.example`.
3. For each variable, add a line `NAME=` with a comment describing what it's for and an example/placeholder value — inferred from how it's used in the code (URL, port, boolean, secret).
4. **Never copy real secret values** from an actual `.env` — use placeholders like `your-api-key-here`.
5. Group related vars with comment headers (database, auth, third-party APIs). Flag any variable the code requires but that has no default — those are mandatory. Output the `.env.example` content.

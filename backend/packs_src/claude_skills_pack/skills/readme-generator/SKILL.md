---
name: readme-generator
description: Generate or update a project README from the actual code and config. Use when a repo needs a README or runs /readme-generator.
---

Write a clear, accurate README for this project.

1. Detect the stack and purpose: read package.json / pyproject.toml / go.mod / Cargo.toml, the entry point, and any existing README.
2. Find the real commands (install, dev, test, build) from the config — do not guess them.
3. Produce a README with these sections:
   - **Title + one-line description** (what it does, for whom)
   - **Features** (3–6 bullets, only real ones)
   - **Install** (real commands)
   - **Usage** (a minimal real example)
   - **Configuration** (env vars / config files if any)
   - **Development** (run tests, build)
   - **License** (if a LICENSE file exists)
4. Base every claim on the actual code. If something is unknown, leave a clearly-marked `<!-- TODO -->` rather than inventing it. Output as `README.md` content.

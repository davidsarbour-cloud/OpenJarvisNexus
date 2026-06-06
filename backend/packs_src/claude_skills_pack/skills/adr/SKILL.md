---
name: adr
description: Write an Architecture Decision Record documenting a technical decision and its trade-offs. Use to record a decision or /adr.
argument-hint: "<the decision being made>"
---

Write an Architecture Decision Record (ADR) for the decision in $ARGUMENTS (ask if empty).

1. Check for an existing ADR folder (`docs/adr/`, `doc/decisions/`) and numbering — continue the sequence (e.g. `0007-use-postgres.md`). If none exists, create `docs/adr/0001-...`.
2. Use the standard ADR structure:
   - **Title** + status (Proposed / Accepted / Superseded)
   - **Context** — the forces and problem driving the decision
   - **Decision** — what was decided, stated plainly
   - **Alternatives considered** — the other options and why they were rejected
   - **Consequences** — the trade-offs accepted, both positive and negative
3. Be honest about downsides — an ADR that lists only upsides is useless. Keep it to one page.
4. Base the context on the actual project where possible. Output the ADR markdown file.

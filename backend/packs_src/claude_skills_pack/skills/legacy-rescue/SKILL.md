---
name: legacy-rescue
description: Safely improve untested legacy code by adding characterization tests first, THEN refactoring under that safety net. Use for risky old code or /legacy-rescue.
argument-hint: "<file or module to rescue>"
---

Rescue the legacy code in $ARGUMENTS (ask if empty) without breaking it.

1. **Understand current behavior** — read the code and map what it actually does, including the weird/edge behaviors. Do not assume intent; observe it.
2. **Characterization tests** — write tests that capture the code's CURRENT behavior exactly as-is (even quirks), so you have a safety net. These pin down behavior, not correctness. Run them — they should pass against the current code.
3. **Plan** — state in 2–3 bullets what you'll improve (readability, dead code, structure) while keeping behavior identical.
4. **Refactor in small steps** — after each step, re-run the characterization tests. Any failure means the step changed behavior — revert it.
5. **Only then** discuss fixing actual bugs (separately, with the user) — that's a behavior change and needs its own test update.
6. Keep the public interface stable. Summarize the tests added and the refactor done, with the suite green.

---
name: add-types
description: Add type annotations (TypeScript types or Python type hints) to a file without changing behavior. Use for typing a file or /add-types.
argument-hint: "<file path>"
---

Add precise type annotations to the file in $ARGUMENTS (ask if empty).

1. Detect the language and typing convention (TypeScript types/interfaces, or Python type hints + `typing`/`from __future__`). Match what the project already uses.
2. Add types to function parameters, return values, and important variables. Infer types from usage, call sites, and existing types — do not weaken everything to `any` / `Any`.
3. Prefer precise types: unions, generics, `Optional`/`| None`, literal types where appropriate. Reuse existing project types.
4. Do NOT change runtime behavior — annotations only (plus imports needed for the types).
5. If a type genuinely can't be determined, use the narrowest safe type and add a short comment. Run the type checker (`tsc --noEmit`, `mypy`, etc.) if available to confirm it's clean.

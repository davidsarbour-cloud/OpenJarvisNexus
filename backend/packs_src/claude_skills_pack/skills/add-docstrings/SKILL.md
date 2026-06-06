---
name: add-docstrings
description: Add clear docstrings/comments to a file's public functions and classes, matching the project's existing style. Use when documenting code or running /add-docstrings.
argument-hint: "<file path>"
---

Document the public surface of the file in $ARGUMENTS (ask if empty).

1. Read the file and a couple of already-documented files nearby to learn the project's docstring style (format, voice, tags).
2. Add or improve docstrings on **public** functions, classes, and modules. Cover: what it does, parameters, return value, and any important side effects or errors.
3. Match the existing convention exactly (e.g. Google/NumPy/JSDoc style). Do not invent a new format.
4. Do not change any code logic — comments and docstrings only.
5. Keep them concise and accurate. Skip trivial getters/obvious one-liners unless the project documents those too.

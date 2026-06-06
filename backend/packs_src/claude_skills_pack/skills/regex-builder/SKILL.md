---
name: regex-builder
description: Build, explain, and test a regular expression from a plain-English description. Use to write a regex or /regex-builder.
argument-hint: "<what the regex should match>"
---

Produce a correct regex for the requirement in $ARGUMENTS (ask if empty).

1. Restate what should match and what should NOT match, so the spec is clear.
2. Write the regex for the target language/flavor (JS, Python `re`, PCRE, Go — ask if unclear; defaults differ on lookbehind, named groups, escaping).
3. Explain it piece by piece so the user can maintain it.
4. Give a short test table: 3–5 strings that should match and 2–3 that should not, with the expected result for each.
5. If the project has the file where it'll be used, drop it in with the correct escaping for that language's string literals. Warn about catastrophic backtracking if the pattern risks it.

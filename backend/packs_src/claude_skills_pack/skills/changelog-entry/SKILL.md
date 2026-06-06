---
name: changelog-entry
description: Generate a Keep-a-Changelog entry from recent commits since the last tag. Use when preparing a release or running /changelog-entry.
argument-hint: "[version number]"
---

Write a changelog entry from recent history.

1. Find the range: run `git describe --tags --abbrev=0` for the last tag, then `git log <tag>..HEAD --oneline`. If there's no tag, use the last ~20 commits.
2. Group the commits under **Keep a Changelog** headings — Added, Changed, Fixed, Removed, Security — based on what each commit actually did.
3. Each line: user-facing, one sentence, imperative. Skip noise (merge commits, "wip", formatting-only).
4. Header: `## [<version>] — <today's date>`. Use the version from $ARGUMENTS if given, else leave a `[Unreleased]` placeholder.
5. Output only the markdown changelog block, ready to paste into CHANGELOG.md.

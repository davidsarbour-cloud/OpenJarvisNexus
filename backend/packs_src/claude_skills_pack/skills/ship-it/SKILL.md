---
name: ship-it
description: Take working changes all the way to a ready-to-merge PR — review, fix, test, commit, push, PR. Use when the user says "ship it", "finish this up", or runs /ship-it.
argument-hint: "[optional PR focus note]"
---

Drive the current changes from "done coding" to "ready to merge". Work the stages in order and STOP at any stage that fails until it's resolved.

1. **Review** — run `git diff` (and `--cached`) and review for bugs, edge cases, and security issues. List what you find.
2. **Fix** — fix the real issues you found. Skip pure style nits unless asked.
3. **Test** — run the project's test suite and linter. If anything fails, fix it. Do not proceed with a red suite.
4. **Stage & commit** — stage the changes and write a Conventional Commits message describing what and why. Show it before committing.
5. **Branch check** — if currently on the main/master branch, create a feature branch first (never commit straight to main).
6. **Push** — push the branch to the remote with upstream tracking.
7. **PR** — produce a PR title + description (Summary, Changes, Testing). If `gh` CLI is available, offer to open the PR with it; otherwise output the text to paste.

Confirm with the user before the irreversible steps (push, opening the PR). Report a short summary of each stage at the end. Honor the focus note in $ARGUMENTS for the PR write-up.

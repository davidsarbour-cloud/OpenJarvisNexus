---
name: pr-description
description: Draft a pull-request title and description from the changes on the current branch. Use when the user asks for a PR write-up or runs /pr-description.
argument-hint: "[optional focus note]"
---

Draft a pull-request title and description for the current branch.

1. Find the changes: run `git diff main...HEAD` (fall back to `git diff master...HEAD`, then `git diff --cached`). Run `git log --oneline main..HEAD` for the commit list.
2. Produce:
   - **Title**: one concise line, imperative mood.
   - **Summary**: 2–4 sentences on what changed and why.
   - **Changes**: a short bullet list of the notable changes.
   - **Testing**: how it was or should be verified.
3. If the user passed a focus note in $ARGUMENTS, emphasize that aspect.
4. Base everything on the real diff — do not fabricate features. Output as markdown ready to paste into the PR.

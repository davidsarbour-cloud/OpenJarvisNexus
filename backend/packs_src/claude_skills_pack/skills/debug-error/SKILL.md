---
name: debug-error
description: Find the root cause of an error or stack trace and fix it. Use when the user pastes an error, a failing log, or runs /debug-error.
argument-hint: "<paste the error / stack trace>"
---

Diagnose and fix the error described in $ARGUMENTS (ask the user to paste it if empty).

1. Read the error carefully: identify the exception type, the message, and the top frame in YOUR code (skip library frames).
2. Open the file and line the trace points to. Read the surrounding code and the values involved.
3. Form the most likely root cause — state it in one sentence before changing anything.
4. Trace backwards: what input or state produced it? Check callers if needed.
5. Apply the minimal fix that addresses the cause (not just the symptom). Add a guard or test if the bug could recur.
6. If you can run the failing path (a test, a script), run it to confirm the fix. Explain the cause and the fix in 2–3 sentences.

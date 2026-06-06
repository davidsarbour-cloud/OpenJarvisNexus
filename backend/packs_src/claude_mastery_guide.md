# The Claude Mastery Guide
### Get expert results from Claude — models, prompting, projects, MCP & the API

*A small, accurate, no-fluff guide. Every section is a real Claude capability with
exactly how to use it and a concrete example. Works for Claude.ai, Claude Code, and
the API. Current as of 2026.*

> This guide teaches the durable skills (prompting, projects, cost control) **and**
> the current specifics (model IDs, pricing, API parameters) so you stop guessing
> and start getting expert output on the first try.

---

## HOW TO USE THIS GUIDE

1. Part 1 makes you fluent in *what Claude is* (models, surfaces).
2. Part 2 is the core: **prompting that actually works**.
3. Part 3–5 go deeper: Projects/Memory, MCP, and the API for builders.
4. The **Prompt Template Library** at the end is copy-paste ready.

---

# PART 1 — KNOW YOUR TOOL

### 1. The Claude model family (pick the right one)

As of 2026, three current models — match the model to the job:

| Model | Model ID | Context | Price (in / out per 1M tokens) | Use it for |
|-------|----------|---------|--------------------------------|------------|
| **Claude Opus 4.8** | `claude-opus-4-8` | 1M | $5 / $25 | Hardest reasoning, long agentic work, coding, deep research |
| **Claude Sonnet 4.6** | `claude-sonnet-4-6` | 1M | $3 / $15 | Best speed/intelligence balance — most production work |
| **Claude Haiku 4.5** | `claude-haiku-4-5` | 200K | $1 / $5 | Fast, cheap, simple tasks (classification, quick edits) |

**Rule:** start on Opus for anything hard, drop to Sonnet for volume, Haiku for simple/fast.
**Pro tip:** "1M context" = ~750,000 words in one prompt. You rarely need it — but it's there for whole codebases or long documents.

---

### 2. The four places you use Claude

| Surface | What it is | Best for |
|---------|-----------|----------|
| **Claude.ai** | The chat app | Everyday questions, writing, analysis, Artifacts |
| **Projects** | Chats + your files + custom instructions, grouped | Recurring work with shared context |
| **Claude Code** | Terminal coding agent | Building, editing, and running code |
| **API / SDK** | `messages.create()` | Putting Claude inside your own apps |

**Pro tip:** the same prompting skills work everywhere. Learn them once (Part 2), apply them in all four.

---

# PART 2 — PROMPTING THAT ACTUALLY WORKS

### 3. Be specific — say what "done" looks like

**What it does:** removes guesswork so Claude hits your target on the first try.
**Do this — replace vague with concrete:**
```
Vague:  "Make this email better."
Better: "Rewrite this email to be 3 short paragraphs, friendly but professional,
         with a clear call-to-action to book a call. Keep it under 120 words."
```
**Pro tip:** state the audience, the length, the tone, and the format. Four constraints beat a paragraph of vague hope.

---

### 4. Give an example (one good example beats ten rules)

**What it does:** shows Claude the exact shape of output you want.
**Do this:**
```
Turn these notes into a changelog entry. Match this format exactly:

## v1.4.0 — 2026-06-05
### Added
- <feature, one line, user-facing>
### Fixed
- <fix, one line>

Notes: <paste your rough notes>
```
**Pro tip:** "match this format exactly" + a sample is the single highest-leverage prompting move.

---

### 5. Use XML tags to separate instructions from data

**What it does:** prevents Claude from confusing *your data* with *your instructions*.
**Do this:**
```
Summarize the review below in one sentence.

<review>
{paste the customer review here}
</review>
```
**Pro tip:** tags like `<document>`, `<example>`, `<context>` make long prompts far more reliable. Claude was trained to respect them.

---

### 6. Set the role with a system prompt

**What it does:** the system prompt is a persistent instruction that shapes *how* Claude responds, separate from your question.
**Do this (in the API or a Project's custom instructions):**
```
You are a senior copy editor. You fix grammar and clarity but never change the
author's voice or meaning. You explain each change in one short note.
```
**Pro tip:** put *durable* rules (role, tone, do's and don'ts) in the system prompt; put the *task* in your message. Don't mix them.

---

### 7. Let it think for hard problems

**What it does:** asking Claude to reason step by step before answering improves accuracy on complex tasks.
**Do this:**
```
Think through the trade-offs before recommending. Consider cost, maintenance,
and team skill. Then give your recommendation in 3 bullets.
```
**Pro tip:** on the API, the latest Opus models think *adaptively* — they decide how much to think on their own. You steer depth with the **effort** setting (see #18), not a manual token budget.

---

### 8. Ask for the format you'll actually use

**What it does:** gets output you can paste straight into your tool — table, JSON, markdown, bullets.
**Do this:**
```
Return the result as a markdown table with columns: Name | Risk | Action.
No preamble — just the table.
```
**Pro tip:** "No preamble — just the X" stops the "Sure! Here's..." opener when you want clean output.

---

### 9. Iterate in the same chat — don't restart

**What it does:** Claude remembers the whole conversation, so refining is cheaper than re-explaining.
**Do this:**
```
Good. Now make it 30% shorter and add a stat in the first line.
```
**Pro tip:** treat it like editing with a colleague. Small follow-ups ("tighter", "more formal", "add an example") converge fast.

---

### 10. Give it the source, not your summary

**What it does:** Claude reasons better from raw material than from your paraphrase.
**Do this:** paste the actual error log, the real contract, the full thread — inside `<tags>` — and ask your question.
**Pro tip:** if it's long, that's fine — the context window is huge. Don't pre-summarize and lose detail.

---

### 11. When output is wrong, correct the instruction — not just the output

**What it does:** fixes the root cause so it doesn't recur.
**Do this:**
```
You keep using passive voice. From now on: active voice only, and never start
a sentence with "There is/are".
```
**Pro tip:** a sharper instruction fixes every future response; editing one output fixes only that one.

---

# PART 3 — PROJECTS & MEMORY

### 12. Use Projects for recurring work

**What it does:** a Project bundles custom instructions + reference files so every chat in it starts with your context loaded.
**When to use:** anything you do repeatedly — a client, a codebase, a writing style.
**Do this:** create a Project, add your style guide / brand docs / specs as knowledge, write custom instructions once.
**Pro tip:** stop re-pasting the same background into every chat. Put it in the Project once.

---

### 13. Curate Project knowledge — quality over quantity

**What it does:** Claude pulls from the files you add; clean, relevant files give sharper answers.
**Pro tip:** a few accurate, current documents beat a dump of everything. Remove stale files — outdated context produces outdated answers.

---

### 14. In Claude Code, your memory file is `CLAUDE.md`

**What it does:** `CLAUDE.md` is persistent project context loaded every session.
**Do this:** run `/init` once to generate it, keep it short (commands, conventions, architecture).
**Pro tip:** add a rule instantly by starting a line with `#` in Claude Code — it saves to memory for next time.

---

# PART 4 — CONNECT CLAUDE TO YOUR TOOLS (MCP)

### 15. MCP plugs external tools and data into Claude

**What it does:** the Model Context Protocol lets Claude use connectors — Google Drive, GitHub, databases, your own servers — as live tools.
**When to use:** when Claude needs *your* live data or needs to *take actions* outside the chat.
**Do this:** add a connector in Claude's settings (or `claude mcp add` in Claude Code), then just ask:
```
Find the 5 newest rows in the orders table and summarize them.
```
**Pro tip:** connectors turn Claude from "knows about your stuff" into "can actually act on your stuff."

---

### 16. Be explicit about which tool to use

**What it does:** with several connectors active, naming the source removes ambiguity.
**Do this:**
```
Using the GitHub connector, list open PRs older than 7 days.
```
**Pro tip:** name the connector and the action. Vague asks make Claude guess which tool you meant.

---

# PART 5 — THE API (FOR BUILDERS)

### 17. The one endpoint: Messages

**What it does:** everything goes through `messages.create()` — chat, tools, structured output.
**Do this (Python):**
```python
import anthropic
client = anthropic.Anthropic()

resp = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=16000,
    system="You are a concise assistant.",
    messages=[{"role": "user", "content": "Explain MCP in 2 sentences."}],
)
print(resp.content[0].text)
```
**Pro tip:** `system` = persistent role, `messages` = the conversation, `max_tokens` = the output cap. Set `max_tokens` generously (~16000) so answers don't truncate.

---

### 18. Control depth with effort (not temperature)

**What it does:** on the latest Opus, **effort** sets how hard Claude thinks and works.
**Do this:**
```python
resp = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=16000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},   # low | medium | high | xhigh | max
    messages=[{"role": "user", "content": "Design a rate limiter."}],
)
```
**Pro tip:** `high` is the sweet spot; `xhigh`/`max` for the hardest coding; `low` for simple/fast. Note: on Opus 4.8/4.7 the old `temperature` and manual thinking-budget knobs are gone — you steer with **effort** and clear prompting.

---

### 19. Stream long responses

**What it does:** streaming shows output token-by-token and avoids timeouts on big generations.
**Do this:**
```python
with client.messages.stream(
    model="claude-opus-4-8", max_tokens=64000,
    messages=[{"role": "user", "content": "Write the full spec."}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```
**Pro tip:** always stream when `max_tokens` is large (> ~16000) — non-streamed big requests can hit HTTP timeouts.

---

### 20. Get structured JSON you can trust

**What it does:** constrains the response to a schema so you get valid, parseable JSON every time.
**Do this:**
```python
resp = client.messages.create(
    model="claude-opus-4-8", max_tokens=2000,
    messages=[{"role": "user", "content": "Extract name and email: Jane, jane@co.com"}],
    output_config={"format": {"type": "json_schema", "schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
        "required": ["name", "email"], "additionalProperties": False,
    }}},
)
```
**Pro tip:** this replaces the old "prefill the assistant turn with `{`" trick (which now errors on the latest models). Use schemas instead.

---

### 21. Give Claude tools (function calling)

**What it does:** you define tools; Claude decides when to call them and you run them.
**Do this:** pass a `tools` list with a JSON `input_schema`; loop until `stop_reason != "tool_use"`.
**Pro tip:** write the tool **description** to say *when* to call it ("Call this when the user asks about current prices"), not just what it does — the latest models reach for tools more deliberately.

---

# PART 6 — SPEND LESS, GET MORE

### 22. Prompt caching — up to 90% off repeated context

**What it does:** caches a large, stable prefix (system prompt, big document) so repeat requests are far cheaper and faster.
**Do this:**
```python
resp = client.messages.create(
    model="claude-opus-4-8", max_tokens=16000,
    cache_control={"type": "ephemeral"},   # caches the stable prefix
    system=big_document_text,
    messages=[{"role": "user", "content": "Question 1 about the doc"}],
)
```
**Key facts:** prefix-match (any change near the front breaks it), default 5-minute TTL (`"ttl": "1h"` for an hour), max 4 cache points, minimum ~4096 tokens to cache on Opus.
**Pro tip:** keep volatile bits (timestamps, the changing question) at the **end**, stable context at the **front**, or caching silently won't trigger.

---

### 23. Batch API — 50% off non-urgent work

**What it does:** submit up to 100,000 requests to run asynchronously at half price.
**When to use:** bulk classification, enrichment, generation you don't need *right now* (most finish within an hour).
**Pro tip:** anything not latency-sensitive should go through Batches. It's the easiest 50% you'll ever save.

---

### 24. Count tokens before you send

**What it does:** `count_tokens` gives the exact Claude token count so you can predict cost.
**Do this:**
```python
n = client.messages.count_tokens(
    model="claude-opus-4-8",
    messages=[{"role": "user", "content": open("doc.md").read()}],
).input_tokens
```
**Pro tip:** don't estimate with OpenAI's `tiktoken` — it undercounts Claude by 15–20%. Use `count_tokens`.

---

# COMMON MISTAKES (avoid these)

1. **Vague prompts** — "improve this" gives generic output. Specify done-conditions.
2. **Restarting instead of refining** — you lose context. Iterate in the same chat.
3. **Pre-summarizing your source** — you throw away the detail Claude needs. Paste the raw material.
4. **Mixing data and instructions** — wrap data in `<tags>`.
5. **Using Opus for everything** — Haiku/Sonnet are cheaper for simple/volume work.
6. **Ignoring caching/batch** — you're overpaying 2–10× on repeated or bulk work.
7. **Estimating tokens with tiktoken** — wrong for Claude; use `count_tokens`.
8. **Reaching for `temperature`/`budget_tokens` on the latest Opus** — removed; steer with `effort` and prompting.

---

# PROMPT TEMPLATE LIBRARY (copy-paste)

**Rewrite with constraints**
```
Rewrite the text below. Constraints: <length> · <tone> · <audience> · <format>.
Keep the original meaning. <text>...</text>
```

**Extract to a table**
```
From the text below, extract <fields> into a markdown table. One row per <item>.
No preamble. <text>...</text>
```

**Explain like I decide**
```
Explain <topic> for someone who has to make a decision about it. Cover what it is,
when to use it, the main trade-off, and a one-line recommendation. Under 150 words.
```

**Critique then improve**
```
First list the 3 biggest weaknesses of the draft below. Then rewrite it fixing them.
Show the weaknesses, then the rewrite. <draft>...</draft>
```

**Role + task (system prompt)**
```
SYSTEM: You are a <role>. You always <key behavior> and never <forbidden behavior>.
USER: <the actual task>
```

**Step-by-step reasoning**
```
Work through this step by step before answering. Show your reasoning, then give the
final answer on its own line prefixed with "ANSWER:". <problem>...</problem>
```

---

*Single-user license. Built for people who want expert output from Claude without the trial and error.*
*Questions: d3dprintix@outlook.com*

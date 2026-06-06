# The Complete Claude Guide
### Every Feature. Every Tool. Every Strategy.

*Your friendly, complete map to everything Claude — written so a total beginner can follow
it, and accurate enough that a pro can trust it. No padding, no hype, no invented features.*

> **New to AI?** You're in the right place. Every technical word is explained in plain
> language the first time it appears, in a box like this one. Read the parts in order and
> you'll go from "what is this?" to "I can actually use this" — and even "I can earn with it."

---

## How this guide is organized

- **Part 1 — Getting your bearings:** what Claude is, the models, and the plans.
- **Part 2 — Using Claude every day:** prompting, Projects, Artifacts, connectors, research.
- **Part 3 — Claude for code:** Claude Code, explained gently.
- **Part 4 — Making money with Claude:** business prompts, real projects, honest income.
- **Part 5 — Quick reference:** templates, cheat sheet, and mistakes to avoid.

Total: 17 short chapters. Take them one at a time.

---

# PART 1 — GETTING YOUR BEARINGS

## 1. What is Claude — and the four ways to use it

Claude is an AI assistant built by Anthropic. You talk to it in ordinary English and it
helps you think, write, analyze, research, and build. Picture a brilliant, patient colleague
who has read an enormous amount, works fast, and never gets tired or annoyed.

**What can you actually do with it?** A lot, but here are the everyday wins:
- Write and rewrite (emails, posts, docs, resumes) in any tone.
- Summarize long things (reports, threads, PDFs) into the parts that matter.
- Explain hard topics simply, or go deep when you want.
- Analyze data, spot patterns, and draft conclusions.
- Research a question and come back with a sourced answer.
- Write, fix, and explain code — even if you don't code.
- Build small tools and apps without setting anything up.

**The four "doors" into Claude.** It's the same Claude behind each — you just pick the door
that fits what you're doing:

| The door | In plain words | Use it when you want to… |
|----------|----------------|---------------------------|
| **claude.ai** | The chat app (browser, desktop, phone) | Ask, write, analyze, research — daily use |
| **Projects** | A workspace of chats that share your files + rules | Do the *same kind* of work repeatedly |
| **Claude Code** | Claude inside your computer's terminal | Build and edit real software |
| **The API** | A way to put Claude *inside* your own app | Automate tasks or build a product to sell |

Most people start at **claude.ai**, graduate to **Projects** for recurring work, and only
touch **Claude Code** or **the API** when they want to build. The single most valuable skill —
talking to Claude well (Part 2) — works identically at every door, so it's never wasted effort.

---

## 2. The models — choosing the right "brain"

Claude comes in three "sizes." Bigger isn't automatically better — you choose based on the
job, the way you'd choose a vehicle: a race car for the track, a van for moving house, a
scooter for a quick errand.

- **Opus — the powerhouse.** The smartest. Use it for genuinely hard thinking, large coding
  jobs, and deep research. The trade-off: slower and more expensive.
- **Sonnet — the everyday champion.** Fast *and* smart, and cheaper than Opus. For most people,
  most of the time, this is the right default.
- **Haiku — the sprinter.** Built for simple, high-volume tasks where speed and low cost beat
  deep reasoning (sorting, quick replies, classifying).

The current versions, and what they cost **on the API** (per-token pricing — more in §3):

| Model | Context window* | Cost / 1M tokens (in / out) | Reach for it when… |
|-------|-----------------|------------------------------|--------------------|
| **Opus 4.8** `claude-opus-4-8` | 1,000,000 | $5 / $25 | The problem is genuinely hard |
| **Opus 4.7 / 4.6** | 1,000,000 | $5 / $25 | Previous-gen Opus, still excellent |
| **Sonnet 4.6** `claude-sonnet-4-6` | 1,000,000 | $3 / $15 | Your everyday default |
| **Haiku 4.5** `claude-haiku-4-5` | 200,000 | $1 / $5 | Simple, fast, and lots of it |

> **Jargon, explained — "token" and "context window."** A **token** is a small chunk of
> text, roughly ¾ of a word. You're billed by the token on the API. The **context window** is
> how much Claude can hold in mind at once. 1,000,000 tokens ≈ 750,000 words — that's an entire
> codebase, or a tall stack of documents, all in a single conversation.

**How to choose, simply:**
1. Start with **Sonnet**. It handles the vast majority of tasks beautifully.
2. Hitting a wall on something hard (complex reasoning, big refactor, deep research)? Switch up
   to **Opus**.
3. Doing something simple thousands of times (tagging, sorting, short replies)? Drop to **Haiku**
   to save time and money.

In the chat app you never type a model ID — you just pick **Opus** or **Sonnet** from a menu.
The exact IDs above only matter when you build on the API.

---

## 3. Plans & pricing — without the confusion

There are **two completely separate ways to pay**, and beginners constantly mix them up. Here's
the clean version.

### A) Subscriptions — for *using* the Claude app
A flat monthly fee, like a streaming service. You get access to chat, the top models, Projects,
connectors, and more — with higher limits as you go up:

| Plan | Who it's for | The idea |
|------|--------------|----------|
| **Free** | Curious first-timers | Try Claude with limited daily use |
| **Pro** | Daily individual users | Much higher limits, best models, Projects — the popular choice |
| **Max** | Heavy power users | The highest personal usage limits |
| **Team** | Small teams | Per-seat pricing, shared billing, collaboration |
| **Enterprise** | Companies | Single sign-on, admin controls, security & compliance |

> **An honest note on prices.** Plan names, limits, and prices change over time and vary by
> country. I won't print a dollar figure that could be wrong by the time you read this — instead,
> **check claude.ai/pricing for today's numbers.** What you actually need to know: most individuals
> are happiest on **Pro**; teams look at **Team**; companies look at **Enterprise**.

### B) Pay-as-you-go — for *building* with the API
Instead of a flat fee, you pay only for what you run, measured in tokens (the table in §2). If
you're putting Claude inside an app, a script, or an automation, this is your lane. Three easy
ways to keep the bill low (each explained later in this guide):
- **Pick the right model** — Haiku/Sonnet for simple/volume work; Opus only when needed.
- **Prompt caching** — reuse a big chunk of context and pay up to ~90% less for it.
- **Batch processing** — run non-urgent jobs in bulk at 50% off.

**The simple rule:** if you *use* Claude → take a subscription. If you *build* with Claude → use
the API. Many people do both, and that's completely normal.

---

# PART 2 — USING CLAUDE EVERY DAY

## 4. Prompt engineering — the one skill that changes everything

A **prompt** is simply the message you send Claude. "Prompt engineering" is just a fancy term for
*asking well*. Almost every "Claude didn't do what I wanted" moment is really an asking problem —
and the fixes are easy. Here are the six moves, each with the *why* and a quick before/after.

**1. Be specific about the finish line.** Claude can't read your mind, so describe the destination.
> ❌ "Make this email better."
> ✅ "Rewrite this email in 3 short paragraphs, friendly but professional, for a first-time customer,
> ending with a clear call to book a call. Keep it under 120 words."

The four dials to set every time: **audience, length, tone, format.**

**2. Show an example.** One sample of the output you want beats a paragraph describing it.
> "Turn these notes into a changelog. Match this format exactly:
> ## v1.2.0 — [date] / ### Added / - [one-line feature]. Notes: <notes>…</notes>"

**3. Separate your data from your instructions.** When you paste material in, wrap it so Claude
knows it's *content to work on*, not new orders. Tags work great:
> "Summarize the review below in one sentence. <review> …paste here… </review>"

**4. Give Claude a role.** A role sets the whole personality of the reply.
> "You are a meticulous copy editor. You fix grammar and clarity but never change my voice or
> meaning, and you note each change in one short line."

**5. Let it think on hard problems.** For anything tricky, invite reasoning before the answer.
> "Think through the trade-offs (cost, effort, risk) before you recommend, then give me 3 bullets."

**6. Ask for the exact format you'll use.** A table, an email, bullets — say so. Add "no preamble,
just the X" to skip the "Sure! Here's…" intro when you want clean output.

**The biggest beginner upgrade of all:** when a reply isn't perfect, **don't start over — refine in
the same chat.** Just say "tighter," "warmer," "add a statistic," "make it formal." Claude remembers
the whole conversation and converges fast. Treat it like editing with a colleague, not pulling a
slot-machine lever.

---

## 5. Projects & Memory — stop repeating yourself

Notice how you keep pasting the same background into Claude? **Projects** end that.

A Project is a saved workspace that holds two things: your **custom instructions** (your standing
rules) and **reference files** (your documents). Every chat you open inside the Project already
knows all of it — no re-explaining, ever.

**When to use one:** any work you do repeatedly — a specific client, a product, your brand's writing
voice, an ongoing study.

**Set one up in four steps:**
1. Create a new Project and give it a clear name.
2. Add knowledge files — your style guide, specs, brand docs, key references.
3. Write the custom instructions once (role, rules, do's and don'ts).
4. Start chatting. Everything in that Project inherits the context automatically.

**Example custom instructions:**
> "You are my marketing assistant for [Brand]. Always write in a warm, plain-spoken voice, never
> use buzzwords, and keep to British spelling. When I share a draft, improve it and explain your
> changes briefly."

**Keep it curated.** A handful of accurate, current files beats a giant dump — outdated files lead
to outdated answers. Remove stale documents as things change.

> **About "memory":** memory just means Claude carrying context so you don't repeat yourself.
> Projects are how you do that in the app. In Claude Code (Part 3), the same idea lives in a file
> called `CLAUDE.md`.

---

## 6. Artifacts — Claude builds it, live, beside the chat

**Artifacts** are a side panel where Claude builds something you can see and use immediately — a
formatted document, a chart, a diagram, or even a small **working app** (a real interactive page) —
with zero setup on your end.

**Try asking:**
- "Build a tip calculator as a little interactive app."
- "Make a clean one-page pricing site for [product]."
- "Turn this data into a bar chart with a short takeaway."

It appears in the Artifact panel, ready to use. Then you **refine by chatting**: "make the button
green," "add a dark mode," "make it mobile-friendly." Each request updates the artifact in place.

**Why beginners love it:** you go from an idea to a working thing in one conversation — no coding
environment, no installs, no setup.

**A worked example — a simple landing page in 3 messages:**
1. "Build a one-page landing site for a dog-walking service called PawPals. Hero, 3 benefits, a
   contact button. Friendly and clean."
2. "Make the colors warm — cream background, soft green accents."
3. "Add a short FAQ section with 3 questions."

You now have a shareable page. **When to graduate to Claude Code:** Artifacts are perfect for
prototypes and mockups; when you need real, maintainable, production software, move to Part 3.

---

## 7. Connectors (MCP) — let Claude reach your real tools

By default Claude works with what you type into the chat. **Connectors** let it reach into your
actual tools and data — so it can look things up and take actions for you.

> **Jargon, explained:** the technology powering connectors is called **MCP** (Model Context
> Protocol). You don't need the plumbing — just think "connectors."

**Popular connectors include:** Gmail, Google Drive, Google Calendar, Notion, GitHub, Slack, and
databases — plus many more, with new ones arriving regularly.

**How to use them:**
1. Turn on the connector you want in Claude's settings (you'll authorize access once).
2. Then just ask in plain English. Claude uses the connector as a tool.

**Example asks, per connector:**
- *Drive:* "Find the contract in my Drive and summarize the cancellation terms."
- *Gmail:* "Draft a reply to the latest email from [person], polite and brief."
- *Calendar:* "What does my Thursday look like, and suggest a 90-minute focus block."
- *Notion:* "Pull my project notes for [X] and turn them into a status update."

**One tip and one caution:**
- **Tip:** if several connectors are on, name the one you mean ("using the Notion connector, …") so
  Claude doesn't have to guess.
- **Caution:** you're giving Claude access to real accounts. Connect only what you need, and review
  actions that change or send things.

This is the leap from "Claude knows about things in general" to "Claude can act on *my* things."

---

## 8. Deep Research — a sourced report instead of a rabbit hole

When you need to actually research something, **Deep Research** sends Claude off to read across many
sources and come back with a structured, **citation-backed report** — in minutes, instead of an
afternoon of twenty open tabs.

**Perfect for:** "what are my best options for X," competitor scans, buying decisions, getting up to
speed on an unfamiliar topic, light literature reviews.

**How to get a genuinely good report — be specific about scope:**
> ❌ "Research project management tools."
> ✅ "Compare the 3 best project-management tools for a 5-person remote design studio under
> $15/user/month. Cover pricing, key features, and the main downside of each. Recommend one."

**What you get:** a written report with its reasoning and a list of sources you can click to verify.

**Always do this:** spot-check the cited sources for anything important. Deep Research is fast and
thorough, but you stay the editor-in-chief — trust, then verify.

---

# PART 3 — AI CODE AUTOMATION (Claude Code)

*Not a coder? You can skim this part — but Claude Code is the most powerful thing Claude does, so
it's worth knowing it exists and what it can do for you.*

## 9. Claude Code — the essentials

**Claude Code** is Claude living inside your computer's terminal, where it can read, write, run, and
fix real code in your project — like a tireless junior developer who has already read your entire
codebase.

**Your first ten minutes, step by step:**
1. **Open it in your project.** In a terminal, go to your project folder and type `claude`. Run it
   from the top of the project so it can see everything.
2. **Give it a memory.** Type `/init`. Claude reads your project and writes a `CLAUDE.md` file —
   notes it loads every session, so you never re-explain your setup. You can add a rule anytime by
   starting a line with `#` (e.g. "# always use pnpm, never npm").
3. **Ask in plain English.** "Add input validation to the signup form, then show me what changed."
   Claude finds the right files, edits them, and reports back.
4. **Keep its head clear.** Type `/clear` when you switch to an unrelated task — a fresh start is
   faster and cheaper than a cluttered conversation. Use `/compact` to shrink a long session while
   keeping the gist.
5. **Look before it leaps.** Press **Shift+Tab** to reach "plan mode," where Claude proposes what it
   *would* do without touching anything. Approve the plan, then let it execute.

**Your safety net is Git.** Save your work (a "commit") before a big change. If you don't like what
Claude did, one command rewinds everything. That safety net is exactly what lets you experiment
boldly — you can always undo.

---

## 10. Customizing Claude Code — make it work your way

Claude Code becomes far more powerful once you tailor it. You don't need all of this on day one —
just know the toolbox exists:

**CLAUDE.md — standing rules and context.** Short notes Claude reads every time (commands,
conventions, "don't touch the generated files"). Keep it brief and accurate.

**Skills — a prompt you save and trigger with `/name`.** Anything you type more than twice becomes a
one-word command. A skill is a small markdown file in `.claude/skills/`:
```
.claude/skills/commit-message/SKILL.md
→ now you can type /commit-message
```

**Hooks — automatic actions at a chosen moment.** A hook runs a command for you — for example,
auto-format every file Claude edits, or block a dangerous command. Configured in
`.claude/settings.json`. Run `/hooks` to set them up without writing JSON by hand.

**Subagents — specialist helpers Claude delegates to.** A reviewer, a debugger, a test-writer — each
with its own focus. They live in `.claude/agents/` and Claude hands the right work to the right
specialist. Run `/agents` to create them.

**Connectors (MCP) — external tools and data.** The same idea as §7, inside your editor: add with
`claude mcp add` so Claude can reach GitHub, a database, and more.

**Rule of thumb:** a prompt you repeat → make it a **skill**. Something that must happen every single
time → make it a **hook**. Recurring specialized work → make a **subagent**.

---

## 11. Automation & headless — Claude on autopilot

Once you're comfortable, Claude Code can run **without you watching** — perfect for scripts, scheduled
jobs, and your team's pipeline.

**The one flag that unlocks it:** `-p` ("do this one thing, then finish").
```
claude -p "Summarize today's changes in changelog style" > notes.md
cat error.log | claude -p "what is the root cause of this error?"
```

**For automation that runs itself:**
- `--output-format json` → machine-readable output another script can read.
- `--allowedTools "Bash(npm test),Read"` → pre-approve exactly what a hands-off run may do (so it
  never stops to ask).
- Combine with your computer's scheduler (cron on Mac/Linux, Task Scheduler on Windows) for nightly
  jobs — auto-changelogs, health checks, draft commit messages in a git hook.

**A real example:** a git "prepare-commit-msg" hook that runs
`git diff --cached | claude -p "write a concise commit message for this diff"` so every commit gets a
clean message automatically. Start it as a suggestion you can edit, then trust it once it proves
itself.

---

# PART 4 — BUSINESS & INCOME

## 12. A business prompt starter kit

Real, copy-paste prompts grouped by job. Fill the [brackets] and send.

**Marketing — ad headlines**
```
Write 5 ad headlines for [product] aimed at [audience]. Angle: [main benefit].
Each under 12 words, no clichés. Then pick the strongest and tell me why.
```
**Sales — follow-up email**
```
Write a follow-up email to [prospect] who [what happened]. Goal: book a call.
Warm, 3 short paragraphs, one clear call-to-action, under 120 words.
```
**Operations — notes into action**
```
Turn these meeting notes into a table of action items (owner, task, due date).
Flag anything blocked. Notes: <notes> …paste… </notes>
```
**Hiring — job description**
```
Write a job post for [role] at a [type of company]: responsibilities, must-have
skills, nice-to-haves, and a short welcoming intro. Keep it scannable.
```
**Finance — explain the numbers**
```
From this data, compute [metrics] and explain the trend in 3 bullets a non-finance
person understands. Data: <data> …paste… </data>
```
**Customer support — reply**
```
Reply to this customer: acknowledge the issue, solve it or set expectations, warm and
jargon-free, end with one next step. Message: <message> …paste… </message>
```
**Content — repurpose**
```
Turn this article into: 1 LinkedIn post, 3 tweets, and a 50-word summary. Keep my voice.
Article: <article> …paste… </article>
```
**E-commerce — product copy**
```
Write a product description for [item]: a punchy first line, 3 benefit bullets, and a
short paragraph. Tone: [tone]. Include 5 SEO keywords naturally.
```

---

## 13. Five real projects you can actually build

Concrete, doable builds — each starts as a tiny version you can finish, then grow.

**1. A personal research assistant.** *What:* on-demand briefings on your topic. *You need:* a Project
with your sources + Deep Research. *Build the MVP:* create the Project, add 5 key sources, and ask it
for a weekly brief. *Extend:* add connectors so it pulls fresh material itself.

**2. A customer-support helper.** *What:* drafts answers in your voice. *You need:* your FAQ and docs.
*MVP:* paste your FAQ into a Project and have it draft replies to real questions. *Extend:* on the API,
use prompt caching so your docs are cheap to reuse on every ticket.

**3. A content machine.** *What:* one topic → outline → draft → social posts. *MVP:* a single chat that
takes a topic and returns all three. *Extend:* turn it into a Claude Code skill or an API workflow you
run on a schedule.

**4. A data helper.** *What:* upload a spreadsheet, get it cleaned, charted, and summarized. *MVP:* drop
a CSV into claude.ai and ask for the cleanup + a chart + a 3-bullet summary. *Extend:* automate it on the
API for recurring reports.

**5. A coding assistant.** *What:* reviews your changes and writes commit messages. *MVP:* in Claude
Code, ask it to review your diff before each commit. *Extend:* run it headless in CI to review every
pull request automatically.

**How to start any of them:** name the *input*, name the *output*, and the *one job* in between. Build
the smallest version that works, then add steps. Shipping a tiny thing beats planning a big one.

---

## 14. AI income — the honest playbook

No hype, no "get rich overnight." Here's how people genuinely earn with Claude, and the truth about each.

| Path | What it is | The honest reality |
|------|-----------|--------------------|
| **Digital products** | Sell guides, prompt packs, templates (like this one) on Etsy/Gumroad | Real, low cost to start; income follows *quality + marketing*, not luck |
| **AI services** | Done-for-you work (content, automation, chatbots) using Claude | The fastest near-term money — but it's a service business, not "passive" |
| **Productized tools** | A small tool people pay for monthly | Higher ceiling; needs upkeep |
| **Teaching / content** | Show others how to use Claude (video, blog) | Slow to build, compounds over time |

**Your first product in a weekend — a simple, honest path:**
1. **Pick one narrow, real need** you can solve (e.g. "Claude prompts for real-estate agents").
2. **Make it genuinely good** — accurate, specific, nicely formatted. Quality is your only moat.
3. **Package it** — a clean PDF + a short README + a simple cover image.
4. **List it** on Gumroad or Etsy with an honest description and a fair price.
5. **Anchor with a bundle** — sell the single product cheap as an entry point, and a bundle higher.
6. **Tell people** — share where your audience already is. Marketing is the real job; the product is
   the easy part.

**Four rules that actually matter:**
1. **Sell something real.** Accurate, useful products earn repeat buyers and good reviews. Padded
   "3000-in-1" filler earns refunds.
2. **"Passive" is mostly upfront work** — you build once, but you keep marketing.
3. **Pick one lane and ship it.** One finished product beats ten half-built ideas.
4. **Reuse your assets.** One pack can sell alone, inside a bundle, and (with resale rights) to other
   sellers — three income streams from one build.

---

# PART 5 — QUICK REFERENCE

## 15. Prompt template library

General-purpose shapes — fill in the blanks for almost any task:

```
REWRITE   "Rewrite this. Constraints: <length>, <tone>, <audience>, <format>.
           Keep the meaning. <text>…</text>"

EXTRACT   "Pull <fields> from the text into a table, one row per <item>.
           No preamble. <text>…</text>"

DECIDE    "Explain <topic> for someone deciding about it: what it is, when to use it,
           the main trade-off, and a one-line recommendation. Under 150 words."

IMPROVE   "List the 3 biggest weaknesses of this draft, then rewrite fixing them.
           <draft>…</draft>"

REASON    "Work through this step by step, show your reasoning, then put the final
           answer on its own line starting with ANSWER:. <problem>…</problem>"

SUMMARIZE "Summarize this for a busy [role] in 5 bullets, then one 'so what?' line.
           <content>…</content>"

TEACH     "Explain <topic> to a complete beginner using a simple analogy and one
           everyday example. No jargon."
```

## 16. Cheat sheets

**Choose a model:** Opus = hardest jobs · Sonnet = everyday default · Haiku = fast & cheap.
**Two ways to pay:** subscription to *use* Claude · API (per token) to *build* with it.
**API cost levers:** right model · prompt caching (~90% off repeated context) · Batch (50% off bulk).
**Prompt well:** be specific · show an example · separate data with tags · refine in the same chat.
**Claude Code first commands:** `/init` (memory) · `/clear` (fresh start) · `/compact` (shrink) ·
`/model` · `/agents` · `/hooks` · `/mcp`.
**Permission modes (Shift+Tab):** default → accept-edits → plan.
**Handy keys:** Shift+Tab (cycle mode) · Esc (interrupt) · ↑ (previous prompt).

## 17. Common mistakes (and the fix)

1. **Vague prompts** → state the audience, length, tone, and format.
2. **Starting over instead of refining** → keep going in the same chat; Claude remembers.
3. **Pre-summarizing your source** → paste the raw material; don't throw away the detail.
4. **Mixing data with instructions** → wrap your data in `<tags>`.
5. **Using Opus for everything** → Sonnet/Haiku are faster and cheaper for everyday and simple work.
6. **Ignoring caching/batch on the API** → you may be overpaying 2–10×.
7. **Over-trusting research** → always verify the cited sources for anything that matters.
8. **Connecting everything** → only enable the connectors you actually need.
9. **Selling filler to make a quick buck** → real, accurate products win long-term; padding gets refunds.

---

*Single-user license. The complete, accurate, beginner-friendly map of the Claude ecosystem —
built to be read and used, not padded to look thick.*
*Questions: d3dprintix@outlook.com*

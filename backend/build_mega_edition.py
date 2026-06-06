"""Build the all-in-one Claude Mega Edition: the guide + 32 skills + 14 agents +
business prompts + glossary + FAQ + real diagrams, as one big 12pt PDF."""

from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from build_pack import md_to_pdf, render_cover
from pack_common import hex_rgb as hx
from pack_common import load_font as F
from PIL import Image, ImageDraw

BACKEND = Path(__file__).resolve().parent
PSRC = BACKEND / "packs_src"
_JS = Path(os.getenv("JARVIS_STL_DIR", r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STL"))
JARVIS_AIPACK = Path(os.getenv("JARVIS_AIPACK_DIR", str(_JS.parent / "AIPacks")))

ACCENT = "#d97757"
KEY, TITLE, PRICE = "claude_mega_edition", "The Complete Claude OS — Mega Edition", 29.99

# ---------- diagram toolkit (light theme, print-friendly) ----------
# hx (hex->RGB) and F (font loader) come from pack_common.


ACC, DARK, GREY, CARD, BORD, BG = (
    hx("#d97757"),
    hx("#1b1f24"),
    hx("#6b7178"),
    hx("#f6f4f0"),
    hx("#e0ddd6"),
    (255, 255, 255),
)


def _wrap(d, s, font, maxw):
    out, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def _card(d, x0, y0, x1, y1, title, items, accent, f_t, f_i):
    d.rounded_rectangle(
        (x0, y0, x1, y1),
        radius=14,
        fill=CARD,
        outline=hx(accent) if isinstance(accent, str) else accent,
        width=3,
    )
    d.rounded_rectangle(
        (x0, y0, x1, y0 + 46), radius=14, fill=hx(accent) if isinstance(accent, str) else accent
    )
    d.rectangle((x0, y0 + 26, x1, y0 + 46), fill=hx(accent) if isinstance(accent, str) else accent)
    tw = d.textlength(title, font=f_t)
    d.text(((x0 + x1) / 2 - tw / 2, y0 + 10), title, font=f_t, fill=(255, 255, 255))
    yy = y0 + 60
    for it in items:
        for ln in _wrap(d, "• " + it, f_i, x1 - x0 - 28):
            d.text((x0 + 16, yy), ln, font=f_i, fill=DARK)
            yy += 26


def diagram_master(out):
    W, H = 1740, 1180
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h = F("arialbd.ttf", 46)
    f_sub = F("arial.ttf", 26)
    f_ct = F("arialbd.ttf", 24)
    f_it = F("arial.ttf", 21)
    f_sm = F("arialbd.ttf", 22)
    d.rounded_rectangle((40, 30, W - 40, 120), radius=16, fill=ACC)
    t = "THE COMPLETE CLAUDE OS"
    d.text((W / 2 - d.textlength(t, font=f_h) / 2, 50), t, font=f_h, fill=(255, 255, 255))
    d.text(
        (W / 2 - d.textlength("everything in this guide, on one page", font=f_sub) / 2, 150),
        "everything in this guide, on one page",
        font=f_sub,
        fill=GREY,
    )
    # 4 surfaces row
    surf = [
        "claude.ai\nthe chat app",
        "Projects\nshared context",
        "Claude Code\ncode in your terminal",
        "API\nbuild your own",
    ]
    sw = (W - 80 - 3 * 20) // 4
    for i, s in enumerate(surf):
        x0 = 40 + i * (sw + 20)
        d.rounded_rectangle((x0, 205, x0 + sw, 300), radius=12, fill=DARK)
        a, b = s.split("\n")
        d.text(
            (x0 + sw / 2 - d.textlength(a, font=f_sm) / 2, 222), a, font=f_sm, fill=(255, 255, 255)
        )
        d.text(
            (x0 + sw / 2 - d.textlength(b, font=f_it) / 2, 256), b, font=f_it, fill=hx("#c9b8a8")
        )
    d.text((40, 320), "4 WAYS IN  ·  same Claude behind each", font=f_it, fill=GREY)
    # 5 pillars
    pillars = [
        (
            "1 · ECOSYSTEM",
            "#d97757",
            ["3 models: Opus/Sonnet/Haiku", "Plans: Free→Enterprise", "API pay-per-token"],
        ),
        (
            "2 · DAILY USE",
            "#3fb950",
            [
                "Prompt engineering",
                "Projects & Memory",
                "Artifacts",
                "Connectors (MCP)",
                "Deep Research",
            ],
        ),
        (
            "3 · CODE",
            "#58a6ff",
            ["Claude Code essentials", "14 specialist Agents", "Automation & headless"],
        ),
        (
            "4 · SKILLS",
            "#bc8cff",
            ["32 ready skills", "S-tier flagships", "git · review · tests · setup"],
        ),
        (
            "5 · BUSINESS",
            "#e0a92e",
            ["Business prompts", "5 real projects", "Honest income playbook"],
        ),
    ]
    pw = (W - 80 - 4 * 18) // 5
    for i, (t2, col, items) in enumerate(pillars):
        x0 = 40 + i * (pw + 18)
        _card(d, x0, 370, x0 + pw, 1060, t2, items, col, f_ct, f_it)
    d.text(
        (
            W / 2
            - d.textlength("Read top-to-bottom once, then keep it as your map.", font=f_sub) / 2,
            1100,
        ),
        "Read top-to-bottom once, then keep it as your map.",
        font=f_sub,
        fill=GREY,
    )
    im.save(str(out))


def diagram_surfaces(out):
    W, H = 1740, 560
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h = F("arialbd.ttf", 34)
    f_ct = F("arialbd.ttf", 28)
    f_it = F("arial.ttf", 22)
    d.text((40, 30), "The 4 ways to use Claude — same brain, different door", font=f_h, fill=DARK)
    cards = [
        ("claude.ai", "The chat app (web / phone).", "Ask, write, analyse, research — daily use."),
        (
            "Projects",
            "A workspace of chats + your files & rules.",
            "Do the same kind of work repeatedly.",
        ),
        ("Claude Code", "Claude inside your terminal.", "Build and edit real software."),
        ("API", "Claude inside your own app.", "Automate tasks or build a product to sell."),
    ]
    cw = (W - 80 - 3 * 20) // 4
    for i, (t, a, b) in enumerate(cards):
        x0 = 40 + i * (cw + 20)
        d.rounded_rectangle((x0, 120, x0 + cw, 470), radius=14, fill=CARD, outline=ACC, width=3)
        d.rounded_rectangle((x0, 120, x0 + cw, 176), radius=14, fill=ACC)
        d.rectangle((x0, 150, x0 + cw, 176), fill=ACC)
        d.text(
            (x0 + cw / 2 - d.textlength(t, font=f_ct) / 2, 132), t, font=f_ct, fill=(255, 255, 255)
        )
        yy = 200
        for ln in _wrap(d, a, f_it, cw - 28):
            d.text((x0 + 16, yy), ln, font=f_it, fill=DARK)
            yy += 28
        yy += 10
        for ln in _wrap(d, b, f_it, cw - 28):
            d.text((x0 + 16, yy), ln, font=f_it, fill=GREY)
            yy += 28
    im.save(str(out))


def diagram_models(out):
    W, H = 1740, 520
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h = F("arialbd.ttf", 34)
    f_ct = F("arialbd.ttf", 30)
    f_it = F("arial.ttf", 23)
    f_q = F("arialbd.ttf", 22)
    d.text((40, 30), "Which model should I pick?", font=f_h, fill=DARK)
    cols = [
        (
            "HAIKU 4.5",
            "#3fb950",
            "Simple & high-volume?",
            "Fast and cheap. Sorting, tagging, quick replies.",
        ),
        (
            "SONNET 4.6",
            "#58a6ff",
            "Your everyday default",
            "Fast AND smart. Use this for most things.",
        ),
        ("OPUS 4.8", "#d97757", "Genuinely hard?", "Max intelligence. Big code, deep research."),
    ]
    cw = (W - 80 - 2 * 24) // 3
    for i, (t, col, q, b) in enumerate(cols):
        x0 = 40 + i * (cw + 24)
        c = hx(col)
        d.rounded_rectangle((x0, 110, x0 + cw, 150), radius=10, fill=c)
        d.text(
            (x0 + cw / 2 - d.textlength(q, font=f_q) / 2, 118), q, font=f_q, fill=(255, 255, 255)
        )
        d.line((x0 + cw / 2, 150, x0 + cw / 2, 180), fill=c, width=4)
        d.rounded_rectangle((x0, 180, x0 + cw, 470), radius=14, fill=CARD, outline=c, width=3)
        d.text((x0 + cw / 2 - d.textlength(t, font=f_ct) / 2, 200), t, font=f_ct, fill=c)
        yy = 260
        for ln in _wrap(d, b, f_it, cw - 28):
            d.text((x0 + 16, yy), ln, font=f_it, fill=DARK)
            yy += 30
    d.text(
        (40, 485),
        "Start on Sonnet. Move up to Opus when stuck; drop to Haiku for bulk.",
        font=f_it,
        fill=GREY,
    )
    im.save(str(out))


def diagram_extend(out):
    W, H = 1740, 500
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h = F("arialbd.ttf", 34)
    f_ct = F("arialbd.ttf", 25)
    f_it = F("arial.ttf", 21)
    d.text((40, 30), "5 ways to make Claude Code your own", font=f_h, fill=DARK)
    boxes = [
        ("CLAUDE.md", "Standing rules & project memory."),
        ("Skills", "A prompt you trigger with /name."),
        ("Hooks", "A command that runs automatically."),
        ("Agents", "Specialists Claude delegates to."),
        ("MCP", "External tools & data (connectors)."),
    ]
    bw = (W - 80 - 4 * 18) // 5
    for i, (t, b) in enumerate(boxes):
        x0 = 40 + i * (bw + 18)
        d.rounded_rectangle((x0, 120, x0 + bw, 440), radius=14, fill=CARD, outline=ACC, width=3)
        d.rounded_rectangle((x0, 120, x0 + bw, 170), radius=14, fill=ACC)
        d.rectangle((x0, 144, x0 + bw, 170), fill=ACC)
        d.text(
            (x0 + bw / 2 - d.textlength(t, font=f_ct) / 2, 130), t, font=f_ct, fill=(255, 255, 255)
        )
        yy = 192
        for ln in _wrap(d, b, f_it, bw - 26):
            d.text((x0 + 14, yy), ln, font=f_it, fill=DARK)
            yy += 28
    im.save(str(out))


# ---------- frontmatter parsing ----------
def parse_md(path):
    txt = path.read_text(encoding="utf-8")
    name = desc = model = ""
    m = re.search(r"^---\s*(.*?)\s*---", txt, re.S | re.M)
    if m:
        fm = m.group(1)
        for key, var in (("name", "name"), ("description", "desc"), ("model", "model")):
            mm = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
            if mm:
                v = mm.group(1).strip().strip('"').strip("'")
                if key == "name":
                    name = v
                elif key == "description":
                    desc = v
                else:
                    model = v
    return name, desc, model


def short_desc(desc):
    # cut at "Use when/Use for/Use to/Use proactively" to keep the "what it does" part
    for marker in (
        " Use when",
        " Use for",
        " Use to",
        " Use proactively",
        " Use during",
        " Use before",
    ):
        i = desc.find(marker)
        if i > 0:
            return desc[:i].strip()
    return desc.strip()


SKILL_GROUPS = [
    (
        "Flagship workflows (S-tier)",
        [
            "ship-it",
            "incident-debug",
            "legacy-rescue",
            "feature-tdd",
            "audit-harden",
            "safe-upgrade",
        ],
    ),
    (
        "Git & workflow",
        [
            "commit-message",
            "pr-description",
            "fix-conflicts",
            "bisect-bug",
            "branch-cleanup",
            "changelog-entry",
        ],
    ),
    (
        "Code quality & review",
        [
            "review-diff",
            "security-scan",
            "debug-error",
            "find-dead-code",
            "lint-fix",
            "safe-refactor",
            "add-types",
        ],
    ),
    ("Testing", ["test-first", "test-coverage"]),
    ("Docs & knowledge", ["explain-codebase", "add-docstrings", "readme-generator", "adr"]),
    (
        "Project setup",
        [
            "gitignore-gen",
            "dockerfile-gen",
            "ci-setup",
            "env-example",
            "dependency-audit",
            "migration-writer",
            "regex-builder",
        ],
    ),
]
AGENT_ORDER = [
    "code-reviewer",
    "security-auditor",
    "debugger",
    "performance-optimizer",
    "architect",
    "test-writer",
    "refactorer",
    "doc-writer",
    "api-designer",
    "database-expert",
    "devops-engineer",
    "frontend-specialist",
    "accessibility-auditor",
    "explorer",
]


def skills_catalog():
    sdir = PSRC / "claude_skills_pack" / "skills"
    by = {p.name: parse_md(p / "SKILL.md") for p in sdir.iterdir() if p.is_dir()}
    out = [
        "# PART 6 — YOUR SKILLS LIBRARY (32 skills)\n",
        "![Your 32 skills](diagram_skills.png)\n",
        "A *skill* is a prompt you save once and trigger with a slash command (`/name`). "
        "Drop these into `.claude/skills/` and they're one-word commands. The full installable "
        "files are in the `skills/` folder of this package. Here's the whole library:\n",
    ]
    for gname, keys in SKILL_GROUPS:
        out.append(f"\n## {gname}\n")
        out.append("| Skill | What it does | Trigger |\n|---|---|---|")
        for k in keys:
            if k in by:
                _, desc, _ = by[k]
                out.append(f"| **{k}** | {short_desc(desc)} | `/{k}` |")
        out.append("")
    return "\n".join(out)


def agents_catalog():
    adir = PSRC / "claude_agents_pack" / "agents"
    by = {p.stem: parse_md(p) for p in adir.glob("*.md")}
    out = [
        "\n# PART 7 — YOUR AGENT TEAM (14 specialists)\n",
        "![Your 14 agents](diagram_agents.png)\n",
        "An *agent* (subagent) is a focused specialist Claude hands work to — its own role, tools, "
        "and model. Drop these into `.claude/agents/` (installable files in the `agents/` folder) and "
        "Claude delegates the right job to the right specialist automatically.\n",
        "| Agent | What it specializes in | Model |\n|---|---|---|",
    ]
    for k in AGENT_ORDER:
        if k in by:
            _, desc, model = by[k]
            out.append(f"| **{k}** | {short_desc(desc)} | {model or 'inherit'} |")
    return "\n".join(out)


def diagram_skills(out):
    W, H = 1740, 640
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h = F("arialbd.ttf", 34)
    f_ct = F("arialbd.ttf", 23)
    f_it = F("arial.ttf", 19)
    f_n = F("arialbd.ttf", 60)
    d.text((40, 28), "32 skills, organized in 6 groups", font=f_h, fill=DARK)
    groups = [
        ("Flagship", "#d97757", "6"),
        ("Git & workflow", "#3fb950", "6"),
        ("Quality & review", "#58a6ff", "7"),
        ("Testing", "#bc8cff", "2"),
        ("Docs", "#e0a92e", "4"),
        ("Setup", "#ec6a5e", "7"),
    ]
    cw = (W - 80 - 5 * 16) // 6
    for i, (t, col, n) in enumerate(groups):
        x0 = 40 + i * (cw + 16)
        c = hx(col)
        d.rounded_rectangle((x0, 110, x0 + cw, 470), radius=14, fill=CARD, outline=c, width=3)
        d.rounded_rectangle((x0, 110, x0 + cw, 156), radius=14, fill=c)
        d.rectangle((x0, 134, x0 + cw, 156), fill=c)
        for ln in _wrap(d, t, f_ct, cw - 20):
            d.text(
                (x0 + cw / 2 - d.textlength(ln, font=f_ct) / 2, 120),
                ln,
                font=f_ct,
                fill=(255, 255, 255),
            )
            break
        d.text((x0 + cw / 2 - d.textlength(n, font=f_n) / 2, 250), n, font=f_n, fill=c)
        d.text(
            (x0 + cw / 2 - d.textlength("skills", font=f_it) / 2, 340),
            "skills",
            font=f_it,
            fill=GREY,
        )
    d.text(
        (40, 500),
        "Every skill is real and does something Claude Code can genuinely do — no filler.",
        font=f_it,
        fill=GREY,
    )
    im.save(str(out))


def diagram_agents(out):
    W, H = 1740, 560
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h = F("arialbd.ttf", 34)
    F("arial.ttf", 20)
    f_n = F("arialbd.ttf", 22)
    d.text((40, 28), "Your 14-specialist team", font=f_h, fill=DARK)
    names = AGENT_ORDER
    cols = 5
    bw = (W - 80 - (cols - 1) * 16) // cols
    bh = 110
    for i, k in enumerate(names):
        r, cc = divmod(i, cols)
        x0 = 40 + cc * (bw + 16)
        y0 = 100 + r * (bh + 16)
        d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=12, fill=CARD, outline=ACC, width=3)
        for ln in _wrap(d, k, f_n, bw - 20)[:2]:
            d.text((x0 + bw / 2 - d.textlength(ln, font=f_n) / 2, y0 + 34), ln, font=f_n, fill=DARK)
    im.save(str(out))


GLOSSARY = """
# PART 8 — PLAIN-ENGLISH GLOSSARY

Every term in this guide, in one place, explained simply.

| Term | In plain words |
|---|---|
| **Prompt** | The message you send Claude. |
| **Token** | A small chunk of text (~¾ of a word). You're billed per token on the API. |
| **Context window** | How much Claude can hold in mind at once (1M tokens ≈ 750,000 words). |
| **Model** | The "brain" you use — Opus (powerful), Sonnet (everyday), Haiku (fast). |
| **LLM** | "Large Language Model" — the kind of AI Claude is. |
| **API** | A way for *programs* to talk to Claude, so you can build apps & automations. |
| **SDK** | A ready-made code library that makes using the API easy. |
| **MCP / Connector** | The tech that lets Claude reach your tools (Gmail, Drive, Notion…). |
| **Artifact** | A document/app Claude builds in a side panel you can use right away. |
| **Project** | A workspace that shares your files + rules across many chats. |
| **CLAUDE.md** | A notes file Claude Code reads every session (project memory). |
| **Skill** | A saved prompt you trigger with `/name` in Claude Code. |
| **Hook** | A command that runs automatically at a chosen moment (e.g. format on save). |
| **Subagent / Agent** | A specialist Claude delegates work to (reviewer, debugger…). |
| **Headless** | Running Claude with no chat window, for scripts (the `-p` flag). |
| **Prompt caching** | Reusing a big chunk of context cheaply (up to ~90% off) on the API. |
| **Batch** | Running many API jobs together at 50% off when you're not in a hurry. |
"""

FAQ = """
# PART 9 — BEGINNER FAQ

**Do I need to know how to code?**
No. Most of this guide (Parts 1, 2, 4) needs zero coding. Part 3 (Claude Code) is for when you
*want* to build software — and even then Claude does the coding; you describe what you want.

**Which plan should I get?**
If you're an individual using the app daily, **Pro** is the usual pick. Teams look at **Team**,
companies at **Enterprise**. Check claude.ai/pricing for current numbers.

**API or subscription — what's the difference?**
A subscription is for *using* the Claude app (flat monthly fee). The API is for *building* with
Claude inside your own apps (pay per use). Many people use both.

**Which model should I use?**
Start with **Sonnet** — it handles almost everything. Move up to **Opus** for hard problems; drop
to **Haiku** for simple, high-volume tasks.

**My answers aren't great — what am I doing wrong?**
Usually the prompt. Be specific (audience, length, tone, format), show an example, and refine in
the same chat instead of starting over. See Part 2, Chapter 4.

**Is my data safe / private?**
Review Anthropic's current privacy and data policies for your plan. As a rule: don't paste
secrets you wouldn't want stored, and only connect the tools you actually need.

**Can Claude access the internet / my files?**
Not by default — it works with what you give it. **Connectors** (Chapter 7) let it reach your
tools, and **Deep Research** (Chapter 8) lets it search the web, when you turn those on.

**How do I actually make money with this?**
Sell something real and specific (a guide, a prompt pack, a service), package it well, list it,
and market it. See Chapter 14 — it's an honest playbook, not a get-rich scheme.

**What's the difference between a skill and an agent?**
A **skill** is a command *you* trigger (`/commit-message`). An **agent** is a specialist *Claude*
hands work to on its own. This package includes 32 skills and 14 agents.

**Will this stay accurate? Models change fast.**
The durable skills (prompting, projects, selling) don't change. The specifics (model names, prices)
do — this edition is current for 2026, and we flag anything you should double-check live.
"""

# ---------- assemble ----------
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
base = f"{KEY}_{ts}"
out_dir = BACKEND / "aipack_output" / base
if out_dir.exists():
    shutil.rmtree(out_dir)
out_dir.mkdir(parents=True, exist_ok=True)

# diagrams
diagram_master(out_dir / "diagram_master.png")
diagram_surfaces(out_dir / "diagram_surfaces.png")
diagram_models(out_dir / "diagram_models.png")
diagram_extend(out_dir / "diagram_extend.png")
diagram_skills(out_dir / "diagram_skills.png")
diagram_agents(out_dir / "diagram_agents.png")

# guide body
guide = (PSRC / "claude_complete_guide.md").read_text(encoding="utf-8")
guide = guide.split("\n", 1)[1]  # drop the H1 title line (we add our own)
guide = guide.split("*Single-user license.", 1)[0]  # drop trailing footer
# inject diagrams after key headers
guide = guide.replace(
    "# PART 1 — GETTING YOUR BEARINGS",
    "# PART 1 — GETTING YOUR BEARINGS\n\n![The 4 ways to use Claude](diagram_surfaces.png)",
)
guide = guide.replace(
    '## 2. The models — choosing the right "brain"',
    '## 2. The models — choosing the right "brain"\n\n![Which model to pick](diagram_models.png)',
)
guide = guide.replace(
    "# PART 3 — AI CODE AUTOMATION (Claude Code)",
    "# PART 3 — AI CODE AUTOMATION (Claude Code)\n\n![Ways to extend Claude Code](diagram_extend.png)",
)

header = (
    "# The Complete Claude OS — Mega Edition\n"
    "### Every Feature. Every Tool. Every Strategy. — plus 32 Skills & 14 Agents.\n\n"
    "*The all-in-one: the complete beginner-friendly guide, your full skills library, your "
    "agent team, business prompts, a glossary and an FAQ — one package, everything in it.*\n\n"
    "![The Complete Claude OS — everything in this guide](diagram_master.png)\n\n---\n"
)

mega_md = "\n".join(
    [
        header,
        guide,
        skills_catalog(),
        agents_catalog(),
        GLOSSARY,
        FAQ,
        "\n---\n\n*Single-user license. The complete Claude ecosystem in one place — "
        "built to be read and used. Questions: d3dprintix@outlook.com*\n",
    ]
)
(out_dir / f"{KEY}.md").write_text(mega_md, encoding="utf-8")

# copy installable skills/ and agents/
shutil.copytree(PSRC / "claude_skills_pack" / "skills", out_dir / "skills")
shutil.copytree(PSRC / "claude_agents_pack" / "agents", out_dir / "agents")

has_pdf = md_to_pdf(
    mega_md, out_dir / f"{KEY}.pdf", accent=ACCENT, font_size=12, base_dir=str(out_dir)
)

(out_dir / "START_HERE.txt").write_text(
    f"{TITLE}\n\nThe all-in-one Claude package. START HERE:\n"
    f"1. Open {KEY}.pdf — the full illustrated guide (models, prompting, Projects, Artifacts, MCP,\n"
    "   Deep Research, Claude Code), PLUS your 32 skills and 14 agents documented, a glossary & FAQ.\n"
    "2. To USE the skills/agents: copy the skills/ and agents/ folders into your project's .claude/\n"
    "   (or ~/.claude/). They work as /commands and auto-delegated specialists.\n\n"
    "Single-user license. Questions: d3dprintix@outlook.com\n",
    encoding="utf-8",
)
(out_dir / "LICENSE.txt").write_text(
    "Single-user license. Use this package for your own work. Redistribution or resale of the "
    "files is not permitted.\n",
    encoding="utf-8",
)
(out_dir / "listing.json").write_text(
    json.dumps(
        {
            "title": TITLE,
            "price_usd": PRICE,
            "pack": KEY,
            "has_pdf": has_pdf,
            "includes": {
                "guide_chapters": 17,
                "skills": 32,
                "agents": 14,
                "diagrams": 6,
                "glossary": True,
                "faq": True,
            },
            "tags": [
                "claude ai",
                "claude code",
                "claude guide",
                "ai agents",
                "claude skills",
                "prompt engineering",
                "mcp",
                "ai automation",
                "anthropic",
                "ai ebook",
                "beginners",
                "all in one",
            ],
            "blurb": "The complete all-in-one Claude package: a beginner-friendly illustrated guide to the entire "
            "ecosystem (models, plans, prompting, Projects, Artifacts, MCP, Deep Research, Claude Code), "
            "PLUS 32 ready-to-use skills and 14 specialist agents (installable files included), business "
            "prompts, a glossary and an FAQ. Real diagrams, no filler.",
            "draft": False,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

render_cover(
    TITLE, "Guide + 32 Skills + 14 Agents + Prompts", "ALL-IN-ONE  ·  2026", ACCENT, out_dir
)

zip_path = out_dir.parent / f"{base}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for f in out_dir.rglob("*"):
        if f.is_file():
            z.write(f, f.relative_to(out_dir))
JARVIS_AIPACK.mkdir(parents=True, exist_ok=True)
jz = JARVIS_AIPACK / f"{base}.zip"
shutil.copy2(zip_path, jz)
print(json.dumps({"dir": str(out_dir), "zip": str(jz), "has_pdf": has_pdf}, indent=2))

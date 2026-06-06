"""Render the Complete Claude Guide structure as an org-tree diagram, light + dark, English."""

import sys
from pathlib import Path

from pack_common import hex_rgb as hx
from pack_common import load_font as fnt
from PIL import Image, ImageDraw

PARTS = [
    (
        "PART 1  —  THE CLAUDE ECOSYSTEM",
        "#d97757",
        [
            ("1", "What Claude is + the 4 surfaces (claude.ai · Projects · Claude Code · API)"),
            ("2", "All models explained (Opus 4.8/4.7/4.6 · Sonnet 4.6 · Haiku 4.5)"),
            ("3", "Plans & pricing (Free · Pro · Max · Team · Enterprise + API per token)"),
        ],
    ),
    (
        "PART 2  —  MASTERING CLAUDE.AI",
        "#3fb950",
        [
            ("4", "Prompt engineering that works"),
            ("5", "Projects & Memory"),
            ("6", "Artifacts (apps/tools inside Claude, zero code)"),
            ("7", "MCP Connectors (Gmail, Drive, Notion, Calendar…)"),
            ("8", "Deep Research mode (sourced reports)"),
        ],
    ),
    (
        "PART 3  —  AI CODE AUTOMATION (Claude Code)",
        "#58a6ff",
        [
            ("9", "Claude Code essentials"),
            ("10", "Customizing it (commands · hooks · subagents · MCP)"),
            ("11", "Automation & headless"),
        ],
    ),
    (
        "PART 4  —  BUSINESS & MONEY",
        "#e0a92e",
        [
            ("12", "Business prompts (by function: marketing, sales, ops, HR…)"),
            ("13", "Real-world AI projects (5 concrete projects to build)"),
            ("14", "AI passive income (honest playbook: products & services)"),
        ],
    ),
    (
        "PART 5  —  REFERENCE",
        "#bc8cff",
        [
            ("15", "Prompt template library"),
            ("16", "Cheat sheets (models · pricing · commands)"),
            ("17", "Common mistakes"),
        ],
    ),
]

THEMES = {
    "light": dict(
        bg=(255, 255, 255),
        root_fill=hx("#1b1f24"),
        root_text=(255, 255, 255),
        root_sub=hx("#d9b8a8"),
        line=hx("#c9c4ba"),
        chap=hx("#1b1f24"),
    ),
    "dark": dict(
        bg=hx("#0e1117"),
        root_fill=hx("#d97757"),
        root_text=(255, 255, 255),
        root_sub=hx("#3a2a22"),
        line=hx("#3a4048"),
        chap=hx("#e6edf3"),
    ),
}


def render(theme_name, out_path):
    th = THEMES[theme_name]
    f_root = fnt("arialbd.ttf", 40)
    f_rsub = fnt("arial.ttf", 24)
    f_ph = fnt("arialbd.ttf", 27)
    f_cn = fnt("arialbd.ttf", 23)
    f_ct = fnt("arial.ttf", 23)
    W = 1560
    PART_H = 64
    CH_H = 52
    PART_GAP = 26
    CH_GAP = 8
    y = 170
    total = y
    for _, _, chs in PARTS:
        total += PART_H + 10 + len(chs) * (CH_H + CH_GAP) + PART_GAP
    H = total + 40
    im = Image.new("RGB", (W, H), th["bg"])
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((60, 30, W - 60, 140), radius=18, fill=th["root_fill"])
    t = "THE COMPLETE CLAUDE GUIDE"
    d.text((W / 2 - d.textlength(t, font=f_root) / 2, 48), t, font=f_root, fill=th["root_text"])
    s = "the all-in-one that beats the competition"
    d.text((W / 2 - d.textlength(s, font=f_rsub) / 2, 100), s, font=f_rsub, fill=th["root_sub"])
    trunk_x = 90
    y = 170
    last_cy = 0
    for pname, col, chs in PARTS:
        c = hx(col)
        p_top = y
        p_cy = y + PART_H // 2
        d.line((trunk_x, p_cy, 130, p_cy), fill=th["line"], width=3)
        d.rounded_rectangle((130, p_top, W - 60, p_top + PART_H), radius=12, fill=c)
        d.text((150, p_top + PART_H // 2 - 15), pname, font=f_ph, fill=(255, 255, 255))
        last_cy = p_cy
        y += PART_H + 10
        sub_x = 200
        sub_top = p_top + PART_H
        cys = []
        for num, txt in chs:
            cy = y + CH_H // 2
            cys.append(cy)
            d.line((sub_x, cy, 236, cy), fill=th["line"], width=2)
            d.rounded_rectangle((236, y + 8, 236 + 54, y + CH_H - 8), radius=9, fill=c)
            d.text(
                (236 + 27 - d.textlength(num, font=f_cn) / 2, y + CH_H // 2 - 15),
                num,
                font=f_cn,
                fill=(255, 255, 255),
            )
            d.text((310, y + CH_H // 2 - 15), txt, font=f_ct, fill=th["chap"])
            y += CH_H + CH_GAP
        if cys:
            d.line((sub_x, sub_top, sub_x, cys[-1]), fill=th["line"], width=2)
        y += PART_GAP
    d.line((trunk_x, 140, trunk_x, last_cy), fill=th["line"], width=3)
    im.save(str(out_path))
    print("saved", out_path, im.size)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    target.mkdir(parents=True, exist_ok=True)
    render("light", target / "schema_tree_light.png")
    render("dark", target / "schema_tree_dark.png")

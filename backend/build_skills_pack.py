"""Package the claude_skills_pack folder (README + skills/*/SKILL.md) into a sellable atom zip."""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from build_pack import md_to_pdf, render_cover  # reuse cover + PDF renderers

BACKEND_DIR = Path(__file__).resolve().parent
SRC = BACKEND_DIR / "packs_src" / "claude_skills_pack"
_JARVIS_STL = Path(os.getenv("JARVIS_STL_DIR", r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STL"))
JARVIS_AIPACK_DIR = Path(os.getenv("JARVIS_AIPACK_DIR", str(_JARVIS_STL.parent / "AIPacks")))

KEY = "claude_skills_pack"
TITLE = "Claude Skills Pack"
PRICE = 16.99

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
base = f"{KEY}_{ts}"
out_dir = BACKEND_DIR / "aipack_output" / base
if out_dir.exists():
    shutil.rmtree(out_dir)
out_dir.mkdir(parents=True, exist_ok=True)

# copy README + skills/ (preserve structure)
shutil.copy2(SRC / "README.md", out_dir / "README.md")
shutil.copytree(SRC / "skills", out_dir / "skills")

skill_dirs = sorted(p for p in (out_dir / "skills").iterdir() if p.is_dir())
n_skills = len(skill_dirs)

# Build a printable PDF catalogue: the README + every skill's full SKILL.md.
catalog = [
    (SRC / "README.md").read_text(encoding="utf-8"),
    "\n\n---\n\n# Full Skill Reference\n\n*The exact contents of every SKILL.md in this pack.*\n",
]
for sd in skill_dirs:
    body = (sd / "SKILL.md").read_text(encoding="utf-8")
    catalog.append(f"\n\n## skills/{sd.name}/SKILL.md\n\n```markdown\n{body}\n```\n")
catalog_md = "".join(catalog)
has_pdf = md_to_pdf(catalog_md, out_dir / f"{KEY}.pdf")

(out_dir / "START_HERE.txt").write_text(
    f"{TITLE} — {n_skills} ready-to-use Claude Code skills\n\n"
    "START HERE:\n"
    "1. Open README.md (or claude_skills_pack.pdf) — 30-second install + full reference.\n"
    "2. Copy the skills/ folders into your project's .claude/skills/ (or ~/.claude/skills/).\n"
    "3. In Claude Code, type / and run one, e.g. /review-diff.\n\n"
    "Single-user license. Questions: d3dprintix@outlook.com\n",
    encoding="utf-8",
)
(out_dir / "LICENSE.txt").write_text(
    "Single-user license. Use these skills for your own work. "
    "Redistribution or resale of the files is not permitted.\n",
    encoding="utf-8",
)
(out_dir / "listing.json").write_text(
    json.dumps(
        {
            "title": TITLE,
            "price_usd": PRICE,
            "pack": KEY,
            "skill_count": n_skills,
            "has_pdf": has_pdf,
            "tags": [
                "claude code",
                "claude ai",
                "ai agents",
                "developer tools",
                "claude skills",
                "coding automation",
                "anthropic",
                "git",
                "productivity",
                "programmer gift",
            ],
            "blurb": f"{n_skills} ready-to-use Claude Code skills (SKILL.md) across git, code review, security, "
            "testing, docs and project setup — commit messages, PR descriptions, code review, security scan, "
            "debug, refactor, types, tests, Dockerfile, CI, and more. Drop into .claude/skills/ and trigger "
            "with a slash command.",
            "draft": False,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

render_cover(
    TITLE,
    f"{n_skills} ready-to-use Claude Code skills",
    f"INSTALL IN 30s  ·  {n_skills} SKILLS",
    "#bc8cff",
    out_dir,
)

zip_path = out_dir.parent / f"{base}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for f in out_dir.rglob("*"):
        if f.is_file():
            z.write(f, f.relative_to(out_dir))

JARVIS_AIPACK_DIR.mkdir(parents=True, exist_ok=True)
jarvis_zip = JARVIS_AIPACK_DIR / f"{base}.zip"
shutil.copy2(zip_path, jarvis_zip)
print(
    json.dumps(
        {"dir": str(out_dir), "zip": str(jarvis_zip), "skills": n_skills, "has_pdf": has_pdf},
        indent=2,
    )
)

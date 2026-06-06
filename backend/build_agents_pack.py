"""Package the claude_agents_pack folder (agents/*.md + README + MRR license) into a sellable atom zip."""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from build_pack import md_to_pdf, render_cover

BACKEND_DIR = Path(__file__).resolve().parent
SRC = BACKEND_DIR / "packs_src" / "claude_agents_pack"
_JARVIS_STL = Path(os.getenv("JARVIS_STL_DIR", r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STL"))
JARVIS_AIPACK_DIR = Path(os.getenv("JARVIS_AIPACK_DIR", str(_JARVIS_STL.parent / "AIPacks")))

KEY = "claude_agents_pack"
TITLE = "Claude Agents Pack"
PRICE = 14.99

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
base = f"{KEY}_{ts}"
out_dir = BACKEND_DIR / "aipack_output" / base
if out_dir.exists():
    shutil.rmtree(out_dir)
out_dir.mkdir(parents=True, exist_ok=True)

# copy README + MRR files + agents/ (preserve structure)
for fname in ("README.md", "RESELL_LICENSE.txt", "RESELLER_KIT.md"):
    shutil.copy2(SRC / fname, out_dir / fname)
shutil.copytree(SRC / "agents", out_dir / "agents")

agent_files = sorted(p for p in (out_dir / "agents").iterdir() if p.suffix == ".md")
n_agents = len(agent_files)

# PDF catalogue: README + every agent's full definition
catalog = [
    (SRC / "README.md").read_text(encoding="utf-8"),
    "\n\n---\n\n# Full Agent Reference\n\n*The exact contents of every agent file in this pack.*\n",
]
for af in agent_files:
    catalog.append(
        f"\n\n## agents/{af.name}\n\n```markdown\n{af.read_text(encoding='utf-8')}\n```\n"
    )
has_pdf = md_to_pdf("".join(catalog), out_dir / f"{KEY}.pdf")

(out_dir / "START_HERE.txt").write_text(
    f"{TITLE} — {n_agents} specialized Claude Code subagents (with Master Resell Rights)\n\n"
    "START HERE:\n"
    "1. Open README.md (or claude_agents_pack.pdf) — 30-second install + the full team.\n"
    "2. Copy the agents/ files into your project's .claude/agents/ (or ~/.claude/agents/).\n"
    "3. In Claude Code, run /agents to see them. Claude delegates to them automatically.\n\n"
    "RESELL: this pack includes Master Resell Rights — see RESELL_LICENSE.txt and RESELLER_KIT.md.\n"
    "Questions: d3dprintix@outlook.com\n",
    encoding="utf-8",
)

(out_dir / "listing.json").write_text(
    json.dumps(
        {
            "title": TITLE,
            "price_usd": PRICE,
            "pack": KEY,
            "agent_count": n_agents,
            "has_pdf": has_pdf,
            "resell_rights": "MRR",
            "tags": [
                "claude code",
                "claude ai",
                "ai agents",
                "subagents",
                "developer tools",
                "ai coding",
                "anthropic",
                "coding automation",
                "ai assistant",
                "resell rights",
            ],
            "blurb": f"{n_agents} ready-to-use Claude Code subagents (.claude/agents/*.md): code reviewer, "
            "security auditor, debugger, architect, test writer, DevOps, database expert, frontend, "
            "a11y, and more. Claude delegates to the right specialist automatically. Includes PDF "
            "catalogue and Master Resell Rights.",
            "draft": False,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

render_cover(
    TITLE,
    f"{n_agents} specialized Claude Code subagents",
    f"MRR INCLUDED  ·  {n_agents} AGENTS",
    "#3fb950",
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
        {"dir": str(out_dir), "zip": str(jarvis_zip), "agents": n_agents, "has_pdf": has_pdf},
        indent=2,
    )
)

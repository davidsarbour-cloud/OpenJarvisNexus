"""build_pack.py — package a hand-authored markdown pack into a sellable atom zip,
matching the Auto-Factory aipack layout (START_HERE / LICENSE / listing.json / cover / zip).

Usage:
    python build_pack.py <src_md> --key <key> --title "..." --price 9.99 \
        --tags "a,b,c" --blurb "..." --accent "#d97757"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from pack_common import hex_rgb as _hex
from pack_common import load_font as fnt

BACKEND_DIR = Path(__file__).resolve().parent
_JARVIS_STL = Path(os.getenv("JARVIS_STL_DIR", r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STL"))
JARVIS_AIPACK_DIR = Path(os.getenv("JARVIS_AIPACK_DIR", str(_JARVIS_STL.parent / "AIPacks")))


def render_cover(title, subtitle, badge, accent, out_dir):
    from PIL import Image, ImageDraw

    acc, bg, white, mute = _hex(accent), (13, 17, 23), (235, 240, 245), (139, 148, 158)

    def draw(size, fname, big, mid, small):
        W, H = size
        im = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(im)
        # top accent bar + faux terminal prompt
        d.rectangle((0, 0, W, int(H * 0.012)), fill=acc)
        term = "  ●  ●  ●   ~/project — claude"
        d.text((int(W * 0.06), int(H * 0.05)), term, font=fnt("consola.ttf", small), fill=mute)
        d.text((int(W * 0.06), int(H * 0.09)), "$ claude", font=fnt("consolab.ttf", mid), fill=acc)
        # title (wrapped)
        words, lines, cur = title.split(), [], ""
        fb = fnt("arialbd.ttf", big)
        for w in words:
            t = (cur + " " + w).strip()
            if d.textbbox((0, 0), t, font=fb)[2] <= W - int(W * 0.12):
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        y = int(H * 0.34)
        for ln in lines:
            d.text((int(W * 0.06), y), ln, font=fb, fill=white)
            y += big + 14
        # subtitle
        d.text((int(W * 0.06), y + 10), subtitle, font=fnt("arial.ttf", small), fill=mute)
        # badge pill
        by = y + int(H * 0.10)
        bw = d.textbbox((0, 0), badge, font=fnt("arialbd.ttf", mid))[2]
        d.rounded_rectangle(
            (int(W * 0.06), by, int(W * 0.06) + bw + 60, by + mid + 34), radius=14, fill=acc
        )
        d.text((int(W * 0.06) + 30, by + 16), badge, font=fnt("arialbd.ttf", mid), fill=bg)
        im.save(out_dir / fname, "PNG")

    draw((2000, 2000), "cover.png", 150, 60, 40)
    draw((1280, 720), "cover_wide.png", 92, 40, 26)


def md_to_pdf(md_text, out_path, accent="#d97757", font_size=11, base_dir=None):
    try:
        import os as _os

        import markdown as _md
        from xhtml2pdf import pisa
    except Exception:
        return False

    def _link_cb(uri, rel):
        if _os.path.isfile(uri):
            return uri
        if base_dir:
            p = _os.path.join(base_dir, uri)
            if _os.path.isfile(p):
                return p
        return uri

    html = _md.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    css = f"""
    @page {{ size: A4; margin: 2.4cm 2.2cm 2.0cm 2.2cm;
             @frame footer {{ -pdf-frame-content: footerContent; bottom: 1.0cm; height: 1cm; }} }}
    body {{ font-family: Helvetica, Arial, sans-serif; font-size: {font_size}pt; line-height: 1.55;
            color: #1b1f24; }}
    img {{ max-width: 100%; }}
    .diagram {{ -pdf-keep-with-next: false; }}
    h1 {{ color: {accent}; font-size: 19pt; margin: 18pt 0 8pt; padding-bottom: 4pt;
          border-bottom: 2px solid {accent}; page-break-after: avoid; }}
    h2 {{ color: #11161c; font-size: 14pt; margin: 16pt 0 6pt; page-break-after: avoid; }}
    h3 {{ color: #11161c; font-size: 11.5pt; margin: 12pt 0 4pt; page-break-after: avoid; }}
    p {{ margin: 0 0 8pt; }}
    ul, ol {{ margin: 0 0 8pt 14pt; }}
    li {{ margin: 0 0 4pt; }}
    strong {{ color: #11161c; }}
    code {{ font-family: Courier, monospace; background: #f0f1f3; font-size: 9.5pt;
            padding: 1pt 3pt; }}
    pre {{ background: #f5f6f8; border: 1px solid #e2e5e9; border-left: 3px solid {accent};
           padding: 8pt 10pt; font-family: Courier, monospace; font-size: 9pt;
           line-height: 1.4; white-space: pre-wrap; word-wrap: break-word; margin: 6pt 0 10pt; }}
    pre code {{ background: transparent; padding: 0; }}
    blockquote {{ background: #fbf6ee; border-left: 3px solid {accent}; margin: 8pt 0;
                  padding: 6pt 12pt; color: #3a3f46; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8pt 0 12pt; font-size: 9.5pt; }}
    th {{ background: {accent}; color: #ffffff; text-align: left; padding: 5pt 7pt; }}
    td {{ border: 1px solid #dcdfe3; padding: 5pt 7pt; vertical-align: top; }}
    tr {{ page-break-inside: avoid; }}
    hr {{ border: none; border-top: 1px solid #e2e5e9; margin: 14pt 0; }}
    """
    styled = (
        f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>"
        f"<div id='footerContent' style='text-align:center;color:#9aa0a6;font-size:8pt;'>"
        f"<pdf:pagenumber></div>"
        f"{html}</body></html>"
    )
    try:
        with open(out_path, "wb") as f:
            return pisa.CreatePDF(styled, dest=f, encoding="utf-8", link_callback=_link_cb).err == 0
    except Exception:
        return False


def build(src_md, key, title, price, tags, blurb, accent, subtitle, badge):
    md_text = Path(src_md).read_text(encoding="utf-8")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{key}_{ts}"
    out_dir = BACKEND_DIR / "aipack_output" / base
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / f"{key}.md").write_text(md_text, encoding="utf-8")
    has_pdf = md_to_pdf(md_text, out_dir / f"{key}.pdf", accent=accent)

    (out_dir / "START_HERE.txt").write_text(
        f"{title}\n\nSTART HERE:\n"
        f"1. Open {key}.{'pdf' if has_pdf else 'md'} — the full guide.\n"
        "2. Work top to bottom: LEVEL 1 -> LEVEL 4. Try each move in a real project.\n"
        "3. The BONUS section has copy-paste config files for your repo.\n"
        "4. Keep the CHEAT SHEET (last page) open while you work.\n\n"
        "Single-user license. Questions: d3dprintix@outlook.com\n",
        encoding="utf-8",
    )
    (out_dir / "LICENSE.txt").write_text(
        "Single-user license. Use this guide for your own work. "
        "Redistribution or resale of the files is not permitted.\n",
        encoding="utf-8",
    )
    listing = {
        "title": title,
        "price_usd": price,
        "pack": key,
        "has_pdf": has_pdf,
        "chars": len(md_text),
        "tags": tags,
        "blurb": blurb,
        "draft": False,
    }
    (out_dir / "listing.json").write_text(
        json.dumps(listing, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    render_cover(title, subtitle, badge, accent, out_dir)

    zip_path = out_dir.parent / f"{base}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out_dir.iterdir()):
            if f.is_file():
                z.write(f, f.name)

    JARVIS_AIPACK_DIR.mkdir(parents=True, exist_ok=True)
    jarvis_zip = JARVIS_AIPACK_DIR / f"{base}.zip"
    shutil.copy2(zip_path, jarvis_zip)
    return {"dir": str(out_dir), "zip": str(jarvis_zip), "has_pdf": has_pdf, "chars": len(md_text)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src_md")
    ap.add_argument("--key", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--price", type=float, default=9.99)
    ap.add_argument("--tags", default="")
    ap.add_argument("--blurb", default="")
    ap.add_argument("--accent", default="#d97757")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--badge", default="")
    a = ap.parse_args()
    res = build(
        a.src_md,
        a.key,
        a.title,
        a.price,
        [t.strip() for t in a.tags.split(",") if t.strip()],
        a.blurb,
        a.accent,
        a.subtitle,
        a.badge,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))

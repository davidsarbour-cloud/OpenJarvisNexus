"""recompose.py — the BUNDLING layer of the Auto-Factory.

The Auto-Factory produces ATOMS daily (single packs: one .zip per product line,
dropped in the Jarvis output folders). This script does the *next* altitude of the
matriochka: it gathers those existing atom .zips and stacks them into big sellable
BUNDLES (themed bundle -> mega -> vault), each with its own README, LICENSE,
manifest, cover and listing.json — ready for Etsy / Gumroad.

It writes NOTHING new content-wise: a bundle is just a folder of already-produced
atoms + generated wrapper files. Build once (the atom), sell at every altitude.

Driven by bundle_defs.json. Disk-driven (not catalog-driven) so it is robust to
the icon line naming packs by label-slug rather than catalog key.

Usage:
    python recompose.py            # build every bundle in bundle_defs.json
    python recompose.py --dry      # show what WOULD be built, write nothing
    python recompose.py --only icon_vault_all
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DEFS_FILE = BACKEND_DIR / "bundle_defs.json"
BUNDLES_OUT = BACKEND_DIR / "bundles_output"

# Same Jarvis base the Auto-Factory writes atoms to (see auto_factory.py).
import os

_JARVIS_STL = Path(os.getenv("JARVIS_STL_DIR", r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STL"))
JARVIS_BASE = _JARVIS_STL.parent
JARVIS_BUNDLES_DIR = JARVIS_BASE / "Bundles"

# line key -> Jarvis folder holding that line's atom .zips
LINE_DIRS = {
    "stl": JARVIS_BASE / "STL",
    "icons": JARVIS_BASE / "IconPacks",
    "pod": JARVIS_BASE / "POD",
    "game2d": JARVIS_BASE / "GameAssets2D",
    "uikit": JARVIS_BASE / "UIKits",
    "aipack": JARVIS_BASE / "AIPacks",
    "shopify": JARVIS_BASE / "Shopify",
    "premium": JARVIS_BASE / "Premium",
}

_TS_RE = re.compile(r"^(?P<key>.+)_(?P<ts>\d{8}_\d{6})$")


# ── atom discovery ────────────────────────────────────────────────────────────


def _parse_atom(zip_path: Path) -> dict:
    """{key, ts, path} from an atom filename '{key}_{YYYYMMDD_HHMMSS}.zip'."""
    m = _TS_RE.match(zip_path.stem)
    if m:
        return {"key": m.group("key"), "ts": m.group("ts"), "path": zip_path}
    return {"key": zip_path.stem, "ts": "", "path": zip_path}


def _latest_atoms(line: str, key_patterns: list[str]) -> list[dict]:
    """Newest atom per key in `line` whose key matches any glob in key_patterns."""
    folder = LINE_DIRS.get(line)
    if not folder or not folder.exists():
        return []
    best: dict[str, dict] = {}
    for zp in folder.glob("*.zip"):
        atom = _parse_atom(zp)
        if not any(fnmatch.fnmatch(atom["key"], pat) for pat in key_patterns):
            continue
        cur = best.get(atom["key"])
        if cur is None or atom["ts"] > cur["ts"]:
            best[atom["key"]] = atom
    return sorted(best.values(), key=lambda a: a["key"])


# ── cover art ─────────────────────────────────────────────────────────────────


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore


def _render_cover(title: str, tier: str, n_packs: int, accent: str, out_dir: Path) -> None:
    """Write cover.png (2000x2000 Etsy) + cover_wide.png (1280x720 Gumroad)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as e:
        print(f"  [cover] PIL unavailable ({e}) — skipping cover")
        return
    fonts = r"C:\Windows\Fonts"

    def font(name, sz):
        try:
            return ImageFont.truetype(str(Path(fonts) / name), sz)
        except Exception:
            return ImageFont.load_default()

    acc = _hex(accent)
    bg = (14, 17, 23)

    def draw(size, fname, big, small, badge):
        W, Hh = size
        im = Image.new("RGB", (W, Hh), bg)
        dd = ImageDraw.Draw(im)
        dd.rectangle((0, 0, W, int(Hh * 0.10)), fill=acc)
        dd.rectangle((0, Hh - int(Hh * 0.04), W, Hh), fill=acc)
        f_b = font("arialbd.ttf", big)
        f_s = font("arialbd.ttf", small)
        # wrap title
        words, lines, cur = title.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if dd.textbbox((0, 0), t, font=f_b)[2] <= W - int(W * 0.12):
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        total = len(lines) * (big + 18)
        y = (Hh - total) // 2 - 20
        for ln in lines:
            w = dd.textbbox((0, 0), ln, font=f_b)[2]
            dd.text(((W - w) / 2, y), ln, font=f_b, fill=(230, 237, 243))
            y += big + 18
        badge_txt = f"{tier.upper()}  ·  {n_packs} PACKS"
        bw = dd.textbbox((0, 0), badge_txt, font=f_s)[2]
        dd.text(((W - bw) / 2, y + 20), badge_txt, font=f_s, fill=acc)
        im.save(out_dir / fname, "PNG")

    draw((2000, 2000), "cover.png", 120, 70, True)
    draw((1280, 720), "cover_wide.png", 84, 46, False)


# ── bundle assembly ───────────────────────────────────────────────────────────


def _readme(bd: dict, atoms: list[dict]) -> str:
    tree = "\n".join(f"  packs/{a['key']}/" for a in atoms)
    return (
        f"# {bd['title']}\n\n"
        f"**{bd['tier'].upper()} bundle** · {len(atoms)} packs · ${bd['price_usd']:.2f}\n\n"
        f"{bd.get('blurb', '')}\n\n"
        "## What's inside\n\n"
        "Each folder under `packs/` is a complete, standalone pack "
        "(its own README, license and files):\n\n"
        f"```\n{tree}\n```\n\n"
        "## How to use\n\n"
        "1. Unzip this bundle.\n"
        "2. Open any folder in `packs/` — each has its own START_HERE / README.\n"
        "3. Use the packs you need; they are independent.\n\n"
        "## License\n\n"
        "Single-user license. Use these packs for your own work. "
        "Redistribution or resale of the files is not permitted.\n\n"
        "Questions: d3dprintix@outlook.com\n"
    )


def recompose_one(bd: dict, dry: bool = False) -> dict:
    inc = bd.get("includes", {})
    lines = inc.get("lines", [])
    keys = inc.get("keys", ["*"])
    atoms: list[dict] = []
    for line in lines:
        for a in _latest_atoms(line, keys):
            atoms.append({**a, "line": line})

    if not atoms:
        return {
            "id": bd["id"],
            "status": "empty",
            "reason": f"aucun atome pour lines={lines} keys={keys}",
        }

    summary = {
        "id": bd["id"],
        "title": bd["title"],
        "tier": bd["tier"],
        "price_usd": bd["price_usd"],
        "atom_count": len(atoms),
        "atoms": [f"{a['line']}:{a['key']}" for a in atoms],
    }
    if dry:
        summary["status"] = "would-build"
        return summary

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{bd['id']}_{ts}"
    work = BUNDLES_OUT / base
    packs = work / "packs"
    packs.mkdir(parents=True, exist_ok=True)

    # extract each atom .zip into packs/{key}/  -> a real "folder of packs"
    for a in atoms:
        dest = packs / a["key"]
        dest.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(a["path"]) as z:
                z.extractall(dest)
        except zipfile.BadZipFile:
            shutil.copy2(a["path"], dest / a["path"].name)  # fallback: drop zip in

    (work / "README.md").write_text(_readme(bd, atoms), encoding="utf-8")
    (work / "LICENSE.txt").write_text(
        "Single-user license. Use these packs for your own work. "
        "Redistribution or resale of the files is not permitted.\n",
        encoding="utf-8",
    )
    manifest = {
        "id": bd["id"],
        "title": bd["title"],
        "tier": bd["tier"],
        "price_usd": bd["price_usd"],
        "created_at": ts,
        "atom_count": len(atoms),
        "includes": [
            {"key": a["key"], "line": a["line"], "source_zip": a["path"].name, "ts": a["ts"]}
            for a in atoms
        ],
    }
    (work / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (work / "listing.json").write_text(
        json.dumps(
            {
                "title": bd["title"],
                "price_usd": bd["price_usd"],
                "tier": bd["tier"],
                "pack_count": len(atoms),
                "draft": True,
                "tags": bd.get("tags", []),
                "blurb": bd.get("blurb", ""),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    _render_cover(bd["title"], bd["tier"], len(atoms), bd.get("accent", "#58a6ff"), work)

    # zip the bundle
    zip_path = BUNDLES_OUT / f"{base}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in work.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(work))

    # mirror to Jarvis/Bundles
    jarvis_zip = None
    try:
        JARVIS_BUNDLES_DIR.mkdir(parents=True, exist_ok=True)
        jarvis_zip = JARVIS_BUNDLES_DIR / f"{base}.zip"
        shutil.copy2(zip_path, jarvis_zip)
    except Exception as e:
        print(f"  [jarvis] copy failed: {e}")

    summary["status"] = "built"
    summary["zip"] = str(jarvis_zip or zip_path)
    summary["dir"] = str(work)
    return summary


def recompose_all(dry: bool = False, only: str | None = None) -> list[dict]:
    defs = json.loads(DEFS_FILE.read_text(encoding="utf-8")).get("bundles", [])
    if only:
        defs = [b for b in defs if b["id"] == only]
    out = []
    for bd in defs:
        res = recompose_one(bd, dry=dry)
        out.append(res)
        tag = res["status"].upper()
        if res["status"] in ("built", "would-build"):
            print(
                f"[{tag}] {res['id']} — {res['atom_count']} packs "
                f"(${res['price_usd']}) :: {', '.join(res['atoms'])}"
            )
            if res.get("zip"):
                print(f"        -> {res['zip']}")
        else:
            print(f"[{tag}] {res['id']} — {res.get('reason', '')}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Stack Auto-Factory atoms into sellable bundles.")
    ap.add_argument("--dry", action="store_true", help="show what would build, write nothing")
    ap.add_argument("--only", help="only build this bundle id")
    args = ap.parse_args()
    results = recompose_all(dry=args.dry, only=args.only)
    built = sum(1 for r in results if r["status"] == "built")
    print(
        f"\n{built}/{len(results)} bundles built."
        if not args.dry
        else f"\n(dry) {len(results)} bundles evaluated."
    )

"""Auto Factory — two autonomous product lines (NEXUS9).

Once a day it advances TWO independent rotations and produces their next item:
  • STL line   — next 3D niche (NICHES)      -> stl_agent (Meshy -> repair -> save)
  • Icon line  — next aesthetic (ICON_THEMES) -> IconForge FLUX pack
then fires one Telegram alert with the ready-file paths. The two lines are
SEPARATE on purpose: a 3D object is not an icon-pack theme. Each rotates over
its own list, by commercial tier, no repeat until its cycle completes.

Why tier rotation, not a buzz-score gate: the trend scorer measures ONLINE BUZZ
velocity, not sales. Evergreen niches never "spike" → a score gate would keep
the factory silent. So rotation drives selection; buzz is an OPTIONAL spike
override on the STL line only (`spike_check`, default off).

Config: config.json -> "auto_factory". Catalogs: factory_niches.py. Scheduler:
daily_tasks.create_scheduler(). Manual: POST /v1/factory/run (?dry / ?force).
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import shutil
import zipfile
import zlib
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from factory_niches import (
    AI_PACKS,
    GAME_ASSETS_2D,
    ICON_THEMES,
    NICHES,
    POD_DESIGNS,
    PREMIUM_VISUALS,
    SHOPIFY_TEMPLATES,
    TIER_RANK,
    UI_KITS,
)
from fastapi import APIRouter, HTTPException

load_dotenv()  # so TELEGRAM_* creds resolve in standalone runs (backend also loads them)

BACKEND_DIR = Path(__file__).resolve().parent
STATE_FILE  = BACKEND_DIR / "auto_factory_state.json"

# Mirror the STL pipeline's "copy to Jarvis folder" behavior for icon packs:
# each finished pack ZIP is also dropped into a sibling IconPacks folder under
# the same Jarvis directory the STL agent uses (override with JARVIS_ICONS_DIR).
JARVIS_STL_DIR   = Path(os.getenv("JARVIS_STL_DIR", r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STL"))
JARVIS_ICONS_DIR = Path(os.getenv("JARVIS_ICONS_DIR", str(JARVIS_STL_DIR.parent / "IconPacks")))
JARVIS_POD_DIR   = Path(os.getenv("JARVIS_POD_DIR",   str(JARVIS_STL_DIR.parent / "POD")))
JARVIS_GAME2D_DIR = Path(os.getenv("JARVIS_GAME2D_DIR", str(JARVIS_STL_DIR.parent / "GameAssets2D")))
JARVIS_UIKIT_DIR  = Path(os.getenv("JARVIS_UIKIT_DIR",  str(JARVIS_STL_DIR.parent / "UIKits")))
JARVIS_AIPACK_DIR = Path(os.getenv("JARVIS_AIPACK_DIR", str(JARVIS_STL_DIR.parent / "AIPacks")))
JARVIS_SHOPIFY_DIR = Path(os.getenv("JARVIS_SHOPIFY_DIR", str(JARVIS_STL_DIR.parent / "Shopify")))
JARVIS_PREMIUM_DIR = Path(os.getenv("JARVIS_PREMIUM_DIR", str(JARVIS_STL_DIR.parent / "Premium")))


def _seed(s: str) -> int:
    """Stable non-negative seed from a string (process-independent)."""
    return zlib.crc32(s.encode("utf-8")) & 0x7FFFFFFF


DEFAULTS: dict = {
    "enabled":            True,
    "schedule_hour":      8,
    "schedule_minute":    0,
    "selection_mode":     "tier_rotation",  # tier_rotation | buzz_rerank | weighted_random
    "stagger_minutes":    20,               # gap between each line's daily job
    "spike_check":        False,            # STL line: a buzz spike jumps the queue
    "spike_threshold":    60,               # score (0-100) that counts as "spiking"
    "products":           ["stl", "icons", "pod", "game2d", "uikit", "aipack", "shopify", "premium"],
    "icon_count":         12,               # subset of the 30-app catalog per pack
    "stl_target_size_mm": 150.0,
    "pod_art_size":       1024,             # FLUX render size for POD designs
    "game2d_item_size":   768,              # FLUX render size per game/UI asset
    "game2d_max_items":   20,               # items/pack — ARPG packs = 20 icônes/jour
    "pod_per_run":        10,               # POD designs produits par run quotidien
    "image_backend":      "comfyui",        # comfyui | gpt-image-1 | auto (ImageFactory)
    "valkyrie_score_threshold": 60,         # premium line: buzz score to ride a trend (hype)
    "premium_quality":    "high",           # gpt-image-1 quality for the premium (VALKYRIE) line
}

_TIER_WEIGHT = {"S": 3, "A": 2, "B": 1}


def factory_cfg() -> dict:
    """Merge config.json -> auto_factory over DEFAULTS."""
    cfg_file = BACKEND_DIR / "config.json"
    try:
        cfg = json.loads(cfg_file.read_text(encoding="utf-8")) if cfg_file.exists() else {}
    except Exception:
        cfg = {}
    out = dict(DEFAULTS)
    out.update(cfg.get("auto_factory", {}) or {})
    return out


# ── Alert ─────────────────────────────────────────────────────────────────────

def send_telegram(text: str) -> bool:
    """Fire a proactive Telegram message to the authorized user. Best-effort.

    Plain text (no parse_mode) on purpose — Windows file paths contain
    backslashes/underscores that break Telegram Markdown parsing.
    """
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_AUTHORIZED_USER_ID", "")
    if not token or not chat_id:
        print("[auto_factory] Telegram creds missing — skipping alert")
        return False
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": int(chat_id), "text": text,
                  "disable_web_page_preview": True},
            timeout=15,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[auto_factory] Telegram send failed: {e}")
        return False


# ── Rotation state (one sub-state per line) ───────────────────────────────────

def _load_state() -> dict:
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    state.setdefault("stl",    {"done": [], "cycle": 1})
    state.setdefault("icons",  {"done": [], "cycle": 1})
    state.setdefault("pod",    {"done": [], "cycle": 1})
    state.setdefault("game2d", {"done": [], "cycle": 1})
    state.setdefault("uikit",   {"done": [], "cycle": 1})
    state.setdefault("aipack",  {"done": [], "cycle": 1})
    state.setdefault("shopify", {"done": [], "cycle": 1})
    state.setdefault("premium", {"done": [], "cycle": 1})
    return state


def _save_state(state: dict) -> None:
    """Atomically persist state (temp file + os.replace) so an overlapping run
    can never read a half-written file."""
    state["last"] = datetime.now().isoformat()
    try:
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        print(f"[auto_factory] state save failed: {e}")


def _save_lines(updated: dict[str, dict]) -> None:
    """Persist ONLY the given line sub-states. Re-reads the latest state from
    disk first and overwrites just `updated`'s keys, so a concurrently-running
    sibling job (the other line) never loses its rotation advance — overlap is
    harmless regardless of timing."""
    fresh = _load_state()
    for line, sub in updated.items():
        fresh[line] = sub
    _save_state(fresh)


# ── Selection ─────────────────────────────────────────────────────────────────

async def _buzz_scores(items: list[dict]) -> dict[str, float]:
    """Score each STL niche's English subject for current online buzz (0-100)."""
    from trend_hunter import score_single_keyword
    terms = [n["stl_prompt"].split(",")[0] for n in items]
    results = await asyncio.gather(
        *[score_single_keyword(t) for t in terms], return_exceptions=True
    )
    out: dict[str, float] = {}
    for n, res in zip(items, results):
        out[n["key"]] = 0.0 if isinstance(res, Exception) else float(res.get("score", 0) or 0)
    return out


def _trend_keywords() -> list[str]:
    """Hype candidate subjects — David's curated trend_hunter keyword list."""
    cfg_file = BACKEND_DIR / "config.json"
    try:
        cfg = json.loads(cfg_file.read_text(encoding="utf-8")) if cfg_file.exists() else {}
        kws = (cfg.get("trend_hunter", {}) or {}).get("dropshipping_keywords", []) or []
        return [str(k) for k in kws]
    except Exception:
        return []


async def _hype_subject(default_subject: str, threshold: float) -> tuple[str, float, bool]:
    """Score curated trend keywords; if the hottest clears `threshold`, ride it.

    Returns (subject, score, rode_hype). Falls back to `default_subject` on any
    failure or a quiet day — the premium line never goes silent (rotation still
    produces the evergreen template). Candidates capped to bound cost/latency.
    """
    candidates = _trend_keywords()[:8]
    if not candidates:
        return default_subject, 0.0, False
    try:
        from trend_hunter import score_single_keyword
        results = await asyncio.gather(
            *[score_single_keyword(k) for k in candidates], return_exceptions=True,
        )
    except Exception as e:
        print(f"[auto_factory] hype scoring failed: {e}")
        return default_subject, 0.0, False
    best, best_score = default_subject, -1.0
    for kw, res in zip(candidates, results):
        if isinstance(res, Exception):
            continue
        s = float(res.get("score", 0) or 0)
        if s > best_score:
            best, best_score = kw, s
    if best_score >= threshold:
        return best, best_score, True
    return default_subject, max(best_score, 0.0), False


def _rotate(catalog: list[dict], sub: dict) -> tuple[dict, str, list[dict]]:
    """Tier-rotation pick over `catalog` using per-line `sub` state (may reset)."""
    done = set(sub.get("done", []))
    remaining = [n for n in catalog if n["key"] not in done]
    if not remaining:                       # cycle complete — start a fresh pass
        sub["done"] = []
        sub["cycle"] = int(sub.get("cycle", 1)) + 1
        remaining = list(catalog)
    remaining.sort(key=lambda n: (TIER_RANK.get(n["tier"], 9), catalog.index(n)))
    pos = len(catalog) - len(remaining) + 1
    return remaining[0], f"rotation {pos}/{len(catalog)} (cycle {sub.get('cycle', 1)})", remaining


async def _select(catalog: list[dict], sub: dict, cfg: dict,
                  allow_buzz: bool) -> tuple[dict, str]:
    """Pick the next item from `catalog`. allow_buzz enables the spike override."""
    mode = cfg.get("selection_mode", "tier_rotation")
    base, reason, remaining = _rotate(catalog, sub)

    if allow_buzz and (mode == "buzz_rerank" or cfg.get("spike_check")):
        try:
            scores = await _buzz_scores(remaining)
            best = max(remaining, key=lambda n: scores.get(n["key"], 0))
            bs = scores.get(best["key"], 0)
            if mode == "buzz_rerank" or bs >= float(cfg.get("spike_threshold", 60)):
                return best, f"buzz spike {bs:.0f}/100"
        except Exception as e:
            print(f"[auto_factory] buzz scoring failed, using rotation: {e}")

    if mode == "weighted_random":
        weights = [_TIER_WEIGHT.get(n["tier"], 1) for n in remaining]
        return random.choices(remaining, weights=weights, k=1)[0], "weighted random"

    return base, reason


# ── Producers ─────────────────────────────────────────────────────────────────

async def _produce_stl(niche: dict, size_mm: float) -> dict:
    """Run the STL pipeline in-process (Meshy -> repair -> save) and await it."""
    from stl_agent import MissionRequest, _missions, _new_mission, _run_pipeline
    req = MissionRequest(prompt=niche["stl_prompt"], engine="auto",
                         auto_bambu=False, target_size_mm=size_mm)
    m = _new_mission(req)
    _missions[m["id"]] = m
    await _run_pipeline(m["id"])
    val = m.get("validation", {})
    return {
        "mission_id":   m["id"],
        "status":       m["status"],
        "file":         m["files"].get("jarvis_stl") or m["files"].get("model") or m["files"].get("raw"),
        "preview":      m["files"].get("preview"),
        "score":        val.get("printability_score"),
        "verdict":      val.get("verdict"),
        "supports":     val.get("supports_required"),
        "support_type": val.get("support_type"),
        "overhang_pct": val.get("overhang_pct"),
    }


async def _produce_icons(theme_item: dict, count: int) -> dict:
    """Render an icon pack in `theme_item`'s aesthetic via FLUX (ComfyUI).
    Blocking pipeline -> run in a thread so the event loop stays free."""
    from iconforge.brief import PackBrief
    from iconforge.catalog import MINIMAL_BLACK_30
    from iconforge.pipeline import run_pack
    brief = PackBrief(
        name=f"{theme_item['label']} Icons",
        theme=f"{theme_item['theme']}, app icon, cohesive set, modern, clean, high detail",
        category="Artistic",
        generator="comfyui",
        targets=["ios"],
        icons=MINIMAL_BLACK_30[: max(1, count)],
    )
    try:
        r = await asyncio.to_thread(run_pack, brief)
        out = {"status": "complete", "pack_id": r.pack_id,
               "zip": str(r.zip_path), "icons": r.icon_count}
        # Copy the pack ZIP into the Jarvis IconPacks folder (mirrors the STL copy).
        try:
            JARVIS_ICONS_DIR.mkdir(parents=True, exist_ok=True)
            dest = JARVIS_ICONS_DIR / Path(r.zip_path).name
            shutil.copy2(str(r.zip_path), str(dest))
            out["jarvis_zip"] = str(dest)
        except Exception as e:
            print(f"[auto_factory] Jarvis icon copy failed: {e}")
        return out
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _overlay_slogan(art_png: bytes, slogan: str) -> bytes:
    """Typeset a clean bold slogan in a band UNDER the rendered mascot art.
    FLUX can't draw text, so the slogan is rendered here (Impact/Arial Black) in
    white with a dark outline so it reads on dark shirts. Transparent-bg PNG out.
    Best-effort: returns the original art unchanged if PIL/fonts are missing."""
    if not slogan:
        return art_png
    import os
    from io import BytesIO
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return art_png

    art = Image.open(BytesIO(art_png)).convert("RGBA")
    W = art.width
    band = int(W * 0.30)              # height of the text band under the art
    pad  = int(W * 0.06)
    canvas = Image.new("RGBA", (W, art.height + band), (0, 0, 0, 0))
    canvas.paste(art, (0, 0), art)
    draw = ImageDraw.Draw(canvas)

    fpath = next((p for p in (
        r"C:\Windows\Fonts\impact.ttf", r"C:\Windows\Fonts\ariblk.ttf",
        r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf",
    ) if os.path.exists(p)), None)

    text = slogan.upper()
    maxw = W - 2 * pad

    def _wrap(font):
        lines, cur = [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if not cur or draw.textlength(t, font=font) <= maxw:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    size = int(band * 0.6)
    font = ImageFont.load_default()
    lines, lh = [text], size
    while size > 10:
        font = ImageFont.truetype(fpath, size) if fpath else ImageFont.load_default()
        lines = _wrap(font)
        lh = int(size * 1.12)
        if len(lines) <= 3 and lh * len(lines) <= band - pad:
            break
        size -= 4

    y = art.height + (band - lh * len(lines)) // 2
    stroke = max(2, size // 16)
    for ln in lines:
        lw = draw.textlength(ln, font=font)
        draw.text(((W - lw) / 2, y), ln, font=font, fill=(255, 255, 255, 255),
                  stroke_width=stroke, stroke_fill=(15, 15, 18, 255))
        y += lh

    out = BytesIO()
    canvas.save(out, "PNG")
    return out.getvalue()


async def _produce_pod(design: dict) -> dict:
    """POD line: art (ImageFactory) -> slogan overlay -> listing draft -> save
    (local + Jarvis/POD) -> Printify sync (gated on PRINTIFY_API_KEY)."""
    from services import image_factory
    cfg = factory_cfg()
    backend = image_factory.choose(cfg.get("image_backend", "comfyui"), niche_type="pod")
    if not image_factory.is_available(backend):
        return {"status": "error", "error": f"backend image indisponible ({backend}) — POD"}
    await image_factory.prepare(backend)             # FLUX: free VRAM

    size = int(cfg.get("pod_art_size", 1024))
    try:
        png = await image_factory.render(
            design["art_prompt"], size=size, seed=_seed(design["key"]),
            backend=backend, transparent=True,
        )
    except Exception as e:
        return {"status": "error", "error": f"{backend}: {e}"}

    # Typeset the clean slogan onto the mascot art (FLUX can't render text).
    slogan = design.get("slogan", "")
    if slogan:
        png = _overlay_slogan(png, slogan)

    # Listing draft (Etsy allows 13 tags). The slogan drives the SEO title.
    tags  = design["tags"][:13]
    _head = slogan or design["label"]
    title = f'{_head} - {design["label"]} AI Coding Humor Unisex Tee Gift'[:140]
    desc  = (f'"{slogan}" — funny AI / coding-humor {design["product"]}.\n\n'
             f"Original {design['label']} design, print-on-demand, high-quality "
             f"print, multiple sizes and colors.\n"
             f"Perfect gift for programmers, developers, prompt engineers and AI "
             f"nerds.\nKeywords: {', '.join(tags)}")
    listing = {"title": title, "tags": tags, "description": desc,
               "price_usd": 24.99, "product": design["product"], "design": design["key"]}

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{design['key']}_{ts}"
    platform = design.get("platform", "general")   # bucket l'output par plateforme AI
    out_dir = BACKEND_DIR / "pod_output" / platform / base
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{base}.png").write_bytes(png)
    (out_dir / "listing.json").write_text(
        json.dumps(listing, indent=2, ensure_ascii=False), encoding="utf-8")

    jarvis_art = None
    try:
        pod_jarvis_dir = JARVIS_POD_DIR / platform   # 1 dossier par plateforme
        pod_jarvis_dir.mkdir(parents=True, exist_ok=True)
        jarvis_art = str(pod_jarvis_dir / f"{base}.png")
        shutil.copy2(str(out_dir / f"{base}.png"), jarvis_art)
        shutil.copy2(str(out_dir / "listing.json"), str(pod_jarvis_dir / f"{base}.listing.json"))
    except Exception as e:
        print(f"[auto_factory] Jarvis POD copy failed: {e}")

    import printify_client
    pf = printify_client.sync(f"{base}.png", png, title, desc, tags)
    return {"status": "complete", "design": design["key"],
            "art": jarvis_art or str(out_dir / f"{base}.png"),
            "listing": str(out_dir / "listing.json"), "printify": pf}


async def _produce_pack(pack: dict, *, out_subdir: str, jarvis_dir: Path,
                        price: float, title_suffix: str,
                        niche_type: str = "game_assets") -> dict:
    """Generic asset-pack producer (shared by the game-asset and UI-kit lines):
    render each item in `pack["items"]` with the shared `pack["style"]` via
    ImageFactory, strip the bg (transparent), bundle into a ZIP + listing.json,
    copy to Jarvis."""
    from services import image_factory
    cfg  = factory_cfg()
    backend = image_factory.choose(cfg.get("image_backend", "comfyui"), niche_type=niche_type)
    if not image_factory.is_available(backend):
        return {"status": "error", "error": f"backend image indisponible ({backend})"}
    await image_factory.prepare(backend)             # FLUX: free VRAM

    size = int(cfg.get("game2d_item_size", 768))
    cap  = int(cfg.get("game2d_max_items", 20))   # ARPG packs = 20 icônes/jour
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{pack['key']}_{ts}"
    out_dir = BACKEND_DIR / out_subdir / base
    out_dir.mkdir(parents=True, exist_ok=True)

    made: list[str] = []
    for item in pack["items"][: max(1, cap)]:
        try:
            png = await image_factory.render(
                f"{item}, {pack['style']}", size=size,
                seed=_seed(pack["key"] + item), backend=backend, transparent=True,
            )
        except Exception as e:
            print(f"[auto_factory] {out_subdir} item '{item}' failed: {e}")
            continue
        slug = re.sub(r"[^a-z0-9]+", "_", item.lower()).strip("_")
        (out_dir / f"{slug}.png").write_bytes(png)
        made.append(slug)

    if not made:
        return {"status": "error", "error": "aucun asset généré"}

    zip_path = out_dir.parent / f"{base}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out_dir.glob("*.png")):
            z.write(p, p.name)
    listing = {"title": f"{pack['label']} - {title_suffix}",
               "items": made, "count": len(made), "price_usd": price}
    (out_dir / "listing.json").write_text(
        json.dumps(listing, indent=2, ensure_ascii=False), encoding="utf-8")

    jarvis_zip = None
    try:
        jarvis_dir.mkdir(parents=True, exist_ok=True)
        jarvis_zip = str(jarvis_dir / f"{base}.zip")
        shutil.copy2(str(zip_path), jarvis_zip)
    except Exception as e:
        print(f"[auto_factory] Jarvis {out_subdir} copy failed: {e}")

    return {"status": "complete", "pack": pack["key"], "assets": len(made),
            "zip": jarvis_zip or str(zip_path)}


async def _produce_game2d(pack: dict) -> dict:
    return await _produce_pack(pack, out_subdir="game2d_output",
                               jarvis_dir=JARVIS_GAME2D_DIR, price=14.99,
                               title_suffix="2D Game Asset Pack",
                               niche_type="game_assets")


async def _produce_uikit(kit: dict) -> dict:
    return await _produce_pack(kit, out_subdir="uikit_output",
                               jarvis_dir=JARVIS_UIKIT_DIR, price=19.99,
                               title_suffix="Game UI Kit",
                               niche_type="ui_kit")


def _sonnet_generate(system: str, brief: str) -> str | None:
    """Generate with Claude Sonnet (premium quality). Returns None on failure so
    the caller can fall back to Ollama. Records the call in the budget tracker."""
    try:
        from app_state import CLAUDE_MODEL_GROS, claude
        r = claude.messages.create(
            model=CLAUDE_MODEL_GROS, max_tokens=8192,
            system=system, messages=[{"role": "user", "content": brief}],
        )
        txt = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
        try:
            import budget_tracker
            budget_tracker.record_call("sonnet", r.usage.input_tokens, r.usage.output_tokens)
        except Exception:
            pass
        return txt or None
    except Exception as e:
        print(f"[auto_factory] Sonnet generate failed, falling back to Ollama: {e}")
        return None


async def _produce_llm_pack(item: dict, *, out_subdir: str, jarvis_dir: Path,
                            file_ext: str, system: str, price: float,
                            title_suffix: str, use_sonnet: bool = False) -> dict:
    """Generic LLM text/code producer (AI-pack + Shopify lines). use_sonnet=True
    → Claude Sonnet (premium), else Ollama. Falls back to Ollama if Sonnet fails."""
    content = None
    engine = "ollama"
    if use_sonnet:
        content = await asyncio.to_thread(_sonnet_generate, system, item["brief"])
        if content:
            engine = "sonnet"
    if not content:
        from ollama_client import ask_ollama, strip_think_tags
        raw = await asyncio.to_thread(ask_ollama, f"{system}\n\n{item['brief']}")
        content = strip_think_tags(raw) if raw else None
    if not content:
        return {"status": "error", "error": "LLM indisponible (Sonnet + Ollama)"}

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{item['key']}_{ts}"
    out_dir = BACKEND_DIR / out_subdir / base
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{item['key']}.{file_ext}").write_text(content, encoding="utf-8")
    listing = {"title": f"{item['label']} - {title_suffix}",
               "price_usd": price, "engine": engine,
               "draft": engine == "ollama", "pack": item["key"]}
    (out_dir / "listing.json").write_text(
        json.dumps(listing, indent=2, ensure_ascii=False), encoding="utf-8")

    jarvis_file = None
    try:
        jarvis_dir.mkdir(parents=True, exist_ok=True)
        jarvis_file = str(jarvis_dir / f"{base}.{file_ext}")
        shutil.copy2(str(out_dir / f"{item['key']}.{file_ext}"), jarvis_file)
    except Exception as e:
        print(f"[auto_factory] Jarvis {out_subdir} copy failed: {e}")

    return {"status": "complete", "pack": item["key"], "chars": len(content),
            "file": jarvis_file or str(out_dir / f"{item['key']}.{file_ext}")}


_AIPACK_KIT_SYSTEM = (
    "You are a senior prompt engineer building a PREMIUM, sellable prompt KIT in the "
    "style of a polished paid digital product (like a top Gumroad/Etsy 'AI prompt "
    "kit'). Output clean Markdown ONLY — no preamble, no commentary outside the kit. "
    "Structure: a # title, a punchy 2-3 sentence intro/hook, a '## How to use this "
    "kit' section, then 90-120 copy-paste prompts organized into clearly-titled "
    "workflow sections (## ...). Every prompt: numbered, specific, professional, uses "
    "[PLACEHOLDERS] for personalization, and a one-line '> Use when:' note. End with a "
    "short '## Pro tips' section. Make it genuinely high-value and ready to sell."
)


def _md_to_pdf_bytes(md_text: str) -> bytes | None:
    """Best-effort Markdown -> PDF (same stack as the AI Server Kit). Returns None if
    the optional libs aren't installed — the kit then ships as Markdown only."""
    try:
        from io import BytesIO

        import markdown as _md
        from xhtml2pdf import pisa
    except Exception:
        return None
    try:
        body = _md.markdown(md_text, extensions=["tables", "fenced_code"])
        html = ("<html><head><meta charset='utf-8'><style>"
                "@page { size: A4; margin: 2cm; } "
                "body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.45; } "
                "h1 { color:#111; } h2 { color:#222; border-bottom:1px solid #ccc; padding-bottom:3px; } "
                "code, pre { background:#f4f4f4; }"
                f"</style></head><body>{body}</body></html>")
        out = BytesIO()
        if pisa.CreatePDF(html, dest=out).err:
            return None
        return out.getvalue()
    except Exception:
        return None


async def _produce_aipack(item: dict) -> dict:
    """AI Pack line — produces a full 'AI Server Kit'-style prompt KIT (intro +
    how-to + ~100 organized prompts), bundled into a ZIP (Markdown + best-effort
    PDF + START_HERE + LICENSE). Premium = Claude Sonnet, Ollama fallback. 1/run."""
    brief = (f"Build the complete kit now. Topic: {item['label']}.\n\n"
             f"Scope: {item['brief']}\n\n"
             "Expand to a FULL kit (90-120 prompts), not a short pack.")
    content = await asyncio.to_thread(_sonnet_generate, _AIPACK_KIT_SYSTEM, brief)
    engine = "sonnet"
    if not content:
        from ollama_client import ask_ollama, strip_think_tags
        raw = await asyncio.to_thread(ask_ollama, f"{_AIPACK_KIT_SYSTEM}\n\n{brief}")
        content = strip_think_tags(raw) if raw else None
        engine = "ollama"
    if not content:
        return {"status": "error", "error": "LLM indisponible (Sonnet + Ollama)"}

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{item['key']}_{ts}"
    out_dir = BACKEND_DIR / "aipack_output" / base
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{item['key']}.md").write_text(content, encoding="utf-8")

    pdf_bytes = await asyncio.to_thread(_md_to_pdf_bytes, content)
    if pdf_bytes:
        (out_dir / f"{item['key']}.pdf").write_bytes(pdf_bytes)

    (out_dir / "START_HERE.txt").write_text(
        f"{item['label']} — AI Prompt Kit\n\n"
        "START HERE:\n"
        f"1. Open {item['key']}.pdf (or .md) — the full kit.\n"
        "2. Copy-paste any prompt, fill the [PLACEHOLDERS], run it in your AI.\n\n"
        "Single-user license. Questions: d3dprintix@outlook.com\n", encoding="utf-8")
    (out_dir / "LICENSE.txt").write_text(
        "Single-user license. Use this kit for your own work. Redistribution or "
        "resale of the files is not permitted.\n", encoding="utf-8")
    listing = {"title": f"{item['label']} - AI Prompt Kit", "price_usd": 14.99,
               "engine": engine, "pack": item["key"], "has_pdf": bool(pdf_bytes),
               "chars": len(content), "draft": engine == "ollama"}
    (out_dir / "listing.json").write_text(
        json.dumps(listing, indent=2, ensure_ascii=False), encoding="utf-8")

    zip_path = out_dir.parent / f"{base}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out_dir.iterdir()):
            if f.is_file():
                z.write(f, f.name)

    jarvis_zip = None
    try:
        JARVIS_AIPACK_DIR.mkdir(parents=True, exist_ok=True)
        jarvis_zip = str(JARVIS_AIPACK_DIR / f"{base}.zip")
        shutil.copy2(str(zip_path), jarvis_zip)
    except Exception as e:
        print(f"[auto_factory] Jarvis aipack copy failed: {e}")

    return {"status": "complete", "pack": item["key"], "chars": len(content),
            "engine": engine, "has_pdf": bool(pdf_bytes),
            "file": jarvis_zip or str(zip_path)}


async def _produce_shopify(item: dict) -> dict:
    return await _produce_llm_pack(
        item, out_subdir="shopify_output", jarvis_dir=JARVIS_SHOPIFY_DIR,
        file_ext="liquid", price=24.99, title_suffix="Shopify Section",
        system=("You are a senior Shopify theme developer. Output a single "
                "valid Shopify section: Liquid markup + a {% schema %} JSON "
                "block with settings. Output ONLY the .liquid code, no commentary."))


async def _produce_premium(visual: dict) -> dict:
    """VALKYRIE premium line — the deliberate 5% on gpt-image-1.

    Three things make this line "premium" rather than just another rotation:
      1) niche_type ∈ PREMIUM_NICHES -> ImageFactory FORCES gpt-image-1.
      2) hype: rides a trending subject when buzz clears valkyrie_score_threshold.
      3) self-improvement: appends learned best modifiers, then records the
         generation so future prompts get measurably better.
    """
    from services import image_factory, valkyrie_memory
    cfg = factory_cfg()
    niche_type = visual.get("niche_type", "thumbnail")
    backend = image_factory.choose(cfg.get("image_backend", "comfyui"), niche_type=niche_type)
    if not image_factory.is_available(backend):
        return {"status": "error", "error": f"backend image indisponible ({backend}) — premium"}
    await image_factory.prepare(backend)             # FLUX fallback: free VRAM

    # 1) Hype — ride a trending subject when buzz clears the threshold.
    subject = visual.get("subject", "")
    hype_score: float | None = None
    rode_hype = False
    if visual.get("hype"):
        subject, hype_score, rode_hype = await _hype_subject(
            visual.get("subject", ""), float(cfg.get("valkyrie_score_threshold", 60)))

    base_prompt = visual["prompt"].replace("{subject}", subject)
    # 2) Self-improvement — append the current best-performing modifiers.
    final_prompt, mods = valkyrie_memory.enhance(base_prompt, niche_type)

    size = visual.get("size", "1024x1024")
    transparent = bool(visual.get("transparent", False))
    quality = str(cfg.get("premium_quality", "high"))
    try:
        png = await image_factory.render(
            final_prompt, size=size, seed=_seed(visual["key"]),
            backend=backend, transparent=transparent, quality=quality,
        )
    except Exception as e:
        return {"status": "error", "error": f"{backend}: {e}"}

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{visual['key']}_{ts}"
    img_name = f"{base}.png"
    out_dir = BACKEND_DIR / "premium_output" / base
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / img_name).write_bytes(png)
    listing = {"title": visual["label"], "niche_type": niche_type, "subject": subject,
               "hype_score": hype_score, "rode_hype": rode_hype, "backend": backend,
               "prompt": final_prompt, "modifiers": mods}
    (out_dir / "listing.json").write_text(
        json.dumps(listing, indent=2, ensure_ascii=False), encoding="utf-8")

    jarvis_art = None
    try:
        JARVIS_PREMIUM_DIR.mkdir(parents=True, exist_ok=True)
        jarvis_art = str(JARVIS_PREMIUM_DIR / img_name)
        shutil.copy2(str(out_dir / img_name), jarvis_art)
        shutil.copy2(str(out_dir / "listing.json"), str(JARVIS_PREMIUM_DIR / f"{base}.listing.json"))
    except Exception as e:
        print(f"[auto_factory] Jarvis premium copy failed: {e}")

    # 3) Record for self-improvement (ledger + best-effort agent_memory mirror).
    valkyrie_memory.record_generation(
        image_name=img_name, base_prompt=base_prompt, final_prompt=final_prompt,
        modifiers=mods, niche_type=niche_type, backend=backend, hype_score=hype_score)
    await valkyrie_memory.mirror_to_memory(
        f"VALKYRIE {niche_type} · {visual['label']} · subject={subject}",
        {"agent": "valkyrie", "niche_type": niche_type, "key": visual["key"],
         "backend": backend, "hype_score": hype_score, "image": img_name})

    return {"status": "complete", "key": visual["key"], "niche_type": niche_type,
            "subject": subject, "hype_score": hype_score, "rode_hype": rode_hype,
            "backend": backend, "art": jarvis_art or str(out_dir / img_name)}


# ── Orchestrator ────────────────────────────────────────────────────────────

def _format_alert(chosen: dict, results: dict) -> str:
    lines = ["🏭 Auto-Factory — production du jour", ""]
    if "stl" in chosen:
        niche, reason = chosen["stl"]
        stl = results.get("stl", {})
        lines.append(f"🧊 STL — {niche['label']} [{niche['tier']}-tier] ({reason})")
        if stl.get("status") in ("complete", "partial") and stl.get("file"):
            badge = {"ready": "✅ PRÊT", "supports_required": "🔧 SUPPORTS REQUIS",
                     "risky": "⛔ RISQUÉ"}.get(stl.get("verdict"), stl.get("verdict") or "?")
            oh = f", overhang {stl['overhang_pct']}%" if stl.get("overhang_pct") is not None else ""
            lines.append(f"   {badge} — imprimabilité {stl.get('score')}/100{oh}")
            if stl.get("supports"):
                lines.append(f"   ⚠️ imprime AVEC supports ({stl.get('support_type') or 'tree'})")
            lines.append(f"   fichier: {stl['file']}")
            if stl.get("preview"):
                lines.append(f"   aperçu: {stl['preview']}")
        else:
            lines.append(f"   échec ({stl.get('status')}) — vérifie Meshy/Blender/crédit Claude")
    if "icons" in chosen:
        theme, reason = chosen["icons"]
        pk = results.get("icons", {})
        lines.append(f"📦 Icônes — {theme['label']} [{theme['tier']}-tier] ({reason})")
        if pk.get("status") == "complete":
            lines.append(f"   {pk['icons']} icônes: {pk.get('jarvis_zip') or pk['zip']}")
        else:
            lines.append(f"   échec — {pk.get('error', '?')}")
    if "pod" in chosen:
        pod = results.get("pod", {})
        batch = pod.get("batch")
        if batch is not None:
            ok = pod.get("ok", 0)
            lines.append(f"👕 POD — {ok}/{batch} designs produits")
            platforms = sorted({d.get("platform", "general")
                                for d in pod.get("designs", []) if d.get("status") == "complete"})
            if platforms:
                lines.append(f"   plateformes: {', '.join(platforms)}")
            for d in pod.get("designs", []):
                icon = "✅" if d.get("status") == "complete" else "❌"
                lines.append(f"   {icon} {d.get('label', d.get('design'))} [{d.get('platform', 'general')}]")
        else:
            design, reason = chosen["pod"]
            lines.append(f"👕 POD — {design['label']} [{design['tier']}-tier] ({reason})")
            lines.append(f"   échec — {pod.get('error', '?')}")
    if "game2d" in chosen:
        pack, reason = chosen["game2d"]
        ga = results.get("game2d", {})
        lines.append(f"🎮 Game2D — {pack['label']} [{pack['tier']}-tier] ({reason})")
        if ga.get("status") == "complete":
            lines.append(f"   {ga['assets']} assets: {ga['zip']}")
        else:
            lines.append(f"   échec — {ga.get('error', '?')}")
    if "uikit" in chosen:
        kit, reason = chosen["uikit"]
        uk = results.get("uikit", {})
        lines.append(f"🕹️ UIKit — {kit['label']} [{kit['tier']}-tier] ({reason})")
        if uk.get("status") == "complete":
            lines.append(f"   {uk['assets']} éléments: {uk['zip']}")
        else:
            lines.append(f"   échec — {uk.get('error', '?')}")
    if "aipack" in chosen:
        item, reason = chosen["aipack"]
        ap = results.get("aipack", {})
        lines.append(f"🤖 AIPack — {item['label']} [{item['tier']}-tier] ({reason})")
        if ap.get("status") == "complete":
            pdf = "PDF+" if ap.get("has_pdf") else ""
            lines.append(f"   kit {pdf}{ap['chars']} car. ({ap.get('engine')}): {ap['file']}")
        else:
            lines.append(f"   échec — {ap.get('error', '?')}")
    if "shopify" in chosen:
        item, reason = chosen["shopify"]
        sp = results.get("shopify", {})
        lines.append(f"🛒 Shopify — {item['label']} [{item['tier']}-tier] ({reason})")
        if sp.get("status") == "complete":
            lines.append(f"   brouillon {sp['chars']} car.: {sp['file']}")
        else:
            lines.append(f"   échec — {sp.get('error', '?')}")
    if "premium" in chosen:
        visual, reason = chosen["premium"]
        pr = results.get("premium", {})
        lines.append(f"🎨 Premium — {visual['label']} [{visual['tier']}-tier] ({reason})")
        if pr.get("status") == "complete":
            hype = (f" · hype {pr['hype_score']:.0f}"
                    if pr.get("rode_hype") and pr.get("hype_score") is not None else "")
            lines.append(f"   {pr['niche_type']} · sujet: {pr['subject']}{hype} · {pr['backend']}")
            lines.append(f"   image: {pr.get('art')}")
        else:
            lines.append(f"   échec — {pr.get('error', '?')}")
    lines += ["", f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    return "\n".join(lines)


async def run_auto_factory(*, dry: bool = False, force: bool = False,
                           products: list[str] | None = None) -> dict:
    """Daily chain: advance each enabled line -> produce -> save -> alert.

    dry=True   : select + alert only, NO production (no spend, no state advance).
    force=True : run even if disabled in config.
    products   : override which lines to run (e.g. ["stl"]); defaults to config.
    """
    cfg = factory_cfg()
    if not cfg.get("enabled") and not (dry or force):
        return {"enabled": False, "message": "auto_factory disabled in config.json"}

    state    = _load_state()
    products = products or cfg.get("products", ["stl", "icons"])
    chosen: dict = {}

    if "stl" in products:
        chosen["stl"] = await _select(NICHES, state["stl"], cfg, allow_buzz=True)
    if "icons" in products:
        chosen["icons"] = await _select(ICON_THEMES, state["icons"], cfg, allow_buzz=False)
    if "pod" in products:
        chosen["pod"] = await _select(POD_DESIGNS, state["pod"], cfg, allow_buzz=False)
    if "game2d" in products:
        chosen["game2d"] = await _select(GAME_ASSETS_2D, state["game2d"], cfg, allow_buzz=False)
    if "uikit" in products:
        chosen["uikit"] = await _select(UI_KITS, state["uikit"], cfg, allow_buzz=False)
    if "aipack" in products:
        chosen["aipack"] = await _select(AI_PACKS, state["aipack"], cfg, allow_buzz=False)
    if "shopify" in products:
        chosen["shopify"] = await _select(SHOPIFY_TEMPLATES, state["shopify"], cfg, allow_buzz=False)
    if "premium" in products:
        chosen["premium"] = await _select(PREMIUM_VISUALS, state["premium"], cfg, allow_buzz=False)

    if dry:
        bits = []
        if "stl" in chosen:
            n, r = chosen["stl"]
            bits.append(f"STL: {n['label']} [{n['tier']}] ({r})")
        if "icons" in chosen:
            t, r = chosen["icons"]
            bits.append(f"Icônes: {t['label']} [{t['tier']}] ({r})")
        if "pod" in chosen:
            p, r = chosen["pod"]
            bits.append(f"POD: {p['label']} [{p['tier']}] ({r})")
        if "game2d" in chosen:
            g, r = chosen["game2d"]
            bits.append(f"Game2D: {g['label']} [{g['tier']}] ({r})")
        if "uikit" in chosen:
            u, r = chosen["uikit"]
            bits.append(f"UIKit: {u['label']} [{u['tier']}] ({r})")
        if "aipack" in chosen:
            a, r = chosen["aipack"]
            bits.append(f"AIPack: {a['label']} [{a['tier']}] ({r})")
        if "shopify" in chosen:
            s, r = chosen["shopify"]
            bits.append(f"Shopify: {s['label']} [{s['tier']}] ({r})")
        if "premium" in chosen:
            v, r = chosen["premium"]
            bits.append(f"Premium: {v['label']} [{v['tier']}] ({r})")
        send_telegram("🏭 Auto-Factory (DRY) — choisirait:\n" + "\n".join(bits) + "\nAucune production.")
        return {"dry": True, "chosen": {k: v[0]["key"] for k, v in chosen.items()},
                "detail": {k: {"label": v[0]["label"], "reason": v[1]} for k, v in chosen.items()}}

    results: dict = {}
    touched: dict[str, dict] = {}      # only the line(s) this run produced
    if "stl" in chosen:
        niche, _ = chosen["stl"]
        results["stl"] = await _produce_stl(niche, float(cfg.get("stl_target_size_mm", 150)))
        if niche["key"] not in state["stl"]["done"]:
            state["stl"]["done"].append(niche["key"])
        touched["stl"] = state["stl"]
    if "icons" in chosen:
        theme, _ = chosen["icons"]
        results["icons"] = await _produce_icons(theme, int(cfg.get("icon_count", 12)))
        if theme["key"] not in state["icons"]["done"]:
            state["icons"]["done"].append(theme["key"])
        touched["icons"] = state["icons"]
    if "pod" in chosen:
        pod_n = max(1, int(cfg.get("pod_per_run", 10)))   # 10 designs/jour
        design, _ = chosen["pod"]
        pod_batch: list[dict] = []
        for _ in range(pod_n):
            if design is None:
                break
            res = await _produce_pod(design)
            pod_batch.append({"label": design["label"],
                              "platform": design.get("platform", "general"), **res})
            if design["key"] not in state["pod"]["done"]:
                state["pod"]["done"].append(design["key"])
            nxt = await _select(POD_DESIGNS, state["pod"], cfg, allow_buzz=False)
            design = nxt[0] if nxt else None
        ok = sum(1 for r in pod_batch if r.get("status") == "complete")
        results["pod"] = {"status": "complete" if ok else "error",
                          "batch": len(pod_batch), "ok": ok, "designs": pod_batch}
        touched["pod"] = state["pod"]
    if "game2d" in chosen:
        pack, _ = chosen["game2d"]
        results["game2d"] = await _produce_game2d(pack)
        if pack["key"] not in state["game2d"]["done"]:
            state["game2d"]["done"].append(pack["key"])
        touched["game2d"] = state["game2d"]
    if "uikit" in chosen:
        kit, _ = chosen["uikit"]
        results["uikit"] = await _produce_uikit(kit)
        if kit["key"] not in state["uikit"]["done"]:
            state["uikit"]["done"].append(kit["key"])
        touched["uikit"] = state["uikit"]
    if "aipack" in chosen:
        item, _ = chosen["aipack"]
        results["aipack"] = await _produce_aipack(item)
        if item["key"] not in state["aipack"]["done"]:
            state["aipack"]["done"].append(item["key"])
        touched["aipack"] = state["aipack"]
    if "shopify" in chosen:
        item, _ = chosen["shopify"]
        results["shopify"] = await _produce_shopify(item)
        if item["key"] not in state["shopify"]["done"]:
            state["shopify"]["done"].append(item["key"])
        touched["shopify"] = state["shopify"]
    if "premium" in chosen:
        visual, _ = chosen["premium"]
        results["premium"] = await _produce_premium(visual)
        if visual["key"] not in state["premium"]["done"]:
            state["premium"]["done"].append(visual["key"])
        touched["premium"] = state["premium"]

    _save_lines(touched)               # atomic, per-line merge — overlap-safe
    send_telegram(_format_alert(chosen, results))
    return {"produced": True, "forced": force,
            "chosen": {k: v[0]["key"] for k, v in chosen.items()}, "results": results}


# ── Scheduler entry + manual routes ───────────────────────────────────────────

async def _safe_run(products: list[str], label: str) -> dict:
    try:
        return await run_auto_factory(products=products)
    except Exception as e:
        print(f"[auto_factory] {label} run failed: {e}")
        send_telegram(f"🏭 Auto-Factory ({label}): crash — {e}")
        return {"error": str(e)}


async def task_auto_factory_stl():
    """APScheduler entry — STL line only (its own Command Center task)."""
    return await _safe_run(["stl"], "STL")


async def task_auto_factory_icons():
    """APScheduler entry — icon-pack line only (its own Command Center task)."""
    return await _safe_run(["icons"], "Icons")


async def task_auto_factory_pod():
    """APScheduler entry — POD textile line only (its own Command Center task)."""
    return await _safe_run(["pod"], "POD")


async def task_auto_factory_game2d():
    """APScheduler entry — 2D game-asset line only (its own Command Center task)."""
    return await _safe_run(["game2d"], "Game2D")


async def task_auto_factory_uikit():
    """APScheduler entry — game UI-kit line only (its own Command Center task)."""
    return await _safe_run(["uikit"], "UIKit")


async def task_auto_factory_aipack():
    """APScheduler entry — AI/automation pack line only (Ollama, draft output)."""
    return await _safe_run(["aipack"], "AIPack")


async def task_auto_factory_shopify():
    """APScheduler entry — Shopify section line only (Ollama, draft output)."""
    return await _safe_run(["shopify"], "Shopify")


async def task_auto_factory_premium():
    """APScheduler entry — VALKYRIE premium gpt-image-1 line (its own task)."""
    return await _safe_run(["premium"], "Premium")


async def task_auto_factory():
    """Manual/combined entry — runs all lines per config."""
    return await _safe_run(
        ["stl", "icons", "pod", "game2d", "uikit", "aipack", "shopify", "premium"], "all")


async def task_auto_factory_bundles():
    """APScheduler entry — stack the day's atoms into sellable bundles (recompose.py).

    Runs in the LAST staggered slot, after every atom line, so each line's fresh
    .zip is already on disk. Disk-driven: recompose picks the newest atom per key.
    Best-effort — a bundle with no atoms yet is reported 'empty', never an error.
    """
    try:
        from recompose import recompose_all
        results = await asyncio.to_thread(recompose_all, False, None)
    except Exception as e:
        print(f"[auto_factory] bundle run failed: {e}")
        send_telegram(f"📦 Auto-Factory (Bundles): crash — {e}")
        return {"error": str(e)}
    built = [r for r in results if r.get("status") == "built"]
    empty = [r for r in results if r.get("status") == "empty"]
    lines = ["📦 Auto-Factory — Bundles", f"{len(built)}/{len(results)} bundles bâtis."]
    for r in built:
        lines.append(f"• {r['id']} — {r['atom_count']} packs (${r['price_usd']})")
        if r.get("zip"):
            lines.append(f"   {r['zip']}")
    if empty:
        lines.append(f"({len(empty)} vides — pas encore d'atomes)")
    send_telegram("\n".join(lines))
    return {"bundles_built": len(built), "results": results}


router = APIRouter(prefix="/v1/factory", tags=["auto_factory"])


@router.get("/config")
def get_config() -> dict:
    return {"config": factory_cfg(), "state": _load_state(),
            "stl_niches": len(NICHES), "icon_themes": len(ICON_THEMES),
            "pod_designs": len(POD_DESIGNS), "game2d_packs": len(GAME_ASSETS_2D),
            "uikit_kits": len(UI_KITS), "aipack_packs": len(AI_PACKS),
            "shopify_templates": len(SHOPIFY_TEMPLATES),
            "premium_visuals": len(PREMIUM_VISUALS)}


@router.get("/catalog")
def list_catalog() -> dict:
    def _slim(items):
        return [{"key": i["key"], "tier": i["tier"], "label": i["label"]} for i in items]
    return {
        "stl_niches":  _slim(NICHES),
        "icon_themes": _slim(ICON_THEMES),
        "pod_designs": _slim(POD_DESIGNS),
        "game2d_packs": _slim(GAME_ASSETS_2D),
        "uikit_kits": _slim(UI_KITS),
        "aipack_packs": _slim(AI_PACKS),
        "shopify_templates": _slim(SHOPIFY_TEMPLATES),
        "premium_visuals": _slim(PREMIUM_VISUALS),
    }


@router.post("/run")
async def run_now(dry: bool = False, force: bool = False) -> dict:
    """Manual trigger. ?dry=true = select+alert only; ?force=true = run even if disabled."""
    return await run_auto_factory(dry=dry, force=force)


@router.post("/bundles")
async def bundles_now(dry: bool = False, only: str | None = None) -> dict:
    """Manual trigger for the bundling layer (recompose.py).

    ?dry=true = show what would build, write nothing; ?only=<bundle_id> = one bundle.
    """
    from recompose import recompose_all
    results = await asyncio.to_thread(recompose_all, dry, only)
    return {"dry": dry, "results": results}


# Chaque ligne dépose ses produits finis dans un dossier Jarvis dédié — c'est le
# "product making" de la ligne. Le Factory Hub ouvre ce dossier d'un clic.
_LINE_OUTPUT_DIRS: dict[str, Path] = {
    "stl":     JARVIS_STL_DIR,
    "icons":   JARVIS_ICONS_DIR,
    "pod":     JARVIS_POD_DIR,
    "game2d":  JARVIS_GAME2D_DIR,
    "uikit":   JARVIS_UIKIT_DIR,
    "aipack":  JARVIS_AIPACK_DIR,
    "shopify": JARVIS_SHOPIFY_DIR,
    "premium": JARVIS_PREMIUM_DIR,
}


@router.post("/open-output/{line}")
def open_output_folder(line: str) -> dict:
    """Ouvre dans l'explorateur Windows le dossier des produits finis d'une ligne
    (stl, icons, pod, game2d, uikit, aipack, shopify, premium)."""
    import subprocess

    d = _LINE_OUTPUT_DIRS.get(line)
    if d is None:
        raise HTTPException(status_code=404, detail=f"ligne inconnue: {line}")
    d.mkdir(parents=True, exist_ok=True)  # peut être vide si aucun produit encore
    try:
        subprocess.Popen(["explorer", str(d)], shell=False)  # NOSONAR - fire-and-forget GUI launch
        return {"status": "opened", "line": line, "path": str(d)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ouverture échouée: {e}") from e

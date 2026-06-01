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
    TIER_RANK,
    UI_KITS,
)
from fastapi import APIRouter

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


def _seed(s: str) -> int:
    """Stable non-negative seed from a string (process-independent)."""
    return zlib.crc32(s.encode("utf-8")) & 0x7FFFFFFF


def _remove_bg(png: bytes) -> bytes:
    """Detour a POD design onto a transparent background (best-effort).

    FLUX renders on white; this strips it so the design prints on any shirt
    colour. Returns the original bytes unchanged if rembg isn't installed or
    fails — the pipeline never breaks on a missing optional dependency.
    """
    try:
        from rembg import remove
        return remove(png)
    except Exception as e:
        print(f"[auto_factory] rembg unavailable — keeping white bg: {e}")
        return png

DEFAULTS: dict = {
    "enabled":            True,
    "schedule_hour":      8,
    "schedule_minute":    0,
    "selection_mode":     "tier_rotation",  # tier_rotation | buzz_rerank | weighted_random
    "spike_check":        False,            # STL line: a buzz spike jumps the queue
    "spike_threshold":    60,               # score (0-100) that counts as "spiking"
    "products":           ["stl", "icons", "pod", "game2d", "uikit", "aipack"],
    "icon_count":         12,               # subset of the 30-app catalog per pack
    "stl_target_size_mm": 150.0,
    "pod_art_size":       1024,             # FLUX render size for POD designs
    "game2d_item_size":   768,              # FLUX render size per game/UI asset
    "game2d_max_items":   8,                # items rendered per pack (cost/time cap)
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
    state.setdefault("uikit",  {"done": [], "cycle": 1})
    state.setdefault("aipack", {"done": [], "cycle": 1})
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


async def _produce_pod(design: dict) -> dict:
    """POD line: FLUX art -> listing draft -> save (local + Jarvis/POD) ->
    Printify sync (gated on PRINTIFY_API_KEY)."""
    from iconforge.generators.comfyui_client import ComfyUIClient
    client = ComfyUIClient()
    if not client.is_available():
        return {"status": "error", "error": "ComfyUI indisponible (design POD)"}
    client.unload_ollama()                       # free VRAM for FLUX

    size = int(factory_cfg().get("pod_art_size", 1024))
    try:
        png = await asyncio.to_thread(client.generate, design["art_prompt"],
                                      _seed(design["key"]), size)
    except Exception as e:
        return {"status": "error", "error": f"FLUX: {e}"}

    png = await asyncio.to_thread(_remove_bg, png)   # -> transparent background

    # Listing draft (Etsy allows 13 tags). No slogans baked into the art — FLUX
    # text is unreliable; the design is illustrative, the text lives in metadata.
    tags  = design["tags"][:13]
    title = f"{design['label']} {design['product'].title()} - Aesthetic Graphic Tee Gift"
    desc  = (f"{design['label']} — design original, imprimé à la demande.\n\n"
             f"Produit: {design['product']}. Impression haute qualité, "
             f"plusieurs tailles et couleurs.\nMots-clés: {', '.join(tags)}")
    listing = {"title": title, "tags": tags, "description": desc,
               "price_usd": 24.99, "product": design["product"], "design": design["key"]}

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{design['key']}_{ts}"
    out_dir = BACKEND_DIR / "pod_output" / base
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{base}.png").write_bytes(png)
    (out_dir / "listing.json").write_text(
        json.dumps(listing, indent=2, ensure_ascii=False), encoding="utf-8")

    jarvis_art = None
    try:
        JARVIS_POD_DIR.mkdir(parents=True, exist_ok=True)
        jarvis_art = str(JARVIS_POD_DIR / f"{base}.png")
        shutil.copy2(str(out_dir / f"{base}.png"), jarvis_art)
        shutil.copy2(str(out_dir / "listing.json"), str(JARVIS_POD_DIR / f"{base}.listing.json"))
    except Exception as e:
        print(f"[auto_factory] Jarvis POD copy failed: {e}")

    import printify_client
    pf = printify_client.sync(f"{base}.png", png, title, desc, tags)
    return {"status": "complete", "design": design["key"],
            "art": jarvis_art or str(out_dir / f"{base}.png"),
            "listing": str(out_dir / "listing.json"), "printify": pf}


async def _produce_pack(pack: dict, *, out_subdir: str, jarvis_dir: Path,
                        price: float, title_suffix: str) -> dict:
    """Generic FLUX asset-pack producer (shared by the game-asset and UI-kit
    lines): render each item in `pack["items"]` with the shared `pack["style"]`,
    strip the bg (transparent), bundle into a ZIP + listing.json, copy to Jarvis."""
    from iconforge.generators.comfyui_client import ComfyUIClient
    client = ComfyUIClient()
    if not client.is_available():
        return {"status": "error", "error": "ComfyUI indisponible"}
    client.unload_ollama()

    cfg  = factory_cfg()
    size = int(cfg.get("game2d_item_size", 768))
    cap  = int(cfg.get("game2d_max_items", 8))
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{pack['key']}_{ts}"
    out_dir = BACKEND_DIR / out_subdir / base
    out_dir.mkdir(parents=True, exist_ok=True)

    made: list[str] = []
    for item in pack["items"][: max(1, cap)]:
        try:
            png = await asyncio.to_thread(client.generate, f"{item}, {pack['style']}",
                                          _seed(pack["key"] + item), size)
            png = await asyncio.to_thread(_remove_bg, png)
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
                               title_suffix="2D Game Asset Pack")


async def _produce_uikit(kit: dict) -> dict:
    return await _produce_pack(kit, out_subdir="uikit_output",
                               jarvis_dir=JARVIS_UIKIT_DIR, price=19.99,
                               title_suffix="Game UI Kit")


async def _produce_aipack(item: dict) -> dict:
    """AI / automation pack line: Ollama (local LLM, free) writes a Markdown
    pack. HONEST: DRAFT output meant to be curated, not a finished product."""
    from ollama_client import ask_ollama, strip_think_tags
    system = ("You create sellable digital AI/automation packs. Output clean, "
              "ready-to-use Markdown ONLY — no preamble, no commentary.")
    content = await asyncio.to_thread(ask_ollama, f"{system}\n\n{item['brief']}")
    if not content:
        return {"status": "error", "error": "Ollama indisponible / timeout"}
    content = strip_think_tags(content)

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{item['key']}_{ts}"
    out_dir = BACKEND_DIR / "aipack_output" / base
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{item['key']}.md").write_text(content, encoding="utf-8")
    listing = {"title": f"{item['label']} - AI Automation Pack",
               "price_usd": 12.99, "draft": True, "pack": item["key"]}
    (out_dir / "listing.json").write_text(
        json.dumps(listing, indent=2, ensure_ascii=False), encoding="utf-8")

    jarvis_file = None
    try:
        JARVIS_AIPACK_DIR.mkdir(parents=True, exist_ok=True)
        jarvis_file = str(JARVIS_AIPACK_DIR / f"{base}.md")
        shutil.copy2(str(out_dir / f"{item['key']}.md"), jarvis_file)
    except Exception as e:
        print(f"[auto_factory] Jarvis aipack copy failed: {e}")

    return {"status": "complete", "pack": item["key"], "chars": len(content),
            "file": jarvis_file or str(out_dir / f"{item['key']}.md")}


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
        design, reason = chosen["pod"]
        pod = results.get("pod", {})
        lines.append(f"👕 POD — {design['label']} [{design['tier']}-tier] ({reason})")
        if pod.get("status") == "complete":
            lines.append(f"   design: {pod.get('art')}")
            pf = pod.get("printify", {})
            st = pf.get("status")
            if st == "product_created":
                lines.append(f"   Printify: produit créé {pf.get('product_id')}"
                             + (" + PUBLIÉ" if pf.get("published") else " (brouillon)"))
            elif st == "uploaded":
                lines.append("   Printify: image uploadée (config produit incomplète)")
            elif st == "skipped":
                lines.append("   Printify: local seulement (pas de clé) — prêt à uploader")
            else:
                lines.append(f"   Printify: {pf.get('reason', st)}")
        else:
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
            lines.append(f"   brouillon {ap['chars']} car.: {ap['file']}")
        else:
            lines.append(f"   échec — {ap.get('error', '?')}")
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
        design, _ = chosen["pod"]
        results["pod"] = await _produce_pod(design)
        if design["key"] not in state["pod"]["done"]:
            state["pod"]["done"].append(design["key"])
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


async def task_auto_factory():
    """Manual/combined entry — runs all lines per config."""
    return await _safe_run(["stl", "icons", "pod", "game2d", "uikit", "aipack"], "all")


router = APIRouter(prefix="/v1/factory", tags=["auto_factory"])


@router.get("/config")
def get_config() -> dict:
    return {"config": factory_cfg(), "state": _load_state(),
            "stl_niches": len(NICHES), "icon_themes": len(ICON_THEMES),
            "pod_designs": len(POD_DESIGNS), "game2d_packs": len(GAME_ASSETS_2D),
            "uikit_kits": len(UI_KITS), "aipack_packs": len(AI_PACKS)}


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
    }


@router.post("/run")
async def run_now(dry: bool = False, force: bool = False) -> dict:
    """Manual trigger. ?dry=true = select+alert only; ?force=true = run even if disabled."""
    return await run_auto_factory(dry=dry, force=force)

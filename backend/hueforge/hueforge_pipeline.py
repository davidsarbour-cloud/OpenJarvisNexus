"""HueForge — gestion des missions + pipeline 7 étapes.

Étapes :
  1. routing       — validation entrée + résolution de la source (ComfyUI vs image)
  2. generation    — ComfyUI/FLUX (texte→image) OU ingestion de l'image fournie
  3. resize        — côté le plus long → ``size`` px (ratio préservé)
  4. contrast      — augmentation du contraste (ImageEnhance)
  5. background    — suppression du fond (rembg) + aplatissement optionnel
  6. export        — sauvegarde dans « Prêt pour HueForge » (+ copie de travail)
  7. report        — palette dominante + rapport JSON + persistance du cache

Calque sur ``forge_room.fabrication_pipeline`` : même forme de mission, même cache
glissant 24h, mêmes helpers ``_log/_step``. La génération passe TOUJOURS par le
service partagé ``services.comfyui_images`` (jamais d'appel ComfyUI ad-hoc).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import traceback
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image

from hueforge import filament_lab, image_ops, variant_lab

# ── Dossiers de sortie ───────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).parent.parent
HUEFORGE_OUTPUT = _BACKEND_DIR / "hueforge_output"          # PNG de travail (raw + final)
# Dossier final demandé par David : « Prêt pour HueForge ». Surchargé via env.
HUEFORGE_READY = Path(
    os.getenv("HUEFORGE_READY_DIR", str(HUEFORGE_OUTPUT / "Pret_pour_HueForge"))
)
HUEFORGE_OUTPUT.mkdir(exist_ok=True)
HUEFORGE_READY.mkdir(parents=True, exist_ok=True)

_MISSIONS_CACHE = _BACKEND_DIR / "hueforge_missions_cache.json"

STEP_LABELS = [
    "routing", "generation", "resize", "contrast", "background", "export", "report",
]
# Étapes additionnelles, ajoutées au dict steps de la mission UNIQUEMENT si le tier
# est activé (STEP_LABELS reste immuable ; progress_pct = done/len(steps) reste juste).
T2_STEPS = ["variant_generation", "best_selection", "etsy_preview"]
T3_STEPS = ["filament_analysis", "layer_change_estimation", "hueforge_render_simulation", "print_params"]

# Valeurs par défaut des paramètres (alignées avec le modèle Pydantic du routeur).
DEFAULT_PARAMS = {
    "size": 1024,
    "contrast": 1.35,
    "remove_bg": True,
    "flatten_bg": None,   # None = garde le PNG transparent ; "#ffffff" = aplatit
    "seed": 0,
    "palette_colors": 6,
    "source": "comfyui",  # "comfyui" (texte→image) ou "image" (fichier fourni)
    # Tier 2 (variantes + sélection + aperçu Etsy) — opt-in
    "tier2": False,
    "variants_count": 3,
    "variant_strategy": "contrast_range",  # contrast_range | seed_variation | comfyui_prompt_tweak
    # Tier 3 (filaments + couches + simulation + paramètres) — opt-in
    "tier3": False,
    "layer_height": 0.08,
    "model_height_mm": 3.0,
    # Taille physique cible de la plaque (mm). Si les deux sont fournis, l'image est
    # recadrée à ce ratio et la taille suit jusqu'aux paramètres d'impression / HueForge.
    "target_w_mm": None,
    "target_h_mm": None,
    # Ouvre automatiquement le PNG final (HueForge si trouvé, sinon Explorateur).
    "auto_open": False,
}


# ── Cache des missions (fenêtre glissante 24h) ───────────────────────────────
def _load_cache() -> dict:
    try:
        if _MISSIONS_CACHE.exists():
            return json.loads(_MISSIONS_CACHE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_cache(missions: dict) -> None:
    """Ne garde que les missions des dernières 24h."""
    try:
        cutoff = datetime.now() - timedelta(hours=24)
        pruned: dict = {}
        for mid, m in missions.items():
            try:
                created_dt = datetime.fromisoformat(m.get("created_at", ""))
            except (TypeError, ValueError):
                pruned[mid] = m  # pas de timestamp valide → on garde par sécurité
                continue
            if created_dt >= cutoff:
                pruned[mid] = m
        _MISSIONS_CACHE.write_text(
            json.dumps(pruned, ensure_ascii=False, default=str), encoding="utf-8"
        )
    except Exception:
        pass


_hueforge_missions: dict = _load_cache()


def _slugify(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return (s or "hueforge")[:limit]


def open_in_hueforge(file_path: str) -> dict:
    """Ouvre le PNG final : app HueForge si trouvée, sinon l'Explorateur (fichier
    sélectionné). Best-effort, non bloquant. Renvoie {opened, via, target/error}.

    Chemin de l'app via env HUEFORGE_PATH, sinon emplacements d'install connus.
    """
    import os
    import subprocess
    import sys

    p = Path(file_path)
    if not p.exists():
        return {"opened": False, "via": None, "error": "fichier introuvable"}

    home = Path.home()
    candidates = [
        os.getenv("HUEFORGE_PATH", ""),
        str(home / "AppData" / "Local" / "Programs" / "HueForge" / "HueForge.exe"),
        r"C:\Program Files\HueForge\HueForge.exe",
        str(home / "AppData" / "Local" / "HueForge" / "HueForge.exe"),
    ]
    for exe in candidates:
        if exe and Path(exe).exists():
            try:
                subprocess.Popen([exe, str(p)], shell=False)
                return {"opened": True, "via": "hueforge", "target": exe}
            except Exception as e:  # noqa: BLE001 - best-effort
                print(f"[HUEFORGE] lancement HueForge echoue: {e}")

    # Repli : Explorateur Windows avec le fichier sélectionné (toujours utile).
    if sys.platform == "win32":
        try:
            subprocess.Popen(["explorer", f"/select,{p}"], shell=False)
            return {"opened": True, "via": "explorer", "target": str(p)}
        except Exception as e:  # noqa: BLE001
            print(f"[HUEFORGE] ouverture Explorateur echouee: {e}")
    return {"opened": False, "via": None, "error": "aucune methode d'ouverture (definis HUEFORGE_PATH)"}


def new_mission(prompt: str, params: dict | None = None, image_path: str | None = None) -> dict:
    """Crée une mission (ou renvoie une identique déjà en cours, anti-duplication <5min)."""
    prompt_stripped = (prompt or "").strip()
    p = {**DEFAULT_PARAMS, **(params or {})}
    if image_path:
        p["source"] = "image"

    # Anti-duplication : même prompt + mêmes tiers running depuis <5min (ignoré pour
    # les images, déjà désambiguïsées par leur chemin disque). Les tiers entrent dans
    # l'égalité pour qu'une mission tier1 et une mission tier2/3 du même prompt ne
    # soient pas fusionnées à tort.
    if prompt_stripped and not image_path:
        for existing in _hueforge_missions.values():
            ep = existing.get("params", {})
            if (
                existing.get("status") == "running"
                and existing.get("prompt", "").strip() == prompt_stripped
                and bool(ep.get("tier2")) == bool(p.get("tier2"))
                and bool(ep.get("tier3")) == bool(p.get("tier3"))
            ):
                try:
                    age_s = (datetime.now() - datetime.fromisoformat(existing["created_at"])).total_seconds()
                    if age_s < 300:
                        print(f"[HUEFORGE] Anti-dup: mission {existing['id']} en cours ({age_s:.0f}s)")
                        return existing
                except Exception:
                    pass

    # Le dict steps inclut les étapes des tiers activés (ordre = exécution logique).
    step_names = list(STEP_LABELS)
    if p.get("tier2"):
        step_names += T2_STEPS
    if p.get("tier3"):
        step_names += T3_STEPS

    mid = str(uuid.uuid4())[:8].upper()
    m = {
        "id": mid,
        "prompt": prompt_stripped,
        "status": "running",
        "current_step": "routing",
        "steps": {s: "pending" for s in step_names},
        "params": p,
        "files": {"input_image": image_path} if image_path else {},
        "palette": None,
        "report": None,
        "logs": [],
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
    }
    _hueforge_missions[mid] = m
    _save_cache(_hueforge_missions)
    return m


def get_mission(mid: str):
    m = _hueforge_missions.get(mid)
    if m is None:
        fresh = _load_cache()
        if mid in fresh:
            _hueforge_missions.update(fresh)
            m = _hueforge_missions.get(mid)
    return m


def _log(m: dict, msg: str, level: str = "info") -> None:
    m["logs"].append({"ts": datetime.now().strftime("%H:%M:%S"), "msg": msg, "level": level})
    print(f"[HUEFORGE:{m['id']}] [{level.upper()}] {msg}")


def _step(m: dict, name: str) -> None:
    m["steps"][name] = "running"
    m["current_step"] = name


def _step_done(m: dict, name: str) -> None:
    m["steps"][name] = "done"


def _step_fail(m: dict, name: str, reason: str) -> None:
    m["steps"][name] = "failed"
    _log(m, f"ÉTAPE ÉCHOUÉE [{name}]: {reason}", "error")


# ── Pipeline ─────────────────────────────────────────────────────────────────
async def run_hueforge_pipeline(mission_id: str) -> dict:
    """Exécute le pipeline complet pour une mission. Robuste : journalise chaque
    étape, marque la mission ``failed`` sur erreur dure, persiste le cache."""
    m = get_mission(mission_id)
    if not m:
        return {"error": f"mission {mission_id} introuvable"}
    p = m["params"]

    try:
        # 1. ROUTING ----------------------------------------------------------
        _step(m, "routing")
        if p.get("source") != "image" and not m.get("prompt"):
            _step_fail(m, "routing", "prompt ou image requis")
            raise ValueError("prompt ou image requis")
        _log(m, f"source={p.get('source')} · size={p['size']} · contrast={p['contrast']} "
                f"· remove_bg={p['remove_bg']}")
        _step_done(m, "routing")

        # 2. GENERATION / INGESTION ------------------------------------------
        _step(m, "generation")
        if p.get("source") == "image":
            src_path = m.get("files", {}).get("input_image")
            if not src_path or not Path(src_path).exists():
                _step_fail(m, "generation", "image source introuvable sur le disque")
                raise FileNotFoundError("image source introuvable")
            img = await asyncio.to_thread(lambda: Image.open(src_path))
            _log(m, f"image ingérée: {Path(src_path).name} ({img.size[0]}x{img.size[1]})")
        else:
            from services import comfyui_images

            if not await asyncio.to_thread(comfyui_images.is_available):
                _step_fail(m, "generation", "ComfyUI injoignable (container éteint ?)")
                raise RuntimeError("ComfyUI injoignable - demarre le container iconforge-comfyui")
            # Libère la VRAM (évince Ollama) pour que FLUX FP8 tienne en 12 Go.
            await asyncio.to_thread(comfyui_images.unload_ollama)
            png = await asyncio.to_thread(
                comfyui_images.render, m["prompt"], size=int(p["size"]), seed=int(p["seed"])
            )
            img = await asyncio.to_thread(image_ops.load_image, png)
            _log(m, f"FLUX render OK ({img.size[0]}x{img.size[1]})")
            raw_path = HUEFORGE_OUTPUT / f"{m['id']}_raw.png"
            await asyncio.to_thread(img.convert("RGB").save, str(raw_path), "PNG")
            m["files"]["raw"] = str(raw_path)
        # On travaille en RGB jusqu'à l'étape background (contraste propre, pas d'alpha).
        img = img.convert("RGB")
        # Recadrage au ratio de la plaque physique cible (ex: 119x47 mm) si fourni,
        # pour que HueForge n'étire pas l'image à l'import. Fait sur la base -> hérité
        # par les variantes (tier2) comme par le flux tier1.
        _tw, _th = p.get("target_w_mm"), p.get("target_h_mm")
        if _tw and _th:
            img = await asyncio.to_thread(image_ops.crop_to_aspect, img, float(_tw), float(_th))
            _log(m, f"recadrage plaque {_tw}x{_th}mm -> {img.size[0]}x{img.size[1]}px")
        _step_done(m, "generation")

        removed = False
        if p.get("tier2"):
            # ── TIER 2 : variantes + sélection auto (remplace resize/contraste/fond) ──
            _step(m, "variant_generation")
            render_fn = None
            if p.get("source") == "comfyui":
                from services import comfyui_images
                render_fn = comfyui_images.render  # pour seed_variation / prompt_tweak
            vdir = HUEFORGE_OUTPUT / m["id"] / "variants"
            variants = await variant_lab.generate_variants(
                img, count=int(p["variants_count"]), strategy=p["variant_strategy"],
                params=p, out_dir=vdir, render_fn=render_fn, prompt=m["prompt"],
            )
            m["variants"] = variants
            _log(m, f"{len(variants)} variantes generees ({p['variant_strategy']})")
            _step_done(m, "variant_generation")

            _step(m, "best_selection")
            sel = variant_lab.select_best_variant(variants)
            if not sel:
                _step_fail(m, "best_selection", "aucune variante generee")
                raise RuntimeError("aucune variante generee")
            winner = sel["winner"]
            m["best_variant_id"] = sel["best_variant_id"]
            m["variant_selection"] = {"best_variant_id": sel["best_variant_id"], "rationale": sel["rationale"]}
            img = await asyncio.to_thread(lambda: Image.open(winner["file"]).copy())
            removed = bool(winner.get("bg_removed"))
            m["report_bg_removed"] = removed
            # Le gagnant est déjà resize+contraste+fond : on marque ces étapes faites.
            for s in ("resize", "contrast", "background"):
                if s in m["steps"]:
                    _step_done(m, s)
            _log(m, f"variante gagnante {sel['best_variant_id']} - {sel['rationale']}")
            _step_done(m, "best_selection")
        else:
            # 3. RESIZE -------------------------------------------------------
            _step(m, "resize")
            img = await asyncio.to_thread(image_ops.resize_longest, img, int(p["size"]))
            _log(m, f"resize -> {img.size[0]}x{img.size[1]} (cote long {p['size']}px)")
            _step_done(m, "resize")

            # 4. CONTRAST -----------------------------------------------------
            _step(m, "contrast")
            img = await asyncio.to_thread(image_ops.boost_contrast, img, float(p["contrast"]))
            _log(m, f"contraste x{p['contrast']}")
            _step_done(m, "contrast")

            # 5. BACKGROUND ---------------------------------------------------
            _step(m, "background")
            if p.get("remove_bg", True):
                img, removed = await asyncio.to_thread(image_ops.remove_background, img)
                _log(m, "fond supprime (rembg)" if removed else "rembg indisponible - fond conserve",
                     "info" if removed else "warning")
                flat = p.get("flatten_bg")
                if removed and flat:
                    img = await asyncio.to_thread(image_ops.flatten_onto, img, flat)
                    _log(m, f"aplati sur fond {flat}")
            else:
                _log(m, "suppression du fond désactivée")
            m["report_bg_removed"] = removed
            _step_done(m, "background")

        # 6. EXPORT → « Prêt pour HueForge » ----------------------------------
        _step(m, "export")
        slug = _slugify(m["prompt"] or Path(m.get("files", {}).get("input_image", "image")).stem)
        final_name = f"{m['id']}_{slug}.png"
        final_path = HUEFORGE_READY / final_name
        work_copy = HUEFORGE_OUTPUT / final_name
        await asyncio.to_thread(img.save, str(final_path), "PNG")
        await asyncio.to_thread(img.save, str(work_copy), "PNG")
        m["files"]["final"] = str(final_path)
        m["files"]["work_copy"] = str(work_copy)
        _log(m, f"export -> {final_path}")
        _step_done(m, "export")

        # 6b. APERCU ETSY (tier 2) -------------------------------------------
        if p.get("tier2"):
            _step(m, "etsy_preview")
            etsy_dir = HUEFORGE_OUTPUT / m["id"] / "etsy"
            etsy_dir.mkdir(parents=True, exist_ok=True)
            ready_etsy = HUEFORGE_READY / "etsy_previews"
            ready_etsy.mkdir(parents=True, exist_ok=True)
            previews: dict = {}
            for vr in m.get("variants", []):
                try:
                    vimg = await asyncio.to_thread(lambda f=vr["file"]: Image.open(f).copy())
                    png = await asyncio.to_thread(
                        variant_lab.render_etsy_preview, vimg, m["prompt"] or "HueForge", vr.get("palette") or [])
                    pth = etsy_dir / f"{vr['id']}_etsy.png"
                    await asyncio.to_thread(pth.write_bytes, png)
                    previews[vr["id"]] = str(pth)
                except Exception as ex:  # noqa: BLE001 - un aperçu raté ne casse pas la mission
                    _log(m, f"apercu Etsy {vr.get('id')} echoue: {ex}", "warning")
            win_id = m.get("best_variant_id")
            if win_id and win_id in previews:
                winner_preview = ready_etsy / f"{m['id']}_{slug}_etsy.png"
                await asyncio.to_thread(
                    lambda: winner_preview.write_bytes(Path(previews[win_id]).read_bytes()))
                m["files"]["etsy_preview"] = str(winner_preview)
            m["files"]["etsy_previews"] = previews
            _log(m, f"{len(previews)} apercus Etsy generes")
            _step_done(m, "etsy_preview")

        # 7. REPORT (palette dominante) ---------------------------------------
        _step(m, "report")
        palette = await asyncio.to_thread(image_ops.dominant_colors, img, int(p["palette_colors"]))
        m["palette"] = palette
        report = {
            "mission_id": m["id"],
            "prompt": m["prompt"],
            "source": p.get("source"),
            "size_px": img.size,
            "contrast": p["contrast"],
            "background_removed": removed,
            "flattened_bg": p.get("flatten_bg") if removed else None,
            "palette": palette,
            "suggested_filament_changes": max(0, len(palette) - 1),
            "plate_size_mm": [float(p["target_w_mm"]), float(p["target_h_mm"])]
                             if (p.get("target_w_mm") and p.get("target_h_mm")) else None,
            "final_file": m["files"].get("final"),
            "ready_dir": str(HUEFORGE_READY),
            "created_at": m["created_at"],
        }
        if p.get("tier2"):
            report["variants"] = [
                {"id": v["id"], "score": v["score"], "contrast": v["contrast"], "components": v["components"]}
                for v in m.get("variants", [])
            ]
            report["best_variant_id"] = m.get("best_variant_id")
            report["variant_selection"] = m.get("variant_selection")
        report_path = HUEFORGE_OUTPUT / f"{m['id']}_report.json"
        await asyncio.to_thread(
            report_path.write_text, json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        m["files"]["report"] = str(report_path)
        m["report"] = report
        _step_done(m, "report")

        # 8. TIER 3 : filaments -> couches -> simulation -> paramètres --------
        if p.get("tier3"):
            inv = await asyncio.to_thread(filament_lab.load_inventory)
            _plate = ((float(p["target_w_mm"]), float(p["target_h_mm"]))
                      if (p.get("target_w_mm") and p.get("target_h_mm")) else None)

            _step(m, "filament_analysis")
            m["filament_analysis"] = await asyncio.to_thread(filament_lab.analyze_filaments, palette, inv)
            _log(m, f"filaments: couverture {m['filament_analysis']['coverage_pct']}% "
                    f"({inv.get('slots')} slots, {m['filament_analysis']['owned_count']} bobines)")
            _step_done(m, "filament_analysis")

            _step(m, "layer_change_estimation")
            bands = await asyncio.to_thread(
                filament_lab.estimate_layer_changes, palette, inv,
                layer_height=float(p["layer_height"]), model_height_mm=float(p["model_height_mm"]))
            m["layer_changes"] = bands
            _log(m, f"{len(bands)} bandes de couleur, {max(0, len(bands) - 1)} changements de filament")
            _step_done(m, "layer_change_estimation")

            _step(m, "hueforge_render_simulation")
            sim = await asyncio.to_thread(
                filament_lab.simulate_hueforge_render, img, bands,
                layer_height=float(p["layer_height"]), model_height_mm=float(p["model_height_mm"]),
                plate_mm=_plate)
            sim_png = sim.pop("preview_png", None)
            if sim_png:
                sim_path = HUEFORGE_OUTPUT / m["id"] / "render_sim.png"
                sim_path.parent.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(sim_path.write_bytes, sim_png)
                m["files"]["render_sim"] = str(sim_path)
            m["hueforge_render"] = sim
            _log(m, f"simulation rendu ({sim.get('method')}, approx={sim.get('approx')})")
            _step_done(m, "hueforge_render_simulation")

            _step(m, "print_params")
            pp = await asyncio.to_thread(
                filament_lab.build_print_params, bands,
                layer_height=float(p["layer_height"]), model_height_mm=float(p["model_height_mm"]),
                plate_mm=_plate)
            m["print_params"] = pp
            _log(m, f"params: {pp.get('color_swap_count', 0)} swaps, {pp.get('total_layers', 0)} couches")
            _step_done(m, "print_params")

            # Fusion tier3 dans le rapport + ré-écriture du JSON.
            report["filament_analysis"] = m["filament_analysis"]
            report["layer_changes"] = bands
            report["hueforge_render"] = sim
            report["print_params"] = pp
            await asyncio.to_thread(
                report_path.write_text, json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            m["report"] = report

        m["status"] = "completed"
        m["completed_at"] = datetime.now().isoformat()
        _log(m, f"mission terminee OK - {len(palette)} couleurs dominantes")

        # Ouverture auto du fichier final (HueForge si trouvée, sinon Explorateur).
        if p.get("auto_open") and m["files"].get("final"):
            res_open = await asyncio.to_thread(open_in_hueforge, m["files"]["final"])
            m["opened"] = res_open
            _log(m, f"ouverture auto: {res_open.get('via') or 'echec'}")
    except Exception as e:  # noqa: BLE001 - on capture pour marquer la mission failed
        m["status"] = "failed"
        m["completed_at"] = datetime.now().isoformat()
        m["error"] = str(e)
        # Toute étape non terminée (running/pending) devient "failed" : sinon des
        # steps tier2/tier3 restaient "running" et le progress n'atteignait jamais
        # un état cohérent (UI ne distinguait plus "en cours" de "échoué").
        for _sname, _sstate in m["steps"].items():
            if _sstate in ("pending", "running"):
                m["steps"][_sname] = "failed"
        _log(m, f"pipeline echoue: {e}", "error")
        print(f"[HUEFORGE:{m['id']}] traceback:\n{traceback.format_exc()}")
    finally:
        _save_cache(_hueforge_missions)
    return m


async def run_hueforge_batch(prompts: list[str], params: dict | None = None) -> list[dict]:
    """Automation : enchaîne une mission par prompt (séquentiel → pas de contention GPU).

    Renvoie un résumé léger par mission. Utilisé par le job planifié et l'endpoint
    ``POST /v1/hueforge/batch``.
    """
    results: list[dict] = []
    for prompt in prompts:
        prompt = (prompt or "").strip()
        if not prompt:
            continue
        m = new_mission(prompt, params)
        await run_hueforge_pipeline(m["id"])
        results.append({
            "id": m["id"],
            "prompt": prompt,
            "status": m["status"],
            "final": m.get("files", {}).get("final"),
            "palette": m.get("palette"),
            "error": m.get("error"),
        })
    print(f"[HUEFORGE] batch terminé: {len(results)} mission(s)")
    return results

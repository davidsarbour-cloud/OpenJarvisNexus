"""HueForge — APIRouter FastAPI.

Endpoints :
  POST /v1/hueforge/mission        - lancer une préparation (prompt OU image)
  GET  /v1/hueforge/mission/{id}   - statut + progression + palette
  GET  /v1/hueforge/missions       - liste des missions
  GET  /v1/hueforge/jobs           - compteurs live (carte Command Center)
  GET  /v1/hueforge/image/{id}     - PNG final (inline, prévisualisation)
  GET  /v1/hueforge/download/{id}  - PNG final (téléchargement)
  GET  /v1/hueforge/report/{id}    - rapport JSON (palette, filaments estimés)
  POST /v1/hueforge/batch          - automation : N prompts → N missions
  GET  /v1/hueforge/health         - dispo ComfyUI / rembg / dossier prêt
  -- tier 2 --
  GET  /v1/hueforge/variants/{id}            - variantes + score + gagnant
  GET  /v1/hueforge/variant/{id}/{vid}       - PNG d'une variante (?preview=1 = aperçu Etsy)
  -- tier 3 --
  GET  /v1/hueforge/print-plan/{id}          - filaments + couches + simu + params
  GET  /v1/hueforge/render-sim/{id}          - PNG de la simulation HueForge
  GET  /v1/hueforge/filaments                - inventaire filaments (live, éditable)
  PUT  /v1/hueforge/filaments                - met à jour l'inventaire filaments
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from hueforge import filament_lab
from hueforge.hueforge_pipeline import (
    HUEFORGE_READY,
    _hueforge_missions,
    get_mission,
    new_mission,
    open_in_hueforge,
    run_hueforge_batch,
    run_hueforge_pipeline,
)

router = APIRouter(prefix="/v1/hueforge", tags=["hueforge"])


class HueForgeRequest(BaseModel):
    # model_height_mm est un vrai champ métier — on lève la réservation Pydantic "model_".
    model_config = {"protected_namespaces": ()}
    prompt: str = ""
    # Image-to-prep : data URI base64 (data:image/...;base64,xxxx) ou base64 brut.
    # Si fourni, la génération ComfyUI est ignorée et l'image est ingérée telle quelle.
    image: str | None = None
    size: int = 1024
    contrast: float = 1.35
    remove_bg: bool = True
    flatten_bg: str | None = None  # None = PNG transparent ; "#ffffff" = aplatit
    seed: int = 0
    palette_colors: int = 6
    # Tier 2 — variantes + sélection auto + aperçu Etsy
    tier2: bool = False
    variants_count: int = 3
    variant_strategy: str = "contrast_range"  # contrast_range | seed_variation | comfyui_prompt_tweak
    # Tier 3 — filaments + couches + simulation + paramètres d'impression
    tier3: bool = False
    layer_height: float = 0.08
    model_height_mm: float = 3.0
    # Taille physique cible de la plaque (mm). Si None, tentative d'extraction depuis
    # le prompt (ex: "119x47"). Recadre l'image au bon ratio + suit jusqu'à HueForge.
    target_w_mm: float | None = None
    target_h_mm: float | None = None
    # Ouvre le PNG final automatiquement (HueForge si trouvé, sinon Explorateur).
    auto_open: bool = False


class HueForgeBatchRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    prompts: list[str]
    size: int = 1024
    contrast: float = 1.35
    remove_bg: bool = True
    flatten_bg: str | None = None
    palette_colors: int = 6
    tier2: bool = False
    variants_count: int = 3
    variant_strategy: str = "contrast_range"
    tier3: bool = False
    layer_height: float = 0.08
    model_height_mm: float = 3.0


class FilamentInventoryRequest(BaseModel):
    slots: int = 4
    filaments: list[dict]


_DIMS_RE = re.compile(r"(\d{1,4})\s*[x×]\s*(\d{1,4})\s*(mm)?", re.I)
# Plage plausible d'une plaque HueForge (mm) : rejette "4x4", résolutions, valeurs absurdes.
_PLATE_MIN_MM, _PLATE_MAX_MM = 5.0, 1000.0


def _parse_dims_mm(text: str) -> tuple[float, float] | None:
    """Extrait une taille de plaque 'LxH' (ex: '119x47') d'un texte libre, en mm.

    Choisit le MEILLEUR candidat (et non le premier) : on garde ceux dans la plage
    plaque plausible, on privilégie ceux suffixés 'mm', puis la plus grande surface.
    Ça évite que '4x4 truck 119x47' renvoie 4x4.
    """
    cands = []
    for m in _DIMS_RE.finditer(text or ""):
        w, h = float(m.group(1)), float(m.group(2))
        if _PLATE_MIN_MM <= w <= _PLATE_MAX_MM and _PLATE_MIN_MM <= h <= _PLATE_MAX_MM:
            cands.append((bool(m.group(3)), w * h, w, h))
    if not cands:
        return None
    cands.sort(key=lambda c: (c[0], c[1]), reverse=True)  # mm-suffixé d'abord, puis surface
    return (cands[0][2], cands[0][3])


def _strip_dims(text: str, dims: tuple[float, float]) -> str:
    """Retire SEULEMENT le token de la dimension choisie du prompt (pas tout 'NxM')."""
    w, h = int(dims[0]), int(dims[1])
    pat = re.compile(rf"\b0*{w}\s*[x×]\s*0*{h}\s*(mm)?\b", re.I)
    return pat.sub(" ", text or "", count=1).strip()


def _params(req: HueForgeRequest) -> dict:
    return {
        "size": req.size,
        "contrast": req.contrast,
        "remove_bg": req.remove_bg,
        "flatten_bg": req.flatten_bg,
        "seed": req.seed,
        "palette_colors": req.palette_colors,
        "tier2": req.tier2,
        "variants_count": req.variants_count,
        "variant_strategy": req.variant_strategy,
        "tier3": req.tier3,
        "layer_height": req.layer_height,
        "model_height_mm": req.model_height_mm,
        "target_w_mm": req.target_w_mm,
        "target_h_mm": req.target_h_mm,
        "auto_open": req.auto_open,
    }


@router.post("/mission")
async def create_hueforge_mission(req: HueForgeRequest, background_tasks: BackgroundTasks):
    """Lance une préparation HueForge. Deux modes : texte (ComfyUI) ou image fournie."""
    prompt = req.prompt.strip()
    if not prompt and not req.image:
        raise HTTPException(status_code=400, detail="prompt ou image requis")

    params = _params(req)
    # Taille de plaque : explicite, sinon extraite du prompt (ex: "119x47" -> mm).
    if not (req.target_w_mm and req.target_h_mm):
        dims = _parse_dims_mm(prompt)
        if dims:
            params["target_w_mm"], params["target_h_mm"] = dims
            prompt = _strip_dims(prompt, dims)  # on retire le token du prompt FLUX

    image_path = None
    if req.image:
        try:
            import base64
            import io

            from PIL import Image

            from hueforge.hueforge_pipeline import HUEFORGE_OUTPUT

            b64 = req.image.split("base64,", 1)[-1]
            raw = base64.b64decode(b64)
            # mid provisoire pour nommer le fichier d'entrée avant la création mission
            tmp_name = f"input_{abs(hash(req.image)) & 0xFFFFFF:06x}.png"
            img_path = HUEFORGE_OUTPUT / tmp_name
            Image.open(io.BytesIO(raw)).save(str(img_path), "PNG")
            image_path = str(img_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"image illisible: {e}") from e

    _before = set(_hueforge_missions.keys())
    m = new_mission(prompt, params, image_path=image_path)
    if m["id"] in _before:
        # Mission identique déjà en cours : on renvoie l'état existant (dédup).
        return {
            "mission_id": m["id"],
            "status": m.get("status", "running"),
            "mode": m["params"].get("source"),
            "message": f"HUEFORGE - Mission {m['id']} déjà en cours (dedup)",
            "poll_url": f"/v1/hueforge/mission/{m['id']}",
            "deduplicated": True,
        }

    background_tasks.add_task(run_hueforge_pipeline, m["id"])
    return {
        "mission_id": m["id"],
        "status": "running",
        "mode": m["params"].get("source"),
        "message": f"HUEFORGE - Mission {m['id']} démarrée",
        "poll_url": f"/v1/hueforge/mission/{m['id']}",
    }


@router.get("/mission/{mission_id}")
async def get_hueforge_mission(mission_id: str):
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} introuvable")
    steps_done = sum(1 for s in m["steps"].values() if s == "done")
    progress = round((steps_done / len(m["steps"])) * 100)
    return {
        "id": m["id"],
        "status": m["status"],
        "current_step": m["current_step"],
        "progress_pct": progress,
        "steps": m["steps"],
        "params": m.get("params", {}),
        "files": m.get("files", {}),
        "palette": m.get("palette"),
        "report": m.get("report"),
        "logs": m["logs"][-20:],
        "created_at": m["created_at"],
        "completed_at": m.get("completed_at"),
        "error": m.get("error"),
    }


@router.get("/missions")
async def list_hueforge_missions():
    return {
        "total": len(_hueforge_missions),
        "missions": [
            {
                "id": mid,
                "status": m["status"],
                "prompt": m["prompt"][:60],
                "created_at": m["created_at"],
                "colors": len(m["palette"]) if m.get("palette") else None,
            }
            for mid, m in _hueforge_missions.items()
        ],
    }


@router.get("/jobs")
async def hueforge_jobs():
    """Compteurs live pour la carte Command Center (snapshot/hueforge)."""
    jobs = [
        {
            "id": mid,
            "status": m["status"],
            "prompt": m["prompt"][:40],
            "tier2": bool(m.get("params", {}).get("tier2")),
            "tier3": bool(m.get("params", {}).get("tier3")),
        }
        for mid, m in _hueforge_missions.items()
    ]
    return {
        "total": len(jobs),
        "running": sum(1 for j in jobs if j["status"] == "running"),
        "done": sum(1 for j in jobs if j["status"] == "completed"),
        "failed": sum(1 for j in jobs if j["status"] == "failed"),
        "variants": sum(1 for j in jobs if j["tier2"]),
        "print": sum(1 for j in jobs if j["tier3"]),
        "jobs": jobs,
    }


def _final_or_404(mission_id: str) -> Path:
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if m["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Mission en cours ({m['status']})")
    final = m.get("files", {}).get("final")
    if not final or not Path(final).exists():
        raise HTTPException(status_code=404, detail="PNG final non disponible")
    return Path(final)


@router.get("/image/{mission_id}")
async def get_hueforge_image(mission_id: str):
    """PNG final inline (prévisualisation navigateur)."""
    path = _final_or_404(mission_id)
    return FileResponse(str(path), media_type="image/png")


@router.get("/download/{mission_id}")
async def download_hueforge_image(mission_id: str):
    """PNG final en téléchargement (prêt pour HueForge)."""
    path = _final_or_404(mission_id)
    return FileResponse(str(path), media_type="image/png", filename=path.name)


@router.post("/open/{mission_id}")
async def open_hueforge_mission(mission_id: str):
    """Ouvre le PNG final (app HueForge si trouvée, sinon Explorateur fichier sélectionné)."""
    path = _final_or_404(mission_id)
    res = await asyncio.to_thread(open_in_hueforge, str(path))
    if not res.get("opened"):
        raise HTTPException(status_code=503,
                            detail=res.get("error", "ouverture impossible (definis HUEFORGE_PATH)"))
    return {"status": "opened", "file": path.name, **res}


@router.get("/report/{mission_id}")
async def get_hueforge_report(mission_id: str):
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if m.get("report"):
        return JSONResponse(m["report"])
    raise HTTPException(status_code=404, detail="Rapport non encore disponible")


@router.post("/batch")
async def hueforge_batch(req: HueForgeBatchRequest, background_tasks: BackgroundTasks):
    """Automation manuelle : lance N missions (une par prompt) en arrière-plan."""
    prompts = [p.strip() for p in req.prompts if p and p.strip()]
    if not prompts:
        raise HTTPException(status_code=400, detail="aucun prompt fourni")
    params = {
        "size": req.size,
        "contrast": req.contrast,
        "remove_bg": req.remove_bg,
        "flatten_bg": req.flatten_bg,
        "palette_colors": req.palette_colors,
        "tier2": req.tier2,
        "variants_count": req.variants_count,
        "variant_strategy": req.variant_strategy,
        "tier3": req.tier3,
        "layer_height": req.layer_height,
        "model_height_mm": req.model_height_mm,
    }
    background_tasks.add_task(run_hueforge_batch, prompts, params)
    return {
        "status": "started",
        "count": len(prompts),
        "message": f"HUEFORGE - batch de {len(prompts)} mission(s) lancé",
    }


@router.get("/health")
async def hueforge_health():
    """Dispo ComfyUI (génération) + rembg (détourage) + dossier « Prêt pour HueForge »."""
    from services import comfyui_images

    comfyui = await asyncio.to_thread(comfyui_images.is_available)
    try:
        import rembg  # noqa: F401
        rembg_ok = True
    except Exception:
        rembg_ok = False
    inv = await asyncio.to_thread(filament_lab.load_inventory)
    return {
        "comfyui": comfyui,
        "rembg": rembg_ok,
        "ready_dir": str(HUEFORGE_READY),
        "ready_dir_exists": HUEFORGE_READY.exists(),
        "missions_cached": len(_hueforge_missions),
        "filaments_owned": len(inv.get("filaments", [])),
    }


# ── TIER 2 : variantes ────────────────────────────────────────────────────────
@router.get("/variants/{mission_id}")
async def list_hueforge_variants(mission_id: str):
    """Variantes générées + scores + variante gagnante (mission tier2)."""
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if not m.get("params", {}).get("tier2"):
        return {"tier2": False, "message": "mission tier1 - pas de variantes", "variants": []}
    variants = []
    for vr in m.get("variants", []):
        variants.append({
            "id": vr["id"],
            "label": vr.get("label"),
            "strategy": vr.get("strategy"),
            "contrast": vr.get("contrast"),
            "score": vr.get("score"),
            "components": vr.get("components"),
            "palette": vr.get("palette"),
            "bg_removed": vr.get("bg_removed"),
            "has_file": bool(vr.get("file")) and Path(vr["file"]).exists(),
        })
    return {
        "tier2": True,
        "status": m["status"],
        "best_variant_id": m.get("best_variant_id"),
        "selection": m.get("variant_selection"),
        "variants": variants,
    }


@router.get("/variant/{mission_id}/{variant_id}")
async def get_hueforge_variant(mission_id: str, variant_id: str, preview: int = 0):
    """PNG d'une variante. ``?preview=1`` renvoie l'aperçu Etsy de la variante."""
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    vr = next((v for v in m.get("variants", []) if v["id"].upper() == variant_id.upper()), None)
    if not vr:
        raise HTTPException(status_code=404, detail="Variante introuvable")
    if preview:
        pth = (m.get("files", {}).get("etsy_previews") or {}).get(vr["id"])
        if not pth or not Path(pth).exists():
            raise HTTPException(status_code=404, detail="Aperçu Etsy non disponible")
        return FileResponse(pth, media_type="image/png")
    if not vr.get("file") or not Path(vr["file"]).exists():
        raise HTTPException(status_code=404, detail="PNG de variante non disponible")
    return FileResponse(vr["file"], media_type="image/png")


# ── TIER 3 : plan d'impression + simulation + inventaire filaments ────────────
@router.get("/print-plan/{mission_id}")
async def get_hueforge_print_plan(mission_id: str):
    """Analyse filaments + changements de couches + simulation + paramètres (tier3)."""
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if not m.get("params", {}).get("tier3"):
        return {"tier3": False, "message": "mission sans tier3 - pas de plan d'impression"}
    return {
        "tier3": True,
        "status": m["status"],
        "filament_analysis": m.get("filament_analysis"),
        "layer_changes": m.get("layer_changes"),
        "hueforge_render": m.get("hueforge_render"),
        "print_params": m.get("print_params"),
    }


@router.get("/render-sim/{mission_id}")
async def get_hueforge_render_sim(mission_id: str):
    """PNG de la simulation de rendu HueForge (tier3)."""
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    pth = m.get("files", {}).get("render_sim")
    if not pth or not Path(pth).exists():
        raise HTTPException(status_code=404, detail="Simulation non disponible")
    return FileResponse(pth, media_type="image/png")


@router.get("/filaments")
async def get_hueforge_filaments():
    """Inventaire filaments live (éditable). Seedé depuis les défauts au 1er appel."""
    return await asyncio.to_thread(filament_lab.load_inventory)


@router.put("/filaments")
async def put_hueforge_filaments(req: FilamentInventoryRequest):
    """Remplace l'inventaire filaments (valide hex + borne ams_slot/td_mm/densité)."""
    return await asyncio.to_thread(filament_lab.save_inventory, req.model_dump())

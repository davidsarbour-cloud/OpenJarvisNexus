"""
The Forge Room - FastAPI Router
Endpoints:
  POST /v1/forge/mission          - lancer une mission de fabrication
  GET  /v1/forge/mission/{id}     - statut + progression
  GET  /v1/forge/download/{id}    - telecharger le STL final
  GET  /v1/forge/report/{id}      - rapport de fabrication JSON
  GET  /v1/forge/missions         - liste toutes les missions
  POST /v1/forge/validate         - valider un STL uploade
"""
from __future__ import annotations

from pathlib import Path

import trimesh
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from forge_room.fabrication_pipeline import (
    FORGE_OUTPUT,
    _forge_missions,
    get_mission,
    new_mission,
    run_forge_pipeline,
)

router = APIRouter(prefix="/v1/forge", tags=["forge"])


class ForgeMissionRequest(BaseModel):
    prompt: str = ""
    engine: str = "auto"
    target_size_mm: float = 150.0
    auto_repair: bool = True
    auto_orient: bool = True
    auto_bambu: bool = False
    # Image-to-3D : data URI base64 (data:image/...;base64,xxxx) ou base64 brut.
    # Si fourni, le pipeline génère via Meshy image-to-3D au lieu de text-to-3D.
    image: str | None = None


class ForgeValidateRequest(BaseModel):
    stl_path: str


class EngineeringPassRequest(BaseModel):
    """Cut a sculpted STL into print-ready pieces (Blender headless).

    Example specs:
        { "plate_mm": [256, 256],
          "cuts": [{"axis": "Z", "value_mm": 80}, {"axis": "Z", "value_mm": 160}],
          "hollow": {"enabled": true, "wall_mm": 2.0} }
    """
    input_stl: str
    specs: dict
    timeout: int = 240


@router.post("/mission")
async def create_forge_mission(req: ForgeMissionRequest, background_tasks: BackgroundTasks):
    """Lance une mission de fabrication The Forge Room.

    Deux modes : text-to-3D (prompt) OU image-to-3D (req.image). Au moins l'un
    des deux est requis. Si une image est fournie, le pipeline la priorise
    (Meshy image-to-3D), avec fallback texte si l'image échoue.
    """
    prompt = req.prompt.strip()
    if not prompt and not req.image:
        raise HTTPException(status_code=400, detail="prompt ou image requis")

    # Image présente : tag de hash dans la clé d'anti-duplication (texte+image
    # inclus) pour que deux images DIFFÉRENTES avec le même texte ne fusionnent
    # jamais, et qu'une re-soumission identique soit bien dédupliquée.
    if req.image:
        import hashlib
        tag = hashlib.sha1(req.image.encode("utf-8", "ignore")).hexdigest()[:8]  # noqa: S324 - tag non-crypto, dédup only
        prompt = f"{prompt} [img:{tag}]" if prompt else f"image-to-3D {tag}"

    # Dédup : new_mission renvoie une mission EXISTANTE (running, <5min, même clé)
    # au lieu d'en créer une. Un id réutilisé était déjà présent dans le registre.
    _before_ids = set(_forge_missions.keys())
    m = new_mission(prompt, auto_bambu=req.auto_bambu)
    if m["id"] in _before_ids:
        # Mission identique déjà en cours : ne PAS écraser l'image ni relancer un
        # 2e pipeline sur le même mission_id — on renvoie l'état existant.
        return {
            "mission_id": m["id"],
            "status": m.get("status", "running"),
            "mode": "image-to-3D" if m.get("image_path") else "text-to-3D",
            "message": f"THE FORGE ROOM - Mission {m['id']} deja en cours (dedup)",
            "poll_url": f"/v1/forge/mission/{m['id']}",
            "deduplicated": True,
        }

    # ── Image-to-3D : décode le base64 + normalise en PNG sur disque ──
    if req.image:
        try:
            import base64
            import io

            from PIL import Image

            b64 = req.image.split("base64,", 1)[-1]
            raw = base64.b64decode(b64)
            img_path = FORGE_OUTPUT / f"{m['id']}_input.png"
            Image.open(io.BytesIO(raw)).convert("RGBA").save(str(img_path), "PNG")
            m["image_path"] = str(img_path)
            m["files"]["input_image"] = str(img_path)
        except Exception as e:
            # Image illisible → on log et on retombe sur le text-to-3D (prompt).
            m["logs"].append({
                "ts": "", "level": "warning",
                "msg": f"Image illisible ({e}) - bascule text-to-3D",
            })

    background_tasks.add_task(run_forge_pipeline, m["id"])

    return {
        "mission_id": m["id"],
        "status": "running",
        "mode": "image-to-3D" if m.get("image_path") else "text-to-3D",
        "message": f"THE FORGE ROOM - Mission {m['id']} demarree",
        "poll_url": f"/v1/forge/mission/{m['id']}",
    }


@router.get("/mission/{mission_id}")
async def get_forge_mission(mission_id: str):
    """Retourne le statut complet d'une mission Forge."""
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} introuvable")

    steps_done  = sum(1 for s in m["steps"].values() if s == "done")
    steps_total = len(m["steps"])
    progress    = round((steps_done / steps_total) * 100)

    return {
        "id":            m["id"],
        "status":        m["status"],
        "current_step":  m["current_step"],
        "progress_pct":  progress,
        "steps":         m["steps"],
        "plan":          m.get("plan", {}),
        "files":         m.get("files", {}),
        "report":        m.get("report"),
        "logs":          m["logs"][-20:],
        "created_at":    m["created_at"],
        "completed_at":  m.get("completed_at"),
        "error":         m.get("error"),
    }


@router.get("/download/{mission_id}")
async def download_forge_stl(mission_id: str):
    """Telecharge le STL final (Bambu-ready)."""
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if m["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Mission en cours ({m['status']})")

    stl_path = m.get("files", {}).get("final_stl")
    if not stl_path or not Path(stl_path).exists():
        raise HTTPException(status_code=404, detail="STL final non disponible")

    return FileResponse(
        stl_path,
        media_type="application/octet-stream",
        filename=f"forge_{mission_id.upper()}.stl",
    )


@router.post("/bambu/{mission_id}")
async def forge_bambu_handoff(mission_id: str):
    """Lance Bambu Studio avec le STL final de la mission Forge."""
    import os
    import subprocess
    from pathlib import Path as _P

    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if m["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Mission non completee ({m['status']})")

    stl_path = m.get("files", {}).get("final_stl")
    if not stl_path or not _P(stl_path).exists():
        raise HTTPException(status_code=404, detail="STL final non disponible")

    bambu_path = os.getenv("BAMBU_STUDIO_PATH", r"C:\Program Files\Bambu Studio\bambu-studio.exe")
    if not _P(bambu_path).exists():
        raise HTTPException(status_code=503, detail=f"Bambu Studio introuvable: {bambu_path}")

    try:
        subprocess.Popen([bambu_path, stl_path], shell=False)
        return {"status": "launched", "file": _P(stl_path).name, "bambu": bambu_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lancement Bambu echoue: {e}") from e


@router.get("/report/{mission_id}")
async def get_forge_report(mission_id: str):
    """Retourne le rapport de fabrication manufacturing_report.json."""
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")

    report_path = m.get("files", {}).get("report")
    if report_path and Path(report_path).exists():
        import json
        return JSONResponse(json.loads(Path(report_path).read_text(encoding="utf-8")))

    if m.get("report"):
        return JSONResponse(m["report"])

    raise HTTPException(status_code=404, detail="Rapport non encore disponible")


@router.get("/missions")
async def list_forge_missions():
    """Liste toutes les missions Forge avec leur statut."""
    return {
        "total": len(_forge_missions),
        "missions": [
            {
                "id":          mid,
                "status":      m["status"],
                "prompt":      m["prompt"][:60],
                "created_at":  m["created_at"],
                "score":       m.get("report", {}).get("printability_score") if m.get("report") else None,
            }
            for mid, m in _forge_missions.items()
        ],
    }


@router.post("/engineering-pass")
async def forge_engineering_pass(req: EngineeringPassRequest):
    """Sculpt → multi-piece print-ready (Blender headless + per-piece validation).
    See backend/forge_room/engineering_pass.py + the brain playbook
    03_Projects/STL/sculpt-3d-playbook.md §4."""
    from datetime import datetime as _dt

    from forge_room.engineering_pass import report_to_dict, run_engineering_pass

    in_stl = Path(req.input_stl)
    if not in_stl.exists():
        raise HTTPException(status_code=400, detail=f"input_stl not found: {in_stl}")
    out_dir = FORGE_OUTPUT / f"engpass_{in_stl.stem}_{_dt.now():%Y%m%d_%H%M%S}"
    return report_to_dict(run_engineering_pass(in_stl, req.specs, out_dir, req.timeout))


@router.post("/validate")
async def validate_stl_upload(file: UploadFile = File(...)):
    """Valide un STL uploade. Retourne le rapport sans lancer de pipeline."""
    from forge_room.mesh_validator import validate_mesh

    content = await file.read()
    if len(content) < 100:
        raise HTTPException(status_code=400, detail="Fichier STL invalide")

    # Anti-path-traversal : basename uniquement + caracteres safe
    raw_name = Path(file.filename or "upload.stl").name
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in raw_name)[:80]
    if not safe_name.lower().endswith(".stl"):
        safe_name += ".stl"
    tmp = FORGE_OUTPUT / f"validate_{safe_name}"
    tmp.write_bytes(content)

    try:
        mesh    = trimesh.load(str(tmp), force="mesh")
        report  = validate_mesh(mesh, check_thickness=True, check_supports=True)

        return {
            "filename":           safe_name,
            "printability_score": report.printability_score,
            "bambu_ready":        report.passed,
            "face_count":         len(mesh.faces),
            "vertex_count":       len(mesh.vertices),
            "manifold":           {
                "watertight":     report.manifold.is_watertight,
                "volume_cm3":     report.manifold.volume_cm3,
                "issues":         report.manifold.issues,
            },
            "floating": {
                "components":     report.floating.floating_components,
                "issues":         report.floating.issues,
            },
            "wall_thickness": {
                "min_mm":         report.wall.min_thickness_mm,
                "thin_pct":       report.wall.thin_face_pct,
                "issues":         report.wall.issues,
            },
            "supports": {
                "required":       report.supports.support_required,
                "overhang_pct":   report.supports.overhang_pct,
                "issues":         report.supports.issues,
            },
            "passed_checks":      report.passed_checks,
            "failed_checks":      report.failed_checks,
        }
    finally:
        tmp.unlink(missing_ok=True)

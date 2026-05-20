"""
The Forge Room — FastAPI Router
Endpoints:
  POST /v1/forge/mission          — lancer une mission de fabrication
  GET  /v1/forge/mission/{id}     — statut + progression
  GET  /v1/forge/download/{id}    — télécharger le STL final
  GET  /v1/forge/report/{id}      — rapport de fabrication JSON
  GET  /v1/forge/missions         — liste toutes les missions
  POST /v1/forge/validate         — valider un STL uploadé
"""
from __future__ import annotations
import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from forge_room.fabrication_pipeline import (
    new_mission, get_mission, run_forge_pipeline, _forge_missions,
    FORGE_OUTPUT, FORGE_REPORTS,
)
from forge_room.export_pipeline import run_export_pipeline
import trimesh

router = APIRouter(prefix="/v1/forge", tags=["forge"])


# ── Modèles Pydantic ─────────────────────────────────────

class ForgeMissionRequest(BaseModel):
    prompt: str
    engine: str = "auto"           # "blender" | "openscad" | "auto"
    target_size_mm: float = 150.0
    auto_repair: bool = True
    auto_orient: bool = True
    auto_bambu: bool = False        # ouvrir Bambu Studio automatiquement après export


class ForgeValidateRequest(BaseModel):
    stl_path: str                  # chemin local absolu


# ── Endpoints ────────────────────────────────────────────

@router.post("/mission")
async def create_forge_mission(req: ForgeMissionRequest, background_tasks: BackgroundTasks):
    """Lance une mission de fabrication The Forge Room."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt requis")

    m = new_mission(req.prompt.strip(), auto_bambu=req.auto_bambu)
    background_tasks.add_task(run_forge_pipeline, m["id"])

    return {
        "mission_id": m["id"],
        "status": "running",
        "message": f"⬡ THE FORGE ROOM — Mission {m['id']} démarrée",
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
        "logs":          m["logs"][-20:],    # derniers 20 logs
        "created_at":    m["created_at"],
        "completed_at":  m.get("completed_at"),
        "error":         m.get("error"),
    }


@router.get("/download/{mission_id}")
async def download_forge_stl(mission_id: str):
    """Télécharge le STL final (Bambu-ready)."""
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
    import os, subprocess
    from pathlib import Path

    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if m["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Mission non complétée ({m['status']})")

    stl_path = m.get("files", {}).get("final_stl")
    if not stl_path or not Path(stl_path).exists():
        raise HTTPException(status_code=404, detail="STL final non disponible")

    bambu_path = os.getenv("BAMBU_STUDIO_PATH", r"C:\Program Files\Bambu Studio\bambu-studio.exe")
    if not Path(bambu_path).exists():
        raise HTTPException(status_code=503, detail=f"Bambu Studio introuvable: {bambu_path}")

    try:
        subprocess.Popen([bambu_path, stl_path], shell=False)
        return {"status": "launched", "file": Path(stl_path).name, "bambu": bambu_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lancement Bambu échoué: {e}")


@router.get("/report/{mission_id}")
async def get_forge_report(mission_id: str):
    """Retourne le rapport de fabrication manufacturing_report.json."""
    m = get_mission(mission_id.upper())
    if not m:
        raise HTTPException(status_code=404, detail="Mission introuvable")

    report_path = m.get("files", {}).get("report")
    if report_path and Path(report_path).exists():
        import json
        return JSONResponse(json.loads(Path(report_path).read_text()))

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


@router.post("/validate")
async def validate_stl_upload(file: UploadFile = File(...)):
    """
    Valide un STL uploadé.
    Retourne le rapport de validation complet sans lancer de pipeline.
    """
    from forge_room.mesh_validator import validate_mesh
    from dataclasses import asdict

    content = await file.read()
    if len(content) < 100:
        raise HTTPException(status_code=400, detail="Fichier STL invalide")

    tmp = FORGE_OUTPUT / f"validate_{file.filename}"
    tmp.write_bytes(content)

    try:
        mesh    = trimesh.load(str(tmp), force="mesh")
        report  = validate_mesh(mesh, check_thickness=True, check_supports=True)

        return {
            "filename":          file.filename,
            "printability_score": report.printability_score,
            "bambu_ready":       report.passed,
            "face_count":        len(mesh.faces),
            "vertex_count":      len(mesh.vertices),
            "manifold":          {
                "watertight":    report.manifold.is_watertight,
                "volume_cm3":    report.manifold.volume_cm3,
                "issues":        report.manifold.issues,
            },
            "floating": {
                "components":    report.floating.floating_components,
                "issues":        report.floating.issues,
            },
            "wall_thickness": {
                "min_mm":        report.wall.min_thickness_mm,
                "thin_pct":      report.wall.thin_face_pct,
                "issues":        report.wall.issues,
            },
            "supports": {
                "required":      report.supports.support_required,
                "overhang_pct":  report.supports.overhang_pct,
                "issues":        report.supports.issues,
            },
            "passed_checks":     report.passed_checks,
            "failed_checks":     report.failed_checks,
        }
    finally:
        tmp.unlink(missing_ok=True)

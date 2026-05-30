"""IconForge HTTP API (Phase 1).

Endpoints:
  POST /v1/iconforge/pilot      — run the Minimal Black 30-icon pilot
  POST /v1/iconforge/pack       — run a custom brief
  GET  /v1/iconforge/packs      — list packs in storage
  GET  /v1/iconforge/download/{pack_id} — download the Theme.zip
  GET  /v1/iconforge/comfyui    — probe the ComfyUI server
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from iconforge.brief import PackBrief
from iconforge.catalog import minimal_black_pilot
from iconforge.config import SETTINGS
from iconforge.generators.comfyui_client import ComfyUIClient
from iconforge.pipeline import run_pack

router = APIRouter(prefix="/v1/iconforge", tags=["iconforge"])


def _result_payload(r) -> dict:
    return {
        "pack_id":   r.pack_id,
        "name":      r.name,
        "icons":     r.icon_count,
        "platforms": r.platforms,
        "zip_url":   f"/v1/iconforge/download/{r.pack_id}",
        "zip_path":  str(r.zip_path),
    }


@router.post("/pilot")
def run_pilot() -> dict:
    """Generate the Minimal Black 30-icon pilot — pure procedural, no GPU."""
    return _result_payload(run_pack(minimal_black_pilot()))


@router.post("/pack")
def run_custom_pack(brief: PackBrief) -> dict:
    """Generate a custom pack from a brief."""
    return _result_payload(run_pack(brief))


@router.get("/packs")
def list_packs() -> dict:
    out = []
    for p in sorted(SETTINGS.storage_dir.glob("*.zip")):
        out.append({"pack_id": p.stem, "size_kb": round(p.stat().st_size / 1024, 1)})
    return {"packs": out}


@router.get("/download/{pack_id}")
def download_pack(pack_id: str):
    z = SETTINGS.storage_dir / f"{pack_id}.zip"
    if not z.exists():
        raise HTTPException(status_code=404, detail="pack not found")
    return FileResponse(z, media_type="application/zip", filename=z.name)


@router.get("/comfyui")
async def comfyui_status() -> dict:
    """Probe — Phase 2 / artistic packs need this. Returns offline gracefully."""
    client = ComfyUIClient()
    return {"url": client.base_url, "available": await client.is_available()}

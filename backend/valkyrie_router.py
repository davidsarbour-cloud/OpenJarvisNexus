"""VALKYRIE — agent de génération d'images OpenAI (gpt-image-1).

Endpoints
  POST   /v1/valkyrie/generate      — génère 1..n images depuis un prompt
  GET    /v1/valkyrie/gallery       — liste les images générées (récentes d'abord)
  GET    /v1/valkyrie/health        — disponibilité (clé configurée ?)
  DELETE /v1/valkyrie/image/{name}  — supprime une image + son sidecar

Les images sont écrites dans backend/generated_images/ et servies en
statique via /generated_images (monté dans main.py).

L'appel OpenAI vit dans services/openai_images.py (service partagé, réutilisé
par auto_factory via ImageFactory) — ce router ne fait que valider, persister
les PNG et exposer la galerie. Pas de logique OpenAI dupliquée ici.
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone

import httpx
from app_state import _agents_status, _log_error_500, openai_available
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from services import openai_images, valkyrie_memory

router = APIRouter(tags=["valkyrie"])

# Dossier de sortie (créé au démarrage de l'import).
_IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "generated_images"))
os.makedirs(_IMAGES_DIR, exist_ok=True)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    size: str = "1024x1024"
    quality: str = "high"
    n: int = Field(1, ge=1, le=4)
    background: str | None = None  # transparent | opaque | auto
    enhance: bool = False          # append learned best modifiers (self-improvement)
    niche_type: str | None = None  # thumbnail | logo | poster | ... (picks the modifier pool)


def _write_image(raw: bytes, meta: dict) -> dict:
    """Écrit un PNG (bytes) + sidecar JSON, retourne l'entrée de galerie."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{stamp}_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(_IMAGES_DIR, name)
    with open(path, "wb") as f:
        f.write(raw)
    entry = {
        "name": name,
        "url": f"/generated_images/{name}",
        "size_bytes": len(raw),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **meta,
    }
    with open(path + ".json", "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)
    return entry


@router.get("/v1/valkyrie/health")
def valkyrie_health():
    return {
        "agent": "VALKYRIE",
        "available": openai_available(),
        "model": openai_images.MODEL,
        "status": _agents_status.get("VALKYRIE", "offline"),
    }


@router.post("/v1/valkyrie/generate")
async def valkyrie_generate(req: GenerateRequest):
    if not openai_available():
        raise HTTPException(503, "OPENAI_API_KEY manquant — VALKYRIE indisponible.")

    size = req.size if req.size in openai_images.VALID_SIZES else "1024x1024"
    quality = req.quality if req.quality in openai_images.VALID_QUALITIES else "high"

    # Self-improvement: optionally append the current best-learned modifiers.
    base_prompt = req.prompt
    prompt, mods = (valkyrie_memory.enhance(base_prompt, req.niche_type)
                    if req.enhance else (base_prompt, []))

    _agents_status["VALKYRIE"] = "active"
    t0 = time.monotonic()
    try:
        raws = await openai_images.generate(
            prompt, size=size, quality=quality, n=req.n, background=req.background,
        )
        meta = {"prompt": prompt, "base_prompt": base_prompt, "modifiers": mods,
                "niche_type": req.niche_type, "model": openai_images.MODEL,
                "size": size, "quality": quality}
        images = [_write_image(raw, meta) for raw in raws]
        # Record each generation so the kept/deleted signal can teach future runs.
        for img in images:
            valkyrie_memory.record_generation(
                image_name=img["name"], base_prompt=base_prompt, final_prompt=prompt,
                modifiers=mods, niche_type=req.niche_type, backend="openai")
        elapsed = round(time.monotonic() - t0, 2)
        cost = openai_images.estimate_cost(size, quality, len(images))
        print(f"[VALKYRIE] {len(images)} image(s) · {size} {quality} · {elapsed}s · ~${cost}")
        return {
            "ok": True,
            "images": images,
            "count": len(images),
            "elapsed_s": elapsed,
            "estimated_cost_usd": cost,
        }
    except openai_images.OpenAIImageError as exc:
        # Remonte le message OpenAI tel quel (ex: org non vérifiée → 403).
        raise HTTPException(502, str(exc))
    except httpx.TimeoutException:
        raise HTTPException(504, "OpenAI timeout (>180s) — réessaie ou baisse la qualité.")
    except Exception as exc:
        _log_error_500("/v1/valkyrie/generate", exc)
        raise HTTPException(500, f"VALKYRIE error: {type(exc).__name__}: {exc}")
    finally:
        _agents_status["VALKYRIE"] = "idle" if openai_available() else "offline"


@router.get("/v1/valkyrie/gallery")
def valkyrie_gallery(limit: int = 60):
    """Liste les images générées, plus récentes d'abord."""
    if not os.path.isdir(_IMAGES_DIR):
        return {"images": [], "count": 0}
    pngs = [f for f in os.listdir(_IMAGES_DIR) if f.lower().endswith(".png")]
    pngs.sort(key=lambda f: os.path.getmtime(os.path.join(_IMAGES_DIR, f)), reverse=True)
    out: list[dict] = []
    for name in pngs[: max(1, limit)]:
        path = os.path.join(_IMAGES_DIR, name)
        entry: dict = {"name": name, "url": f"/generated_images/{name}"}
        sidecar = path + ".json"
        if os.path.isfile(sidecar):
            try:
                with open(sidecar, encoding="utf-8") as f:
                    entry.update(json.load(f))
            except Exception:
                pass
        else:
            entry["size_bytes"] = os.path.getsize(path)
            entry["created_at"] = datetime.fromtimestamp(
                os.path.getmtime(path), tz=timezone.utc,
            ).isoformat(timespec="seconds")
        out.append(entry)
    return {"images": out, "count": len(out)}


@router.delete("/v1/valkyrie/image/{name}")
def valkyrie_delete(name: str):
    """Supprime une image générée + son sidecar (protégé contre path traversal)."""
    safe = os.path.basename(name)
    if not safe.lower().endswith(".png"):
        raise HTTPException(400, "Nom invalide.")
    path = os.path.join(_IMAGES_DIR, safe)
    if not os.path.isfile(path):
        raise HTTPException(404, "Introuvable.")
    os.remove(path)
    if os.path.isfile(path + ".json"):
        os.remove(path + ".json")
    # Implicit negative signal: a deleted image marks its modifiers as "bad".
    valkyrie_memory.record_feedback(safe, kept=False)
    return {"ok": True, "deleted": safe}


@router.get("/v1/valkyrie/memory")
def valkyrie_memory_stats():
    """Self-improvement stats: total generations, keep-rate, learned top modifiers."""
    return {"agent": "VALKYRIE", **valkyrie_memory.stats()}

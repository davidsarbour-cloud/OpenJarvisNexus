"""
Commerce Router — FastAPI endpoints pour le pipeline de commerce autonome.

POST /v1/commerce/pipeline          — créer et lancer un pipeline
GET  /v1/commerce/pipeline/{id}     — statut d'un pipeline
GET  /v1/commerce/pipelines         — liste de tous les pipelines
GET  /v1/commerce/approval/pending  — produits en attente d'approbation
POST /v1/commerce/approval/{id}/approve — approuver un produit
POST /v1/commerce/approval/{id}/reject  — rejeter un produit
GET  /v1/commerce/analytics         — statistiques globales
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from commerce.approval_queue import (
    approve_product,
    get_pending_approvals,
    reject_product,
)
from commerce.pipeline import (
    get_pipeline,
    list_pipelines,
    new_pipeline,
    run_commerce_pipeline,
)

router = APIRouter(prefix="/v1/commerce", tags=["Commerce"])


# ── Modèles Pydantic ───────────────────────────────────────────────────────────

class PipelineCreateRequest(BaseModel):
    idea: str


class RejectRequest(BaseModel):
    reason: str = ""


class ApproveRequest(BaseModel):
    approved_by: str = "human"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/pipeline", summary="Créer et lancer un pipeline produit")
async def create_pipeline(body: PipelineCreateRequest, background_tasks: BackgroundTasks):
    """
    Lance le pipeline complet :
    idea → concept (ULTRON) → STL (Forge) → metadata → approval queue.
    Retourne immédiatement l'ID du pipeline ; l'exécution tourne en background.
    """
    if not body.idea.strip():
        raise HTTPException(status_code=400, detail="Le champ 'idea' ne peut pas être vide.")

    p = new_pipeline(body.idea.strip())
    background_tasks.add_task(run_commerce_pipeline, p.id)
    return {
        "ok": True,
        "pipeline_id": p.id,
        "status": p.status,
        "message": f"Pipeline {p.id} lancé en arrière-plan.",
    }


@router.get("/pipeline/{pipeline_id}", summary="Statut d'un pipeline")
async def pipeline_status(pipeline_id: str):
    """Retourne l'état complet d'un pipeline (logs inclus)."""
    p = get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' introuvable.")
    return asdict(p)


@router.get("/pipelines", summary="Liste de tous les pipelines")
async def list_all_pipelines():
    """Liste tous les pipelines triés par date de création (plus récent en premier)."""
    return {"pipelines": list_pipelines(), "count": len(list_pipelines())}


@router.get("/approval/pending", summary="Produits en attente d'approbation")
async def pending_approvals():
    """
    Retourne tous les produits en statut 'approval' non encore approuvés.
    Ces produits DOIVENT être approuvés manuellement avant publication.
    """
    pending = get_pending_approvals()
    return {"pending": pending, "count": len(pending)}


@router.post("/approval/{pipeline_id}/approve", summary="Approuver un produit")
async def approve(pipeline_id: str, body: ApproveRequest):
    """
    Approuve un produit pour publication.
    Le statut passe de 'approval' → 'publishing'.
    """
    result = approve_product(pipeline_id.upper(), approved_by=body.approved_by)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/approval/{pipeline_id}/reject", summary="Rejeter un produit")
async def reject(pipeline_id: str, body: RejectRequest):
    """
    Rejette un produit — il ne sera pas publié.
    Le statut passe à 'rejected'.
    """
    result = reject_product(pipeline_id.upper(), reason=body.reason)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/analytics", summary="Statistiques globales du pipeline commerce")
async def analytics():
    """Statistiques agrégées sur tous les pipelines."""
    all_p = list_pipelines()

    status_counts: dict[str, int] = {}
    total_score   = 0
    scored_count  = 0
    total_price   = 0.0
    priced_count  = 0

    for p in all_p:
        st = p.get("status", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1

        score = p.get("printability_score", 0)
        if score:
            total_score  += score
            scored_count += 1

        price = p.get("price_usd", 0.0)
        if price:
            total_price  += price
            priced_count += 1

    return {
        "total_pipelines": len(all_p),
        "by_status": status_counts,
        "published_count": status_counts.get("published", 0),
        "pending_approval": status_counts.get("approval", 0),
        "avg_printability_score": round(total_score / scored_count, 1) if scored_count else 0,
        "avg_price_usd": round(total_price / priced_count, 2) if priced_count else 0,
    }


@router.get("/revenue", summary="Chiffre d'affaires Etsy (D3Dprintix)")
async def etsy_revenue(days: int = 30):
    """
    Revenus Etsy agrégés sur N jours (commandes payées) — carte $$$ du Command
    Center. Nécessite ETSY_ACCESS_TOKEN + ETSY_SHOP_ID dans .env.
    """
    from commerce.etsy_client import get_shop_revenue
    return await get_shop_revenue(days=days)

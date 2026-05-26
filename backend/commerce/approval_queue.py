"""Human Approval Queue — OBLIGATOIRE avant toute publication."""
from __future__ import annotations

from datetime import datetime

from commerce.pipeline import _log, _save_pipelines, get_pipeline


def get_pending_approvals() -> list[dict]:
    """Retourne tous les produits en attente d'approbation."""
    from dataclasses import asdict

    from commerce.pipeline import _pipelines
    return [
        asdict(p)
        for p in _pipelines.values()
        if p.status == "approval" and not p.approved
    ]


def approve_product(pipeline_id: str, approved_by: str = "human") -> dict:
    """Approuve un produit pour publication."""
    p = get_pipeline(pipeline_id)
    if not p:
        return {"ok": False, "error": "Pipeline introuvable"}
    if p.status != "approval":
        return {"ok": False, "error": f"Statut inattendu: {p.status}"}

    p.approved    = True
    p.approved_by = approved_by
    p.approved_at = datetime.now().isoformat()
    p.status      = "publishing"
    _log(p, f"APPROUVÉ par {approved_by} — publication en cours...", "success")
    _save_pipelines()
    return {"ok": True, "pipeline_id": p.id}


def reject_product(pipeline_id: str, reason: str = "") -> dict:
    """Rejette un produit (ne sera pas publié)."""
    p = get_pipeline(pipeline_id)
    if not p:
        return {"ok": False, "error": "Pipeline introuvable"}

    p.status           = "rejected"
    p.rejection_reason = reason
    _log(p, f"REJETÉ — raison: {reason or 'non spécifiée'}", "warning")
    _save_pipelines()
    return {"ok": True, "pipeline_id": p.id}

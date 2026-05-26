"""
Analytics — statistiques et tableaux de bord pour le Vault Hub.
"""
from __future__ import annotations

import json
from datetime import datetime

from vault.memory_manager import get_stats
from vault.vault_core import _BACKEND_DIR


def get_vault_analytics() -> dict:
    """Retourne toutes les analytics du Vault."""
    collection_counts = get_stats()
    total_memories    = sum(collection_counts.values())

    # Forge analytics depuis le cache
    forge_stats = _get_forge_stats()

    return {
        "total_memories":    total_memories,
        "collections":       collection_counts,
        "forge":             forge_stats,
        "generated_at":      datetime.now().isoformat(),
    }


def _get_forge_stats() -> dict:
    cache_file = _BACKEND_DIR / "forge_missions_cache.json"
    if not cache_file.exists():
        return {"total": 0, "completed": 0, "avg_score": 0}
    try:
        missions  = json.loads(cache_file.read_text(encoding="utf-8"))
        completed = [m for m in missions.values() if m.get("status") == "completed"]
        scores    = [m.get("report", {}).get("printability_score", 0)
                     for m in completed if m.get("report")]
        return {
            "total":     len(missions),
            "completed": len(completed),
            "failed":    len([m for m in missions.values() if m.get("status") == "failed"]),
            "avg_score": round(sum(scores) / max(len(scores), 1), 1),
            "bambu_ready": len([m for m in completed
                                if m.get("report", {}).get("bambu_ready")]),
        }
    except Exception:
        return {"total": 0, "completed": 0, "avg_score": 0}

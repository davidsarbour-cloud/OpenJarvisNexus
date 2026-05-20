"""
Forge Learning — sauvegarde les résultats STL pour améliorer les futures générations.
"""
from __future__ import annotations
from datetime import datetime
from vault.memory_manager import add_memory


async def save_forge_result(mission: dict, report: dict) -> None:
    """Sauvegarde le résultat d'une mission Forge dans Vault."""
    prompt = mission.get("prompt", "")
    score  = report.get("printability_score", 0)
    grade  = report.get("printability_grade", "?")
    engine = mission.get("files", {}).get("raw_stl", "unknown")
    orient = report.get("orientation_used", "?")
    wall   = report.get("wall_thickness_min_mm", 0)
    mat    = report.get("estimated_material_g", 0)

    text = (
        f"Forge mission: '{prompt}'\n"
        f"Score: {score}/100 Grade: {grade}\n"
        f"Orientation: {orient} | Wall: {wall}mm | Material: {mat}g\n"
        f"Bambu-ready: {report.get('bambu_ready', False)}\n"
        f"Repairs: {', '.join(report.get('repairs_applied', [])[:3])}"
    )

    await add_memory(
        "forge_reports",
        text,
        metadata={
            "mission_id": mission.get("id", "?"),
            "prompt":     prompt[:100],
            "score":      str(score),
            "grade":      grade,
            "bambu_ready": str(report.get("bambu_ready", False)),
        },
        pinned=(score >= 85),
    )


async def get_similar_forge(prompt: str) -> list[dict]:
    """Retrouve des missions Forge similaires pour optimiser la nouvelle."""
    from vault.memory_manager import search_memory
    return await search_memory("forge_reports", prompt, n_results=3)

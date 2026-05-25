"""Orchestration, smoke-test, ecosystem-health & cheat-code endpoints.

Extracted from main.py. Delegates to orchestrator, smoke_tests, health_score
and pipeline_runner; no shared app state.
"""

from fastapi import APIRouter, BackgroundTasks
from orchestrator import classify_intent, orchestrate
from pydantic import BaseModel
from smoke_tests import run_smoke_tests

router = APIRouter(tags=["orchestrate"])


# ─── moved verbatim from main.py ───
class OrchestrateRequest(BaseModel):
    text: str
    model: str = "claude-haiku-4-5-20251001"

@router.post("/v1/orchestrate")
async def orchestrate_request(req: OrchestrateRequest):
    """
    Endpoint d'orchestration JARVIS complet.
    Classifie l'intention, requête le Vault, route vers les agents appropriés.
    """
    try:
        orch = await orchestrate(req.text, req.model)
        return orch.to_dict()
    except Exception as e:
        return {"success": False, "error": str(e), "intent": "unknown", "agents": ["JARVIS"]}

@router.get("/v1/orchestrate/classify")
async def classify_only(text: str):
    """Classification rapide d'une requête sans exécution."""
    return classify_intent(text)

# ════════════════════════════════════════════════════════
# SMOKE TESTS
# ════════════════════════════════════════════════════════

@router.post("/v1/smoke-test")
async def run_smoke_test_endpoint(background_tasks: BackgroundTasks):
    """Lance tous les smoke tests et retourne le rapport."""
    report = await run_smoke_tests()
    # Log dans Vault si disponible
    try:
        from vault.memory_manager import add_memory
        summary = report["summary"]
        background_tasks.add_task(
            add_memory, "orchestration",
            f"Smoke test: {summary['passed']}/{summary['total']} passed, {report['health_pct']}% health",
            {"type": "smoke_test", "health_pct": str(report["health_pct"])},
        )
    except Exception:
        pass
    return report


@router.get("/v1/smoke-test/quick")
async def quick_smoke_test():
    """Smoke test rapide des systèmes critiques seulement (5 tests)."""
    from smoke_tests import (
        test_backend_health,
        test_forge_endpoint,
        test_jarvis_orchestration,
        test_ollama_connectivity,
        test_vault_read,
    )
    return await run_smoke_tests([
        test_backend_health,
        test_ollama_connectivity,
        test_vault_read,
        test_jarvis_orchestration,
        test_forge_endpoint,
    ])


# ════════════════════════════════════════════════════════
# ECOSYSTEM HEALTH SCORE
# ════════════════════════════════════════════════════════

from health_score import compute_health_score, get_forge_reliability


@router.get("/v1/ecosystem/health")
async def ecosystem_health():
    """Score de santé pondéré de l'écosystème Nexus9 (0-100)."""
    return await compute_health_score()

@router.get("/v1/ecosystem/health/quick")
async def ecosystem_health_quick():
    """Score rapide sans tests Claude (évite les coûts)."""
    return await compute_health_score(skip_claude=True)

@router.get("/v1/ecosystem/forge/reliability")
def forge_reliability():
    """Métriques de fiabilité du pipeline Forge Room (success_rate, avg_score, bambu_ready_pct)."""
    return get_forge_reliability()


# ════════════════════════════════════════════════════════
# CHEAT CODE ULTIME — Orbital Pipeline HUB
# ════════════════════════════════════════════════════════

@router.post("/v1/cheat-code")
async def cheat_code_run(voice: bool = True):
    """
    One-Click Cheat Code : sync agents, vérifie pipelines, met à jour le Vault, notifie David.
    Déclenché aussi par JARVIS: RUN CHEAT CODE dans le chat.
    """
    from pipeline_runner import run_cheat_code
    report = await run_cheat_code(voice=voice)
    return report



@router.get("/v1/cheat-code/status")
def cheat_code_status():
    """Dernier rapport Cheat Code exécuté."""
    from pipeline_runner import get_last_report
    report = get_last_report()
    if not report:
        return {"status": "never_run", "message": "Lance POST /v1/cheat-code pour démarrer."}
    return report

"""
Ecosystem Health Score — scoring pondéré 0-100 pour l'écosystème Nexus9.
Catégories: orchestration, memory, forge, voice, execution, connectivity.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

BACKEND_PORT  = int(os.getenv("BACKEND_PORT", 8000))
from config import OLLAMA_HOST
OPENHANDS_URL = os.getenv("OPENHANDS_URL", "http://localhost:3000")

# Base URL du backend (auto-référence)
_BACKEND_BASE = f"http://localhost:{BACKEND_PORT}"

# ── Poids pondérés — total = 100 ─────────────────────────
WEIGHTS = {
    "backend":      20,  # API FastAPI online
    "claude_api":   15,  # Claude Haiku accessible
    "ollama":       15,  # Ollama + modèles disponibles
    "vault":        15,  # ChromaDB + embeddings
    "forge_room":   10,  # Pipeline STL opérationnel
    "jarvis_files": 10,  # Workspace OneDrive accessible
    "voice":         5,  # TTS + Whisper
    "bruce":         5,  # OpenHands (optionnel)
    "memory_embed":  5,  # nomic-embed-text disponible
}
# Total = 100


def _grade(score: int) -> str:
    """Convertit un score 0-100 en lettre A-D."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _status(score: int) -> str:
    """Statut textuel selon le score."""
    if score >= 75:
        return "healthy"
    if score >= 50:
        return "degraded"
    return "critical"


async def _check(client, url: str, timeout: float = 3.0) -> tuple[bool, str]:
    """GET rapide — retourne (ok, detail)."""
    try:
        r = await client.get(url, timeout=timeout)
        return r.status_code < 500, f"HTTP {r.status_code}"
    except Exception as exc:
        return False, str(exc)[:80]


async def compute_health_score(skip_claude: bool = False) -> dict:
    """
    Calcule le score de santé pondéré de l'écosystème Nexus9.

    Args:
        skip_claude: Si True, saute le test Claude API (évite les coûts).

    Returns:
        dict avec score 0-100, grade, status, categories, timestamp, recommendations.
    """
    import httpx

    categories: dict[str, dict] = {}
    recommendations: list[str]  = []

    async with httpx.AsyncClient() as client:

        # ── backend (20 pts) ────────────────────────────────
        ok, detail = await _check(client, f"{_BACKEND_BASE}/health")
        score_backend = WEIGHTS["backend"] if ok else 0
        categories["backend"] = {
            "score":  score_backend,
            "max":    WEIGHTS["backend"],
            "status": "pass" if ok else "fail",
            "detail": detail,
        }
        if not ok:
            recommendations.append("Backend FastAPI inaccessible — relancer: 2_BACKEND.bat")

        # ── claude_api (15 pts) ─────────────────────────────
        if skip_claude:
            categories["claude_api"] = {
                "score":  WEIGHTS["claude_api"],
                "max":    WEIGHTS["claude_api"],
                "status": "skip",
                "detail": "Test Claude ignoré (mode quick)",
            }
            score_claude = WEIGHTS["claude_api"]
        else:
            ok, detail = await _check(client, f"{_BACKEND_BASE}/v1/models")
            # /v1/models liste les modèles disponibles; si Claude y est → API ok
            score_claude = WEIGHTS["claude_api"] if ok else 0
            categories["claude_api"] = {
                "score":  score_claude,
                "max":    WEIGHTS["claude_api"],
                "status": "pass" if ok else "fail",
                "detail": detail,
            }
            if not ok:
                recommendations.append(
                    "Claude API inaccessible — vérifier ANTHROPIC_API_KEY dans backend/.env"
                )

        # ── ollama (15 pts) ──────────────────────────────────
        try:
            r = await client.get(f"{OLLAMA_HOST}/api/tags", timeout=3.0)
            if r.status_code == 200:
                data   = r.json()
                models = data.get("models", [])
                ok_ol  = len(models) > 0
                detail = f"{len(models)} modèle(s) disponible(s)"
            else:
                ok_ol  = False
                detail = f"HTTP {r.status_code}"
        except Exception as exc:
            ok_ol  = False
            detail = str(exc)[:80]
            models = []

        score_ollama = WEIGHTS["ollama"] if ok_ol else 0
        categories["ollama"] = {
            "score":  score_ollama,
            "max":    WEIGHTS["ollama"],
            "status": "pass" if ok_ol else "fail",
            "detail": detail,
        }
        if not ok_ol:
            recommendations.append("Relancer Ollama: 1_OLLAMA.bat")

        # ── vault (15 pts) ───────────────────────────────────
        ok, detail = await _check(client, f"{_BACKEND_BASE}/v1/vault/stats")
        score_vault = WEIGHTS["vault"] if ok else 0
        categories["vault"] = {
            "score":  score_vault,
            "max":    WEIGHTS["vault"],
            "status": "pass" if ok else "fail",
            "detail": detail,
        }
        if not ok:
            recommendations.append(
                "Vault ChromaDB inaccessible — redémarrer le backend"
            )

        # ── forge_room (10 pts) ──────────────────────────────
        ok, detail = await _check(client, f"{_BACKEND_BASE}/v1/forge/missions")
        score_forge = WEIGHTS["forge_room"] if ok else 0
        categories["forge_room"] = {
            "score":  score_forge,
            "max":    WEIGHTS["forge_room"],
            "status": "pass" if ok else "fail",
            "detail": detail,
        }
        if not ok:
            recommendations.append(
                "Forge Room inaccessible — redémarrer le backend (forge_engine)"
            )

        # ── jarvis_files (10 pts) ────────────────────────────
        ok, detail = await _check(client, f"{_BACKEND_BASE}/v1/jarvis/files/list")
        score_files = WEIGHTS["jarvis_files"] if ok else 0
        categories["jarvis_files"] = {
            "score":  score_files,
            "max":    WEIGHTS["jarvis_files"],
            "status": "pass" if ok else "fail",
            "detail": detail,
        }
        if not ok:
            recommendations.append(
                "Workspace Jarvis Files inaccessible — vérifier OneDrive et jarvis_files.py"
            )

        # ── voice (5 pts) ────────────────────────────────────
        ok_voice = False
        detail_voice = "endpoint inaccessible"
        try:
            r = await client.get(f"{_BACKEND_BASE}/v1/speech/health", timeout=3.0)
            if r.status_code == 200:
                data     = r.json()
                ok_voice = data.get("available", False) is True
                detail_voice = "TTS disponible" if ok_voice else "TTS indisponible"
            else:
                detail_voice = f"HTTP {r.status_code}"
        except Exception as exc:
            detail_voice = str(exc)[:80]

        score_voice = WEIGHTS["voice"] if ok_voice else 0
        categories["voice"] = {
            "score":  score_voice,
            "max":    WEIGHTS["voice"],
            "status": "pass" if ok_voice else "fail",
            "detail": detail_voice,
        }
        if not ok_voice:
            recommendations.append(
                "TTS/Whisper dégradé — vérifier edge-tts et Whisper dans le backend"
            )

        # ── bruce (5 pts) — optionnel, warn seulement ────────
        ok_bruce = False
        detail_bruce = "offline"
        try:
            r = await client.get(f"{OPENHANDS_URL}/api/options/models", timeout=2.0)
            ok_bruce     = r.status_code < 500
            detail_bruce = f"HTTP {r.status_code}"
        except Exception as exc:
            detail_bruce = str(exc)[:80]

        score_bruce = WEIGHTS["bruce"] if ok_bruce else 0
        categories["bruce"] = {
            "score":  score_bruce,
            "max":    WEIGHTS["bruce"],
            "status": "pass" if ok_bruce else "warn",
            "detail": detail_bruce,
        }
        if not ok_bruce:
            recommendations.append(
                "BRUCE optionnel — lancer: docker compose --profile bruce up bruce"
            )

        # ── memory_embed (5 pts) — nomic-embed-text dans Ollama ─
        embed_ok     = False
        detail_embed = "nomic-embed-text absent"
        if ok_ol:
            # models est déjà rempli depuis le check ollama
            model_names  = [m.get("name", "") for m in models]
            embed_ok     = any("nomic-embed-text" in n for n in model_names)
            detail_embed = (
                "nomic-embed-text disponible"
                if embed_ok
                else f"Modèles: {', '.join(model_names[:4]) or 'aucun'}"
            )
        else:
            detail_embed = "Ollama offline — impossible de vérifier"

        score_embed = WEIGHTS["memory_embed"] if embed_ok else 0
        categories["memory_embed"] = {
            "score":  score_embed,
            "max":    WEIGHTS["memory_embed"],
            "status": "pass" if embed_ok else "warn",
            "detail": detail_embed,
        }
        if not embed_ok:
            recommendations.append(
                "Embeddings manquants — installer: ollama pull nomic-embed-text"
            )

    # ── Score final ──────────────────────────────────────────
    total = (
        score_backend + score_claude + score_ollama + score_vault
        + score_forge + score_files + score_voice + score_bruce + score_embed
    )

    return {
        "score":           total,
        "grade":           _grade(total),
        "status":          _status(total),
        "categories":      categories,
        "timestamp":       datetime.now().isoformat(),
        "recommendations": recommendations,
    }


# ── Forge reliability ────────────────────────────────────────

def get_forge_reliability() -> dict:
    """
    Lit forge_missions_cache.json et retourne les métriques de fiabilité du pipeline.

    Returns:
        dict avec success_rate, avg_score, last_mission_status, bambu_ready_pct.
    """
    cache_path = Path(__file__).parent / "forge_missions_cache.json"

    if not cache_path.exists():
        return {
            "success_rate":       0.0,
            "avg_score":          0.0,
            "last_mission_status": "unknown",
            "bambu_ready_pct":    0.0,
            "total_missions":     0,
            "completed":          0,
        }

    try:
        data: dict = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "success_rate":       0.0,
            "avg_score":          0.0,
            "last_mission_status": "error",
            "bambu_ready_pct":    0.0,
            "total_missions":     0,
            "completed":          0,
        }

    missions = list(data.values())
    total    = len(missions)
    if total == 0:
        return {
            "success_rate":       0.0,
            "avg_score":          0.0,
            "last_mission_status": "none",
            "bambu_ready_pct":    0.0,
            "total_missions":     0,
            "completed":          0,
        }

    completed   = [m for m in missions if m.get("status") == "completed"]
    success_cnt = len(completed)
    success_rate = round(success_cnt / total * 100, 1)

    # Moyenne printability_score (seulement missions avec rapport)
    scores = [
        m["report"]["printability_score"]
        for m in completed
        if isinstance(m.get("report"), dict) and "printability_score" in m["report"]
    ]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    # % Bambu-ready
    bambu_ready = [
        m for m in completed
        if isinstance(m.get("report"), dict) and m["report"].get("bambu_ready") is True
    ]
    bambu_ready_pct = round(len(bambu_ready) / success_cnt * 100, 1) if success_cnt else 0.0

    # Dernière mission (tri par completed_at)
    sorted_missions = sorted(
        missions,
        key=lambda m: m.get("completed_at") or m.get("created_at") or "",
        reverse=True,
    )
    last_mission_status = sorted_missions[0].get("status", "unknown") if sorted_missions else "unknown"

    return {
        "success_rate":        success_rate,
        "avg_score":           avg_score,
        "last_mission_status": last_mission_status,
        "bambu_ready_pct":     bambu_ready_pct,
        "total_missions":      total,
        "completed":           success_cnt,
    }

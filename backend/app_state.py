"""Shared application state & helpers for the Nexus9 backend.

Single home for cross-router state (Anthropic client, budget, agent status,
base system prompt, cost helper) so feature routers can import these without
a circular dependency on main.py.

NOTE: the shared httpx client (`_http`) still lives in main.py because it is
(re)assigned by the lifespan; it will move here with a getter when the
health/agents routers are extracted.
"""

import logging
import os
import traceback

import budget_tracker
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL      = os.getenv("CLAUDE_MODEL",      "claude-haiku-4-5-20251001")
CLAUDE_MODEL_GROS = os.getenv("CLAUDE_MODEL_GROS", "claude-sonnet-4-6")
PORT              = int(os.getenv("BACKEND_PORT", 8000))

_default_origins = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174,"  # Nexusx9 React hub (vite --port 5174)
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:8080,http://127.0.0.1:8080"
)
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _default_origins).split(",")
    if o.strip()
]

if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY manquant dans .env")

# ── Logger erreurs 500 ───────────────────────────────────
_ERROR_LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "error_logs"))
os.makedirs(_ERROR_LOGS_DIR, exist_ok=True)
_error_handler = logging.FileHandler(
    os.path.join(_ERROR_LOGS_DIR, "errors.log"),
    encoding="utf-8",
)
_error_handler.setLevel(logging.ERROR)
_error_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
_error_logger = logging.getLogger("nexus.errors")
_error_logger.setLevel(logging.ERROR)
_error_logger.addHandler(_error_handler)
_error_logger.propagate = False


def _log_error_500(route: str, exc: Exception) -> None:
    """Log traceback complet dans backend/error_logs/errors.log."""
    _error_logger.error(
        "ROUTE=%s | %s: %s\n%s",
        route, type(exc).__name__, exc, traceback.format_exc(),
    )


claude = Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_base_system() -> str:
    """Construit le prompt de base depuis config.json (langue dynamique)."""
    from memory import load_config
    cfg = load_config().get("jarvis", {})
    lang = cfg.get("language", "Français")
    personality = cfg.get("personality", "")
    if personality:
        return personality
    # Fallback si config vide
    return (
        f"Tu es JARVIS, l'assistant IA personnel de David Arbour. "
        f"Réponds TOUJOURS en {lang}. "
        "Tu es direct, tactique, futuriste. "
        "Tu as accès au workspace Jarvis via les endpoints /v1/jarvis/files/. "
        "Consulte les fichiers workspace avant de répondre à des questions spécifiques aux projets."
    )


BASE_SYSTEM = _build_base_system()

# ── Budget ───────────────────────────────────────────────
BUDGET_MAX_USD = float(os.getenv("BUDGET_MAX_USD", "2.0"))

_budget = {
    "cout_usd":      0.0,
    "appels_ollama": 0,
    "appels_claude": 0,
}


def _budget_ok() -> bool:
    return _budget["cout_usd"] < BUDGET_MAX_USD


def _enregistrer_cout(tokens: int, model: str, input_tokens: int = 0, output_tokens: int = 0):
    prix = 0.003 if "sonnet" in model else 0.00025
    cout = (tokens / 1000) * prix
    _budget["cout_usd"]      += cout
    _budget["appels_claude"] += 1
    # Persistance dans budget_logs.json
    budget_tracker.record_call(model, input_tokens or tokens // 2, output_tokens or tokens // 2)
    print(
        f"[budget] {model}: {tokens} tokens = ${cout:.5f} "
        f"| session: ${_budget['cout_usd']:.4f} / ${BUDGET_MAX_USD}"
    )


# ── État global ──────────────────────────────────────────
_crew_jobs: dict[str, dict] = {}

_agents_status: dict[str, str] = {
    "JARVIS":   "online",   # orchestrateur — claude-haiku-4-5
    "ULTRON":   "idle",     # claude-sonnet-4-6 — designer créatif
    "FORGE":    "idle",     # meshy AI + repair pipeline — ingénieur 3D (ex-KAIZEN)
    "QWEN":     "idle",     # ollama qwen3:14b
    "CORTANA":  "idle",     # deepseek-coder:6.7b
    "BRUCE":    "offline",  # openhands + qwen3:14b — repair + autonome
    "NOVA":     "idle",     # ollama deepseek-r1:7b — reasoning & complex code
}

# ── Client HTTP partagé (connection pooling) ─────────────
# Set by main's lifespan via set_http(); read everywhere via get_http().
# Returns None before startup, so callers can guard with `if get_http() is None`.
_http = None


def set_http(client) -> None:
    global _http
    _http = client


def get_http():
    """Return the shared httpx.AsyncClient (None before lifespan startup)."""
    return _http

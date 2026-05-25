"""
OpenJarvis Nexus — Backend v0.5.0
FastAPI + Claude + Ollama + CrewAI + SSE Streaming + Mémoire
"""

import os
import re
import time
import json
import logging
import traceback
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from anthropic import Anthropic, APIError
import httpx

from memory import (
    get_history, add_message, clear_session, list_sessions,
    load_facts, save_facts, build_system_prompt, load_config,
    get_last_session_summary, is_new_session, compress_session_sync,
)
from ollama_client import (
    is_ollama_available, list_local_models,
    ask_ollama_chat, should_use_claude, get_claude_model, stream_ollama_chat, strip_think_tags,
    OLLAMA_MODEL,
)
from tools.docker_tools import (
    CLAUDE_TOOL_DEFS as _DOCKER_TOOL_DEFS,
    dispatch as _docker_dispatch,
    quick_status_text as _docker_quick_status,
)
from tools.skill_tools import (
    CLAUDE_TOOL_DEFS as _SKILL_TOOL_DEFS,
    dispatch as _skill_dispatch,
    skill_catalog_text as _skill_catalog_text,
)

# ── Environnement ────────────────────────────────────────
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

claude      = Anthropic(api_key=ANTHROPIC_API_KEY)
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
    "KAIZEN":   "idle",     # meshy AI + repair pipeline — ingénieur 3D
    "QWEN":     "idle",     # ollama qwen3:14b
    "CORTANA":  "idle",     # deepseek-coder:6.7b
    "BRUCE":    "offline",  # openhands + qwen3:14b — repair + autonome
}

# ── Client HTTP partagé (connection pooling) ─────────────
# Initialisé dans _lifespan, fermé proprement au shutdown.
# Utiliser _http pour tous les appels httpx dans main.py.
_http: httpx.AsyncClient | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Gère le cycle de vie de l'app (remplace @app.on_event deprecated)."""
    import asyncio as _asyncio

    # ── STARTUP ──────────────────────────────────────────
    global _http
    _http = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    )

    from memory import load_config as _lc
    _cfg = _lc().get("jarvis", {})

    # Pré-charger Kokoro si configuré (évite la latence au 1er appel TTS)
    if _cfg.get("tts_engine") == "kokoro":
        _voice = _cfg.get("tts_voice_kokoro", "bm_george")
        _lc_code = _voice[0] if _voice else "b"
        try:
            await _asyncio.to_thread(_get_kokoro_pipeline, _lc_code)
            print(f"[TTS] Kokoro pré-chargé (lang={_lc_code}, voice={_voice})")
        except Exception as _e:
            print(f"[TTS] Kokoro pré-chargement ignoré: {_e}")

    # ── Scheduler APScheduler (STL research 21:00 + tâches quotidiennes) ────
    from apscheduler.triggers.cron import CronTrigger as _CronTrigger
    _scheduler = create_scheduler()
    _scheduler.add_job(
        generate_daily_report,
        _CronTrigger(hour=21, minute=0),
        id="daily_stl_research",
        name="Daily: stl_research",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    app.state.scheduler = _scheduler
    print("[Daily] Scheduler démarré — STL research 21:00, brain re-index 03:55 (daily_tasks)")

    # ── Ollama heartbeat — garde qwen3:14b chaud en VRAM ────────────────
    # Ping toutes les 4 min entre 7h et 23h. En dehors → Ollama libère la VRAM.
    async def _ollama_heartbeat():
        import asyncio as _aio
        from datetime import datetime as _dt
        from config import OLLAMA_HOST as _OHB_HOST, OLLAMA_MODEL as _OHB_MODEL, OLLAMA_NUM_CTX as _OHB_CTX
        _hb_url = f"{_OHB_HOST}/api/generate"
        while True:
            await _aio.sleep(240)  # 4 minutes
            _hour = _dt.now().hour
            if 7 <= _hour < 23:
                try:
                    await _http.post(_hb_url, json={
                        "model":  _OHB_MODEL,
                        "prompt": "",
                        "stream": False,
                        "options": {"num_predict": 1, "num_ctx": _OHB_CTX},
                    }, timeout=10.0)
                except Exception:
                    pass  # Ollama indisponible — silencieux

    _asyncio.create_task(_ollama_heartbeat())
    from config import OLLAMA_MODEL as _hb_model_name
    print(f"[Ollama] Heartbeat démarré — {_hb_model_name} restera chaud 07h-23h.")

    print("[Nexus9] Startup complet — client HTTP partagé prêt.")
    yield

    # ── SHUTDOWN ─────────────────────────────────────────
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        print("[Daily] Scheduler arrêté")
    await _http.aclose()
    # Close shared Playwright browser if it was used
    try:
        from scrapers.browser import close_browser as _close_browser
        await _close_browser()
        print("[Browser] Playwright browser fermé.")
    except Exception:
        pass
    print("[Nexus9] Shutdown — client HTTP fermé.")


# ── App ──────────────────────────────────────────────────
app = FastAPI(title="OpenJarvis Nexus Backend", version="0.5.0", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

import budget_tracker
from stl_agent import router as stl_router
from stl_researcher import router as research_router, generate_daily_report
from forge_room.forge_engine import router as forge_router
from daily_tasks import create_scheduler
from vault.vault_router import router as vault_router
from jarvis_files import router as files_router
from orchestrator import orchestrate, classify_intent
from smoke_tests import run_smoke_tests
from commerce.commerce_router import router as commerce_router
from commerce.etsy_oauth import router as etsy_oauth_router
from monitoring_router import router as monitoring_router
from ws_router import router as ws_router
from daily_briefing import router as briefing_router
from trend_hunter import router as trends_router
app.include_router(stl_router)
app.include_router(research_router)
app.include_router(forge_router)
app.include_router(vault_router)
app.include_router(files_router)
app.include_router(commerce_router)
app.include_router(etsy_oauth_router)
app.include_router(monitoring_router)
app.include_router(ws_router)
app.include_router(briefing_router)
app.include_router(trends_router)

# ── Sert Nexus9.html (UI principale) à la racine ─────────
# Permet l'accès micro (Web Speech API exige un contexte sécurisé : localhost OK, file:// bloqué)
_NEXUS9_HTML = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "archive", "legacy", "Nexus9.html"))
# ── Phase 5 : React Command Center SPA buildé ───────────
_FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
_SPA_INDEX = os.path.join(_FRONTEND_DIST, "index.html")
_SPA_ASSETS = os.path.join(_FRONTEND_DIST, "assets")

def _spa_or_legacy_html():
    """Sert le SPA React si dist/index.html existe, sinon fallback Nexus9.html."""
    if os.path.isfile(_SPA_INDEX):
        return FileResponse(_SPA_INDEX, media_type="text/html")
    return FileResponse(_NEXUS9_HTML, media_type="text/html")

@app.get("/")
async def serve_root():
    return _spa_or_legacy_html()

@app.get("/nexus9.html")
async def serve_nexus9_alias():
    """Alias legacy — sert toujours l'ancien Nexus9.html monolithique."""
    return FileResponse(_NEXUS9_HTML, media_type="text/html")

# ── Etsy OAuth callback — reçoit le code d'autorisation ──
# Etsy redirige vers cette URL après que l'utilisateur autorise l'accès
@app.get("/callback", include_in_schema=False)
async def etsy_oauth_callback_root(code: str = None, state: str = None, error: str = None):
    """Callback OAuth Etsy — échange le code et affiche la page de confirmation."""
    from fastapi.responses import HTMLResponse
    if error:
        html = f"""<!DOCTYPE html><html><head><title>Etsy OAuth — Erreur</title></head>
        <body style="background:#02050b;color:#ff2d55;font-family:monospace;padding:40px">
        <h2>❌ Erreur OAuth Etsy</h2><p>{error}</p></body></html>"""
        return HTMLResponse(html, status_code=400)
    if not code:
        html = """<!DOCTYPE html><html><body style="background:#02050b;color:#ff2d55;font-family:monospace;padding:40px">
        <h2>❌ Code OAuth manquant</h2></body></html>"""
        return HTMLResponse(html, status_code=400)
    # Affiche le code et les instructions
    html = f"""<!DOCTYPE html>
    <html><head><title>Nexus9 — Etsy OAuth</title>
    <style>body{{background:#02050b;color:#b0c8e8;font-family:'Courier New',monospace;padding:40px;max-width:700px;margin:0 auto}}
    h2{{color:#00d4ff;letter-spacing:3px}} .code{{background:#040a14;border:1px solid #173050;padding:16px;border-radius:8px;font-size:13px;word-break:break-all;color:#00ff88}}
    .btn{{background:rgba(0,212,255,.15);border:1px solid rgba(0,212,255,.4);color:#00d4ff;padding:12px 24px;border-radius:6px;cursor:pointer;font:700 12px monospace;letter-spacing:2px}}
    </style></head>
    <body>
    <h2>⬡ NEXUS9 — ETSY OAUTH</h2>
    <p style="color:#00ff88">✓ Autorisation reçue</p>
    <p>Code OAuth:</p>
    <div class="code">{code}</div>
    <br>
    <p>Ce code a été transmis à JARVIS. Ferme cette fenêtre.</p>
    <p style="color:#5a7a9a;font-size:11px">State: {state or 'N/A'}</p>
    <script>
    // Auto-exchange du code via l'API backend
    fetch('/v1/etsy/exchange-token', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{code: '{code}', state: '{state or ""}', redirect_uri: window.location.origin + '/callback'}})
    }}).then(r => r.json()).then(d => {{
        const el = document.createElement('div');
        el.style.cssText = 'margin-top:16px;padding:12px;border-radius:6px;';
        if (d.ok) {{
            el.style.background = 'rgba(0,255,136,.08)';
            el.style.border = '1px solid rgba(0,255,136,.3)';
            el.style.color = '#00ff88';
            el.innerHTML = '<b>✓ Token échangé avec succès!</b><br>Ajoute dans .env:<br><code>' + (d.env_line || '') + '</code>';
        }} else {{
            el.style.background = 'rgba(255,45,85,.08)';
            el.style.border = '1px solid rgba(255,45,85,.3)';
            el.style.color = '#ff2d55';
            el.innerHTML = '<b>⚠ Échange manuel requis</b><br>POST /v1/etsy/exchange-token avec ce code';
        }}
        document.body.appendChild(el);
    }}).catch(() => {{}});
    </script>
    </body></html>"""
    return HTMLResponse(html)

# ── Orbital UI — couche visuelle modulaire ────────────────
from fastapi.staticfiles import StaticFiles
_ORBITAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "archive", "legacy", "orbital_ui_vanilla"))

@app.get("/orbital", include_in_schema=False)
async def serve_orbital():
    """Phase 5 : sert le SPA React si buildé, sinon l'ancien orbital.html vanilla."""
    if os.path.isfile(_SPA_INDEX):
        return FileResponse(_SPA_INDEX, media_type="text/html")
    return FileResponse(os.path.join(_ORBITAL_DIR, "orbital.html"), media_type="text/html")

@app.get("/orbital-legacy", include_in_schema=False)
async def serve_orbital_legacy():
    """Accès explicite à l'ancien orbital_ui vanilla (avant Phase 3 React)."""
    return FileResponse(os.path.join(_ORBITAL_DIR, "orbital.html"), media_type="text/html")

if os.path.isdir(_ORBITAL_DIR):
    app.mount("/orbital_ui", StaticFiles(directory=_ORBITAL_DIR), name="orbital_ui")

_FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <polygon points="16,1 31,8.5 31,23.5 16,31 1,23.5 1,8.5"
           fill="#00c8ff" opacity="0.9"/>
  <polygon points="16,5 27,11 27,21 16,27 5,21 5,11"
           fill="#030609"/>
  <polygon points="16,9 23,13 23,19 16,23 9,19 9,13"
           fill="#00c8ff" opacity="0.7"/>
</svg>"""

@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.svg", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(content=_FAVICON_SVG, media_type="image/svg+xml")

# ── Lancement d'apps locales (whitelist) ─────────────────
# Permet à Jarvis d'ouvrir VS Code, Claude desktop, ou une URL depuis Nexus9.html
import subprocess
import webbrowser

VSCODE_PATH = os.getenv("VSCODE_PATH", r"C:\Users\bobby\AppData\Local\Programs\Microsoft VS Code\Code.exe")
CLAUDE_APP_PATH = os.getenv("CLAUDE_APP_PATH", r"C:\Users\bobby\AppData\Local\AnthropicClaude\Claude.exe")
MORNING_YOUTUBE_URL = os.getenv("MORNING_YOUTUBE_URL", "https://www.youtube.com/watch?v=EJqFjvKF8HU")

class OpenRequest(BaseModel):
    target: str  # 'vscode' | 'claude' | 'youtube' | 'url' | 'morning'
    url: Optional[str] = None

def _launch_target(target: str, url: Optional[str] = None) -> dict:
    """Lance une app whitelistée. Retourne {ok, target, detail}."""
    try:
        if target == "vscode":
            if not os.path.exists(VSCODE_PATH):
                return {"ok": False, "target": target, "detail": f"VS Code introuvable: {VSCODE_PATH}"}
            subprocess.Popen([VSCODE_PATH], creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0)
            return {"ok": True, "target": target, "detail": "VS Code lancé"}
        if target == "claude":
            if not os.path.exists(CLAUDE_APP_PATH):
                return {"ok": False, "target": target, "detail": f"Claude app introuvable: {CLAUDE_APP_PATH}"}
            subprocess.Popen([CLAUDE_APP_PATH], creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0)
            return {"ok": True, "target": target, "detail": "Claude app lancée"}
        if target == "youtube":
            webbrowser.open(MORNING_YOUTUBE_URL)
            return {"ok": True, "target": target, "detail": MORNING_YOUTUBE_URL}
        if target == "url":
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                return {"ok": False, "target": target, "detail": "URL invalide (doit commencer par http(s)://)"}
            webbrowser.open(url)
            return {"ok": True, "target": target, "detail": url}
        return {"ok": False, "target": target, "detail": f"Target inconnu: {target}"}
    except Exception as e:
        return {"ok": False, "target": target, "detail": str(e)}

@app.post("/v1/system/open")
async def system_open(req: OpenRequest):
    """Lance une app locale (whitelistée) ou une URL."""
    return _launch_target(req.target, req.url)

@app.post("/v1/system/morning-routine")
async def morning_routine():
    """Routine matinale : YouTube + VS Code + Claude app dans l'ordre."""
    results = [
        _launch_target("youtube"),
        _launch_target("vscode"),
        _launch_target("claude"),
    ]
    return {"opened": results, "count_ok": sum(1 for r in results if r["ok"])}

@app.post("/v1/pipeline/start-all")
async def pipeline_start_all():
    """Lance START_ALL.bat dans une nouvelle fenêtre console (détachée)."""
    import subprocess
    bat = r"C:\OpenJarvisNexus\START_ALL.bat"
    try:
        subprocess.Popen(  # NOSONAR - intentional detached fire-and-forget
            ["cmd", "/c", bat],
            cwd=r"C:\OpenJarvisNexus",
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_CONSOLE,
        )
        return {"status": "launched", "message": "START_ALL.bat lancé dans une nouvelle fenêtre"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Brain re-index endpoint (appelé par le vault_graph sidecar après chaque sync) ──

@app.post("/v1/brain/reindex")
async def brain_reindex_endpoint(background_tasks: BackgroundTasks):
    """
    Lance un re-index incrémental du brain Obsidian dans ChromaDB.
    Fire-and-forget : retourne immédiatement, l'indexage tourne en arrière-plan.
    Appelé automatiquement par le sidecar vault_graph après chaque vault:sync.
    """
    async def _run():
        try:
            from vault.brain_index import index_brain
            result = await index_brain()
            print(f"[Brain] post-sync re-index: {result.get('indexed')} indexed / {result.get('total')} total")
        except Exception as e:
            print(f"[Brain] post-sync re-index failed: {e}")

    background_tasks.add_task(_run)
    return {"status": "reindex_started"}


@app.post("/v1/brain/autolink")
async def brain_autolink_endpoint(
    background_tasks: BackgroundTasks,
    dry_run: bool = False,
):
    """
    Obsidian Knowledge Auto-Linker :
    - Normalise les tags frontmatter (ajoute les tags attendus par dossier, supprime doublons inline)
    - Crée les MOCs manquants (moc-trading, moc-dropshipping, moc-ia, moc-mindset)
    - Détecte les backlinks implicites (mentions sans [[link]]) et les ajoute
    - Génère un rapport d'audit dans BRAIN/05_Resources/Research/autolink-report-*.md
    Fire-and-forget (background) — retourne immédiatement.
    Param dry_run=true : calcule tout sans écrire aucun fichier.
    """
    import asyncio as _aio

    result_holder: dict = {}

    async def _run():
        try:
            from brain_autolinker import run_autolink
            r = await _aio.to_thread(run_autolink, dry_run)
            result_holder.update(r)
            print(
                f"[AutoLinker] DONE — {len(r['mocs_created'])} MOCs | "
                f"{len(r['tags_fixed'])} tags | {r['implicit_links_added']} liens | "
                f"{r['elapsed_ms']}ms"
            )
        except Exception as e:
            result_holder["error"] = str(e)
            print(f"[AutoLinker] ERREUR: {e}")

    background_tasks.add_task(_run)
    return {
        "status":  "autolink_started",
        "dry_run": dry_run,
        "message": "Rapport disponible dans BRAIN/05_Resources/Research/autolink-report-{date}.md",
    }


@app.post("/v1/brain/autolink/sync")
async def brain_autolink_sync_endpoint(dry_run: bool = False):
    """
    Version synchrone (attend le résultat) — usage : debug / CLI.
    Retourne le rapport complet. Peut prendre quelques secondes.
    """
    import asyncio as _aio
    try:
        from brain_autolinker import run_autolink
        result = await _aio.to_thread(run_autolink, dry_run)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Import configuration depuis nexus9-setup.md ────────────────────────────

@app.post("/v1/setup/import")
async def import_setup():
    """
    Lit BRAIN/08_Command-Center/nexus9-setup.md et met à jour config.json + memory.json.
    Déclencher via : POST /v1/setup/import
    Ou depuis le chat : "JARVIS, importe la configuration nexus9-setup"
    """
    import re as _re
    import asyncio as _aio

    brain_setup = (
        Path(__file__).parent / "BRAIN" / "BRAIN" / "08_Command-Center" / "nexus9-setup.md"
    )
    if not brain_setup.exists():
        raise HTTPException(404, f"Fichier introuvable : {brain_setup}")

    raw = brain_setup.read_text(encoding="utf-8")

    def _extract_block(header: str) -> list[str]:
        """Extrait les lignes non-commentaires du bloc de code sous `header`."""
        pattern = rf"### {_re.escape(header)}\n.*?```\n(.*?)```"
        m = _re.search(pattern, raw, _re.DOTALL)
        if not m:
            return []
        return [
            line.strip()
            for line in m.group(1).splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    def _extract_checked(header: str) -> list[str]:
        """Extrait les items cochés [x] sous `header`."""
        pattern = rf"### {_re.escape(header)}\n(.*?)(?=\n###|\n---|\Z)"
        m = _re.search(pattern, raw, _re.DOTALL)
        if not m:
            return []
        return [
            _re.sub(r"^- \[x\] \*\*(\w+)\*\*.*", r"\1", line.strip()).split(" — ")[0].split("**")[0].strip()
            for line in m.group(1).splitlines()
            if line.strip().startswith("- [x]")
        ]

    # ── Trend Hunter ────
    tickers    = _extract_block("Tickers boursiers (actions / ETFs)")
    crypto     = _extract_block("Cryptomonnaies")
    keywords   = _extract_block("Mots-clés dropshipping à surveiller")
    subreddits = _extract_block("Subreddits à surveiller")
    th_time    = _extract_block("Heure du fetch quotidien (format HH:MM)")
    th_h, th_m = (int(x) for x in (th_time[0] if th_time else "06:00").split(":"))

    # ── Daily Briefing ──
    sections   = _extract_checked("Sections à inclure dans le brief matinal")
    bf_time    = _extract_block("Heure du brief automatique (format HH:MM)")
    bf_h, bf_m = (int(x) for x in (bf_time[0] if bf_time else "07:30").split(":"))
    greeting   = (_extract_block("Message d'accueil personnalisé") or ["Bonjour David. Voici ton brief du {date}."])[0]

    # ── Session Continuity ──
    gap_raw    = _extract_block("Délai avant \"nouvelle session\" (en minutes)")
    gap_min    = int(gap_raw[0]) if gap_raw else 60
    summ_raw   = _extract_block("Nombre de messages à inclure dans le résumé de session")
    summ_msgs  = int(summ_raw[0]) if summ_raw else 10

    # ── Memory Compression ──
    thresh_raw = _extract_block("Seuil de compression (nombre de messages)")
    threshold  = int(thresh_raw[0]) if thresh_raw else 30
    keep_raw   = _extract_block("Messages récents à préserver (jamais compressés)")
    keep       = int(keep_raw[0]) if keep_raw else 10
    model_raw  = _extract_block("Modèle IA pour la compression")
    comp_model = model_raw[0] if model_raw else "qwen3:14b"

    # ── Infos personnelles ──
    projects   = _extract_block("Projets actifs (un par ligne)")
    goals      = _extract_block("Objectifs 2026 (un par ligne)")
    stack      = _extract_block("Stack technique principale (un par ligne)")
    notes_raw  = _extract_block("Notes importantes (infos que JARVIS doit toujours retenir)")

    # ── Patch config.json ──
    cfg_file = Path(__file__).parent / "config.json"
    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))

    cfg["trend_hunter"] = {
        **cfg.get("trend_hunter", {}),
        "tickers":              tickers,
        "crypto":               crypto,
        "dropshipping_keywords": keywords,
        "reddit_subreddits":    subreddits,
        "schedule_hour":        th_h,
        "schedule_minute":      th_m,
    }
    cfg["daily_briefing"] = {
        **cfg.get("daily_briefing", {}),
        "sections":           sections or ["health", "vault_stubs", "stl_trends", "watchlist", "tasks"],
        "schedule_hour":      bf_h,
        "schedule_minute":    bf_m,
        "greeting_template":  greeting,
    }
    cfg["session_continuity"] = {
        **cfg.get("session_continuity", {}),
        "gap_minutes":            gap_min,
        "max_summary_messages":   summ_msgs,
    }
    cfg["memory_compression"] = {
        **cfg.get("memory_compression", {}),
        "threshold_messages":   threshold,
        "keep_recent_messages": keep,
        "compression_model":    comp_model,
    }
    cfg_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Patch memory.json — LEAN uniquement ──────────────────────────────────
    # Règle : memory.json = injecté dans CHAQUE prompt → garder minimal.
    # Données riches (goals, stack, observations) → restent dans le Vault Obsidian
    # et sont récupérées via ChromaDB/_needs_memory() uniquement quand pertinent.
    from memory import load_facts, save_facts
    facts = load_facts()

    # Projets actifs : top 5 max (ce qui est TOUJOURS pertinent)
    if projects:
        facts["projects"] = projects[:5]

    # Notes critiques : top 5 max, seulement si remplies
    if notes_raw:
        facts["notes"] = notes_raw[:5]

    # goals / tech_stack / observations → NE PAS injecter dans memory.json
    # Ils vivent dans nexus9-setup.md (Vault) et ChromaDB les indexe via brain_reindex.
    save_facts(facts)

    # ── Mettre à jour le tableau de bord dans le fichier setup ──
    today = datetime.now().strftime("%Y-%m-%d")
    updated_raw = raw.replace(
        "| Session Continuity | ⏳ À configurer | — |",
        f"| Session Continuity | ✅ Configuré | {today} |",
    ).replace(
        "| Memory Compression | ⏳ À configurer | — |",
        f"| Memory Compression | ✅ Configuré | {today} |",
    ).replace(
        "| Daily Briefing | ⏳ À configurer | — |",
        f"| Daily Briefing | ✅ Configuré | {today} |",
    ).replace(
        "| Trend Hunter | ⏳ À configurer | — |",
        f"| Trend Hunter | ✅ Configuré | {today} |",
    )
    brain_setup.write_text(updated_raw, encoding="utf-8")

    return {
        "ok": True,
        "imported_at": datetime.now().isoformat(),
        "trend_hunter": {
            "tickers": tickers, "crypto": crypto,
            "keywords": keywords, "subreddits": subreddits,
            "schedule": f"{th_h:02d}:{th_m:02d}",
        },
        "daily_briefing": {
            "sections": sections, "schedule": f"{bf_h:02d}:{bf_m:02d}",
            "greeting": greeting,
        },
        "session_continuity": {"gap_minutes": gap_min, "max_summary": summ_msgs},
        "memory_compression": {"threshold": threshold, "keep": keep, "model": comp_model},
        "memory_json": {"projects": len(projects), "goals": len(goals), "notes": len(notes_raw)},
        "message": "✅ config.json + memory.json mis à jour — redémarre le backend pour recharger le scheduler",
    }


# (Scheduler démarré dans _lifespan — voir début du fichier)

@app.post("/v1/pipeline/daily/start")
def daily_research_start():
    """Lance le daily research en background — retourne immédiatement."""
    from pipeline_runner import start_daily_research_background
    return start_daily_research_background()


@app.get("/v1/pipeline/daily/status")
def daily_research_status():
    """Statut en temps réel du daily research (polling toutes les 5s)."""
    from pipeline_runner import get_research_state
    return get_research_state()


@app.post("/v1/daily/run-task")
async def daily_run_task(body: dict):
    """Exécute une daily task par nom. Body: {"task": "vault_cleanup"}"""
    from daily_tasks import (
        task_vault_cleanup, task_forge_analytics, task_stl_directory_sync,
        task_system_health_log, task_error_logs_cleanup, task_vault_maintenance,
        task_commerce_analytics,
        task_jarvis_workspace_index, task_daily_smoke_tests,
        task_orchestration_diagnostics,
    )
    _task_map = {
        "vault_cleanup":             task_vault_cleanup,
        "forge_analytics":           task_forge_analytics,
        "stl_sync":                  task_stl_directory_sync,
        "health_log":                task_system_health_log,
        "error_log_cleanup":         task_error_logs_cleanup,
        "vault_maintenance":         task_vault_maintenance,
        "commerce_analytics":        task_commerce_analytics,
        "jarvis_workspace_index":    task_jarvis_workspace_index,
        "daily_smoke_tests":         task_daily_smoke_tests,
        "orchestration_diagnostics": task_orchestration_diagnostics,
    }
    name = body.get("task", "")
    fn   = _task_map.get(name)
    if not fn:
        raise HTTPException(404, f"Tâche inconnue: {name}. Dispo: {list(_task_map)}")
    try:
        await fn()
        return {"ok": True, "task": name, "message": f"{name} exécutée avec succès"}
    except Exception as e:
        return {"ok": False, "task": name, "message": str(e)}


@app.post("/v1/daily/run-all")
async def daily_run_all():
    """Exécute toutes les daily tasks et retourne le rapport complet."""
    from pipeline_runner import run_daily_tasks, save_report
    daily = await run_daily_tasks()
    save_report("daily", daily)
    return daily


@app.post("/v1/report/save")
async def report_save(body: dict):
    """Sauvegarde un rapport dans le brain (08_Command-Center/reports/{type})."""
    from pipeline_runner import save_report
    type_ = body.get("type", "pipelines")
    data  = body.get("data", {})
    path  = save_report(type_, data)
    return {"ok": bool(path), "path": str(path) if path else None}


@app.get("/v1/daily/status")
def daily_status():
    """Statut du scheduler de tâches quotidiennes."""
    if not hasattr(app.state, "scheduler"):
        return {"status": "not_started"}
    jobs = [
        {"id": j.id, "name": j.name, "next_run": str(j.next_run_time)}
        for j in app.state.scheduler.get_jobs()
    ]
    return {"status": "running", "jobs": jobs}

# ── Schémas ──────────────────────────────────────────────
class ChatMessage(BaseModel):
    role:    str
    content: str

class ChatRequest(BaseModel):
    message:     Optional[str]               = None
    messages:    Optional[list[ChatMessage]] = None
    model:       Optional[str]               = None
    system:      Optional[str]               = None
    max_tokens:  int                         = 1024
    temperature: float                       = 0.7
    stream:      bool                        = False
    session_id:  str                         = "default"

class FactsUpdate(BaseModel):
    user_name:   Optional[str]       = None
    full_name:   Optional[str]       = None
    location:    Optional[str]       = None
    projects:    Optional[list[str]] = None
    preferences: Optional[list[str]] = None
    tech_stack:  Optional[list[str]] = None
    goals:       Optional[list[str]] = None
    notes:       Optional[list[str]] = None

class CrewRequest(BaseModel):
    mission:      str
    mission_type: str = "auto"

# ── Helpers ──────────────────────────────────────────────
def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

def _get_session_id(req: ChatRequest, request: Request) -> str:
    if req.session_id and req.session_id != "default":
        return req.session_id
    ip = request.client.host if request.client else "local"
    return f"ip:{ip}"

def _stream_text(text: str, model_used: str, req_id: str, memory: dict | None = None):
    yield _sse({
        "id": req_id, "object": "chat.completion.chunk",
        "model": model_used,
        "choices": [{"index": 0,
                     "delta": {"role": "assistant", "content": ""},
                     "finish_reason": None}]
    })
    for i in range(0, len(text), 12):
        yield _sse({
            "id": req_id, "object": "chat.completion.chunk",
            "model": model_used,
            "choices": [{"index": 0,
                         "delta": {"content": text[i:i+12]},
                         "finish_reason": None}]
        })
        time.sleep(0.01)
    _final = {
        "id": req_id, "object": "chat.completion.chunk",
        "model": model_used,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    if memory:
        _final["memory"] = memory
    yield _sse(_final)
    yield "data: [DONE]\n\n"

# ════════════════════════════════════════════════════════
# ROUTES SYSTÈME
# ════════════════════════════════════════════════════════

_health_cache: dict = {"ollama_ok": None, "ts": 0.0}
_HEALTH_TTL = 8.0  # seconds — avoid hammering Ollama on every frontend poll

@app.get("/health")
def health():
    import time as _t
    now = _t.monotonic()
    if _health_cache["ollama_ok"] is None or now - _health_cache["ts"] > _HEALTH_TTL:
        _health_cache["ollama_ok"] = is_ollama_available()
        _health_cache["ts"] = now
    ollama_ok = _health_cache["ollama_ok"]
    return {
        "status":        "ok",
        "version":       "0.5.0",
        "claude_model":  CLAUDE_MODEL,
        "ollama_online": ollama_ok,
        "ollama_model":  OLLAMA_MODEL if ollama_ok else "non disponible",
        "budget": {
            "depense":       f"${_budget['cout_usd']:.4f}",
            "maximum":       f"${BUDGET_MAX_USD}",
            "restant":       f"${BUDGET_MAX_USD - _budget['cout_usd']:.4f}",
            "appels_ollama": _budget["appels_ollama"],
            "appels_claude": _budget["appels_claude"],
        }
    }


async def _hc_claude() -> str:
    """Health check Claude API — isolé pour asyncio.gather."""
    import asyncio
    try:
        await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                None,
                lambda: claude.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "ping"}],
                ),
            ),
            timeout=5.0,
        )
        return "ok"
    except asyncio.TimeoutError:
        return "timeout"
    except Exception as e:
        return f"error: {type(e).__name__}"

async def _hc_ollama() -> str:
    """Health check Ollama."""
    return "ok" if is_ollama_available() else "offline"

async def _hc_forge() -> str:
    """Health check Forge Room — vérifie que le dossier output existe."""
    try:
        from forge_room.fabrication_pipeline import FORGE_OUTPUT
        return "ok" if FORGE_OUTPUT.exists() else "error: forge_output absent"
    except Exception as e:
        return f"error: {e}"

async def _hc_meshy() -> str:
    """Health check Meshy API — utilise le client HTTP partagé."""
    meshy_key = os.getenv("MESHY_API_KEY", "")
    if not meshy_key:
        return "not_configured"
    if _http is None:
        return "error: client_not_ready"
    try:
        r = await _http.get(
            "https://api.meshy.ai/v2/text-to-3d",
            headers={"Authorization": f"Bearer {meshy_key}"},
            timeout=3.0,
        )
        return "ok" if r.status_code in (200, 401, 403) else f"error: HTTP {r.status_code}"
    except httpx.TimeoutException:
        return "timeout"
    except Exception as e:
        return f"error: {type(e).__name__}"

@app.get("/v1/health/deep")
async def health_deep():
    """Health check approfondi — teste chaque service en parallèle (asyncio.gather).
    Retourne: backend, claude_api, ollama, forge_room, meshy_api, timestamp.
    """
    import asyncio
    now = datetime.now().isoformat(timespec="seconds")

    # Tous les checks en parallèle — latence = max(individuel) au lieu de la somme
    claude_status, ollama_status, forge_status, meshy_status = await asyncio.gather(
        _hc_claude(), _hc_ollama(), _hc_forge(), _hc_meshy()
    )

    return {
        "backend":    "ok",
        "claude_api": claude_status,
        "ollama":     ollama_status,
        "forge_room": forge_status,
        "meshy_api":  meshy_status,
        "timestamp":  now,
    }

@app.get("/v1/savings")
def savings():
    return {"balance": 0}

@app.get("/v1/telemetry/stats")
def telemetry_stats():
    return {"stats": {}}

@app.get("/v1/telemetry/energy")
def telemetry_energy():
    return {"energy": 0}


_sys_net_state = {"t": 0.0, "bytes": 0}


def _read_vram() -> dict:
    """VRAM/GPU via nvidia-smi. Retourne des None si pas de GPU NVIDIA."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        used, total, util = (int(x.strip()) for x in out.stdout.strip().splitlines()[0].split(","))
        return {"vram": round(used / total * 100), "vram_used_mb": used,
                "vram_total_mb": total, "gpu_util": util}
    except Exception:
        return {"vram": None, "vram_used_mb": None, "vram_total_mb": None, "gpu_util": None}


def _collect_system_metrics() -> dict:
    """Collecte CPU/RAM/VRAM/stockage/réseau + health score (source unique)."""
    import psutil
    cpu     = psutil.cpu_percent(interval=0.1)
    ram     = psutil.virtual_memory().percent
    storage = psutil.disk_usage("C:/").percent
    g       = _read_vram()

    net   = psutil.net_io_counters()
    total = net.bytes_sent + net.bytes_recv
    now   = time.time()
    mbps  = 0.0
    if _sys_net_state["t"]:
        dt = now - _sys_net_state["t"]
        if dt > 0:
            mbps = (total - _sys_net_state["bytes"]) / dt / 1_000_000
    _sys_net_state["t"] = now
    _sys_net_state["bytes"] = total

    score = 100
    for v in (cpu, ram, g["vram"], storage):
        if v is None:
            continue
        if v > 90:
            score -= 15
        elif v > 80:
            score -= 8
        elif v > 70:
            score -= 3
    score = max(0, score)
    label = ("OPTIMAL" if score >= 85 else "GOOD" if score >= 70
             else "FAIR" if score >= 50 else "DEGRADED")

    return {
        "cpu": round(cpu), "ram": round(ram), "storage": round(storage),
        "vram": g["vram"], "vram_used_mb": g["vram_used_mb"],
        "vram_total_mb": g["vram_total_mb"], "gpu_util": g["gpu_util"],
        "network_mbps": round(max(0.0, mbps), 1),
        "health_score": score, "health_label": label,
    }


@app.get("/v1/system/metrics")
def system_metrics():
    """Métriques hardware temps réel pour le HUD (JSON)."""
    return _collect_system_metrics()


@app.get("/metrics")
def prometheus_metrics():
    """Exposition Prometheus des métriques hardware (host + GPU) pour le scrape."""
    from fastapi.responses import PlainTextResponse
    m = _collect_system_metrics()
    out: list[str] = []

    def gauge(name: str, val, help_: str):
        if val is None:
            return
        out.append(f"# HELP {name} {help_}")
        out.append(f"# TYPE {name} gauge")
        out.append(f"{name} {val}")

    gauge("nexus_cpu_percent",      m["cpu"],           "Host CPU usage percent")
    gauge("nexus_ram_percent",      m["ram"],           "Host RAM usage percent")
    gauge("nexus_storage_percent",  m["storage"],       "Host storage usage percent (C:)")
    gauge("nexus_vram_percent",     m["vram"],          "GPU VRAM usage percent")
    gauge("nexus_vram_used_mb",     m["vram_used_mb"],  "GPU VRAM used (MB)")
    gauge("nexus_vram_total_mb",    m["vram_total_mb"], "GPU VRAM total (MB)")
    gauge("nexus_gpu_util_percent", m["gpu_util"],      "GPU utilization percent")
    gauge("nexus_network_mbps",     m["network_mbps"],  "Host network throughput (MB/s)")
    gauge("nexus_health_score",     m["health_score"],  "Composite system health score (0-100)")

    return PlainTextResponse("\n".join(out) + "\n",
                             media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/api/digest")
def api_digest():
    return {
        "summary":       "OpenJarvis Nexus en ligne.",
        "alerts":        [],
        "agents_active": len([j for j in _crew_jobs.values() if j["status"] == "running"]),
        "timestamp":     int(time.time()),
    }

# ── Kokoro pipeline cache (un par lang_code, chargé une seule fois) ─────────
_kokoro_pipelines: dict = {}

def _get_kokoro_pipeline(lang_code: str):
    """Retourne le KPipeline mis en cache pour ce lang_code."""
    if lang_code not in _kokoro_pipelines:
        from kokoro import KPipeline
        _kokoro_pipelines[lang_code] = KPipeline(lang_code=lang_code)
    return _kokoro_pipelines[lang_code]

def _run_kokoro_sync(text: str, tts_voice: str) -> bytes:
    """Inference Kokoro synchrone — à appeler via asyncio.to_thread()."""
    import numpy as np
    import soundfile as sf
    import io as _io
    lang_code = tts_voice[0] if tts_voice else "b"
    pipeline = _get_kokoro_pipeline(lang_code)
    chunks = []
    for _, _, audio in pipeline(text, voice=tts_voice, speed=1.0):
        chunks.append(audio)
    if not chunks:
        raise RuntimeError("Kokoro n'a produit aucun audio")
    full_audio = np.concatenate(chunks)
    buf = _io.BytesIO()
    sf.write(buf, full_audio, 24000, format="WAV")
    return buf.getvalue()


@app.get("/v1/tts")
async def text_to_speech(
    text: str = Query(..., description="Texte à lire"),
    voice: str = Query(None, description="Override voix (défaut: config.json)"),
    engine: str = Query(None, description="Override moteur: 'edge' ou 'kokoro' (défaut: config.json)"),
):
    """Synthèse vocale — Edge TTS (gratuit, cloud) ou Kokoro (local, offline)."""
    import asyncio
    from memory import load_config
    cfg = load_config().get("jarvis", {})

    tts_engine = engine or cfg.get("tts_engine", "edge")
    text = text[:4000].strip()   # Bug fix: limite portée à 4000 chars
    if not text:
        raise HTTPException(400, "Texte vide")

    # ── Kokoro (local, offline) ──────────────────────────────────────────────
    if tts_engine == "kokoro":
        tts_voice = voice or cfg.get("tts_voice_kokoro", "bm_george")
        try:
            import kokoro  # noqa: F401
            import soundfile  # noqa: F401
        except ImportError:
            raise HTTPException(503, "Kokoro non installé — lance: pip install kokoro soundfile")

        try:
            # Bug fix: asyncio.to_thread évite de bloquer l'event loop FastAPI
            audio_bytes = await asyncio.to_thread(_run_kokoro_sync, text, tts_voice)
        except RuntimeError as e:
            raise HTTPException(503, str(e))

        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=jarvis.wav"},
        )

    # ── Edge TTS (cloud Microsoft, gratuit) ─────────────────────────────────
    tts_voice = voice or cfg.get("tts_voice_edge", "fr-CA-JeanNeural")
    try:
        import edge_tts
    except ImportError:
        raise HTTPException(503, "edge-tts non installé — lance: pip install edge-tts")

    communicate = edge_tts.Communicate(text, tts_voice)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")  # NOSONAR
    tmp_path = tmp.name
    tmp.close()

    await communicate.save(tmp_path)

    async def stream_and_delete():
        try:
            with open(tmp_path, "rb") as f:  # NOSONAR
                while chunk := f.read(8192):
                    yield chunk
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return StreamingResponse(
        stream_and_delete(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=jarvis.mp3"},
    )


# ── Whisper local (faster-whisper, chargé une seule fois) ───────────────────
_whisper_model = None

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # "small" = bien meilleure précision que "base", ~2-4s sur CPU
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
        print("🎙 Whisper small chargé sur CPU (int8)")
    return _whisper_model


@app.get("/v1/speech/health")
async def speech_health():
    try:
        import faster_whisper  # noqa: F401
        return {"available": True, "backend": "faster-whisper-local"}
    except ImportError:
        return {"available": False, "backend": None, "error": "faster-whisper not installed"}


@app.post("/v1/speech/transcribe")
async def speech_transcribe(
    file: UploadFile = File(...),
    language: str | None = None,   # "fr" | "en" | None = auto-detect
):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(400, "Fichier audio vide")

    # Resolve language: explicit param > config > default "fr"
    # Forcing a language prevents auto-detect bugs like "allo" → Arabic "هلو"
    _cfg_lang = load_config().get("jarvis", {}).get("language", "Français")
    _lang_map  = {"Français": "fr", "French": "fr", "English": "en", "fr": "fr", "en": "en"}
    resolved_lang = language or _lang_map.get(_cfg_lang, "fr")

    suffix = ".webm"
    tmp_f  = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)  # NOSONAR
    tmp_f.write(audio_bytes)
    tmp_f.close()

    def _run(path: str):
        model = _get_whisper()
        segments, info = model.transcribe(
            path,
            language=resolved_lang,            # FIX: force language — prevents "allo"→"هلو"
            task="transcribe",
            beam_size=5,
            no_speech_threshold=0.6,           # ignore silence/background noise
            condition_on_previous_text=False,  # prevents hallucinated repetitions
            repetition_penalty=1.2,            # extra guard against echo loops
            temperature=0,                     # deterministic output
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text, info

    try:
        import asyncio
        import traceback
        loop = asyncio.get_running_loop()   # fix: get_event_loop() déprécié Python 3.10+
        try:
            text, info = await loop.run_in_executor(None, _run, tmp_f.name)
        except Exception as e:
            print(f"[SPEECH] Erreur transcription: {traceback.format_exc()}")
            raise HTTPException(500, f"Transcription échouée: {e}")
        return {
            "text":             text,
            "language":         info.language,
            "confidence":       float(info.language_probability),
            "duration_seconds": float(info.duration),
        }
    finally:
        try:
            os.unlink(tmp_f.name)
        except OSError:
            pass


@app.get("/v1/business/stats")
def business_stats():
    """Stats D3Dprintix — connecter Etsy API + n8n pour des vraies données."""
    etsy_key = os.getenv("ETSYPUBLIC_KEY", "")
    listings = 0
    sales    = 0.0
    tasks    = 0
    if etsy_key:
        try:
            import requests as _req
            r = _req.get(
                "https://api.etsy.com/v3/application/listings/active",
                headers={"x-api-key": etsy_key},
                params={"limit": 1},
                timeout=4,
            )
            if r.ok:
                listings = r.json().get("count", 0)
        except Exception:
            pass
    return {"listings": listings, "sales": sales, "tasks": tasks}


# ════════════════════════════════════════════════════════
# RAPPORTS — génération HTML + popup desktop
# ════════════════════════════════════════════════════════

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
os.makedirs(REPORTS_DIR, exist_ok=True)

_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#030609;color:#cce4ff;font-family:'Courier New',monospace;padding:32px;}}
h1{{color:#00c8ff;font-size:22px;letter-spacing:4px;margin-bottom:8px;text-shadow:0 0 14px rgba(0,200,255,.6);}}
.meta{{color:#3a5870;font-size:11px;letter-spacing:2px;margin-bottom:32px;}}
.section{{margin-bottom:28px;}}
.section h2{{color:#00ffaa;font-size:13px;letter-spacing:3px;margin-bottom:12px;border-bottom:1px solid rgba(0,255,170,.2);padding-bottom:6px;}}
.row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:12px;}}
.row .label{{color:#3a5870;}}
.row .value{{color:#cce4ff;font-weight:700;}}
.badge{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;letter-spacing:1px;}}
.ok{{background:rgba(0,255,170,.12);color:#00ffaa;border:1px solid rgba(0,255,170,.3);}}
.warn{{background:rgba(255,140,0,.12);color:#ff8c00;border:1px solid rgba(255,140,0,.3);}}
.err{{background:rgba(255,45,85,.12);color:#ff2d55;border:1px solid rgba(255,45,85,.3);}}
pre{{background:rgba(8,16,38,.8);padding:16px;border-radius:8px;font-size:11px;color:#00ffaa;border:1px solid rgba(0,255,170,.1);white-space:pre-wrap;word-break:break-word;}}
.footer{{margin-top:40px;color:#1e3040;font-size:10px;letter-spacing:2px;text-align:center;}}
</style></head>
<body>
<h1>⬡ {title}</h1>
<div class="meta">NEXUS X9 · {date} · David Arbour</div>
{body}
<div class="footer">GENERATED BY JARVIS · OPENJARVISNEXUS</div>
</body></html>"""


def _build_report_body(report_type: str, data: dict) -> str:
    rows = ""
    for k, v in data.items():
        badge = ""
        if isinstance(v, bool):
            cls = "ok" if v else "err"
            badge = f'<span class="badge {cls}">{"OK" if v else "FAIL"}</span>'
            v_str = badge
        elif isinstance(v, (int, float)):
            v_str = str(v)
        elif isinstance(v, list):
            v_str = "<pre>" + "\n".join(str(i) for i in v) + "</pre>"
        else:
            v_str = str(v)
        rows += f'<div class="row"><span class="label">{k.upper()}</span><span class="value">{v_str}</span></div>'

    return f'<div class="section"><h2>{report_type.upper()} REPORT</h2>{rows}</div>'


@app.post("/v1/reports/generate")
async def generate_report(request: Request):
    import datetime
    body        = await request.json()
    report_type = body.get("type", "system")
    title       = body.get("title", f"JARVIS Report — {report_type.upper()}")
    data        = body.get("data", {})
    notes       = body.get("notes", "")

    now      = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    date_disp= now.strftime("%Y-%m-%d %H:%M")
    filename = f"{date_str}_{report_type}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)

    # Contenu texte brut pour Notepad
    lines = [
        f"{'='*60}",
        f"  JARVIS — {title.upper()}",
        f"  {date_disp}  |  David Arbour",
        f"{'='*60}",
        "",
    ]
    for k, v in data.items():
        lines.append(f"  {k.upper():<20} {v}")
    if notes:
        lines += ["", f"{'─'*60}", "  NOTES", f"{'─'*60}", notes]
    lines += ["", f"{'='*60}", "  GENERATED BY JARVIS · OPENJARVISNEXUS", f"{'='*60}"]

    content = "\n".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:  # NOSONAR - small text report, sync write acceptable
        f.write(content)

    # Destination brain selon le type de rapport (plus OneDrive)
    import shutil
    from config import BRAIN_REPORTS_DIR
    if report_type == "status":
        brain_dir = str(BRAIN_REPORTS_DIR / "status")
    elif report_type == "memory":
        brain_dir = str(BRAIN_REPORTS_DIR / "memory")
    else:
        brain_dir = str(BRAIN_REPORTS_DIR)
    os.makedirs(brain_dir, exist_ok=True)
    brain_path = os.path.join(brain_dir, filename)
    shutil.copy2(filepath, brain_path)
    subprocess.Popen(["notepad.exe", brain_path])  # NOSONAR - fire-and-forget GUI launch

    return {"filename": filename, "filepath": filepath, "title": title}


@app.get("/v1/reports")
def list_reports():
    files = []
    for f in sorted(os.listdir(REPORTS_DIR), reverse=True)[:20]:
        if f.endswith(".txt"):
            files.append({"filename": f, "filepath": os.path.join(REPORTS_DIR, f)})
    return {"reports": files}


@app.get("/v1/sources")
def sources_list():
    return {"sources": []}

@app.get("/v1/logs")
def logs_list():
    return {"logs": []}

@app.get("/v1/models")
def models_list():
    # Embedding / non-chat models — never appear in the chat model picker
    _EMBED_SKIP = re.compile(
        r"(embed|embedding|vision-only|clip|rerank|bge-|e5-|nomic-embed|all-minilm)",
        re.I,
    )
    models = [{"id": CLAUDE_MODEL,      "provider": "anthropic", "available": True}]
    # Add Sonnet only if user hasn't run out of credits (budget guard)
    if _budget_ok():
        models.append({"id": CLAUDE_MODEL_GROS, "provider": "anthropic", "available": True})
    if is_ollama_available():
        for m in list_local_models():
            if not _EMBED_SKIP.search(m):   # skip embedding / non-chat models
                models.append({"id": m, "provider": "ollama", "available": True})
    return {"models": models}

@app.get("/v1/managed-agents")
def managed_agents():
    return {"agents": []}

# ════════════════════════════════════════════════════════
# ROUTES AGENTS
# ════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════
# /task — PIPELINE MULTI-AGENTS
# ════════════════════════════════════════════════════════

OPENHANDS_URL = os.getenv("OPENHANDS_URL", "http://localhost:3000")

AGENT_SYSTEM_PROMPTS = {
    "ULTRON": (
        "Tu es ULTRON, agent d'analyse stratégique de NexusX9. "
        "Modèle: Claude Sonnet 4-6. "
        "Tu analyses en profondeur, tu planifies, tu structures. "
        "Réponds en français. Sois précis et exhaustif."
    ),
    "QWEN": (
        "Tu es QWEN, agent d'exécution masse de NexusX9. "
        "Modèle: Ollama qwen3:14b local. "
        "Tu génères du contenu en volume, tu traites des données, tu résumes. "
        "Réponds en français. Sois efficace et concis."
    ),
    "CORTANA": (
        "Tu es CORTANA, agent ingénierie de NexusX9. "
        "Modèle: deepseek-coder:6.7b. "
        "Tu écris du code Python/FastAPI/React/TypeScript COMPLET et fonctionnel. "
        "Toujours livrer le code entier, jamais partiel. Commentaires en français."
    ),
    "JARVIS": (
        "Tu es JARVIS, orchestrateur de NexusX9. "
        "Modèle: Claude Haiku 4-5. "
        "Réponds en anglais, style Iron Man JARVIS. Ultra-concis. Commence par ⬡."
    ),
}

async def _run_ultron(task: str) -> dict:
    """ULTRON — Claude Sonnet 4-6."""
    try:
        resp = claude.messages.create(
            model=CLAUDE_MODEL_GROS,
            max_tokens=4096,
            temperature=0.7,
            system=AGENT_SYSTEM_PROMPTS["ULTRON"],
            messages=[{"role": "user", "content": task}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        _enregistrer_cout(
            resp.usage.input_tokens + resp.usage.output_tokens, CLAUDE_MODEL_GROS,
            input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
        )
        return {"ok": True, "agent": "ULTRON", "model": CLAUDE_MODEL_GROS, "result": text}
    except Exception as e:
        return {"ok": False, "agent": "ULTRON", "error": str(e)}

async def _run_qwen(task: str) -> dict:
    """QWEN — Ollama qwen3:14b."""
    try:
        msgs = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPTS["QWEN"]},
            {"role": "user",   "content": task},
        ]
        text = ask_ollama_chat(msgs, OLLAMA_MODEL)
        _budget["appels_ollama"] += 1
        budget_tracker.record_ollama_call()
        if text is None:
            # ask_ollama_chat retourne None sur timeout — message propre
            return {"ok": False, "agent": "QWEN", "error": "Ollama timeout — QWEN ne répond pas (>60s). Vérifie que Ollama tourne: 1_OLLAMA.bat"}
        return {"ok": True, "agent": "QWEN", "model": OLLAMA_MODEL, "result": text or "Pas de réponse Ollama."}
    except httpx.TimeoutException:
        return {"ok": False, "agent": "QWEN", "error": "Ollama timeout — QWEN ne répond pas. Relance Ollama via 1_OLLAMA.bat"}
    except Exception as e:
        return {"ok": False, "agent": "QWEN", "error": str(e)}

async def _run_cortana(task: str) -> dict:
    """CORTANA — deepseek-coder:6.7b."""
    try:
        msgs = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPTS["CORTANA"]},
            {"role": "user",   "content": task},
        ]
        text = ask_ollama_chat(msgs, "deepseek-coder:6.7b")
        _budget["appels_ollama"] += 1
        budget_tracker.record_ollama_call()
        if text is None:
            # ask_ollama_chat retourne None sur timeout — message propre
            return {"ok": False, "agent": "CORTANA", "error": "Ollama timeout — CORTANA ne répond pas (>60s). Vérifie que Ollama tourne: 1_OLLAMA.bat"}
        return {"ok": True, "agent": "CORTANA", "model": "deepseek-coder:6.7b", "result": text or "Pas de réponse CORTANA."}
    except httpx.TimeoutException:
        return {"ok": False, "agent": "CORTANA", "error": "Ollama timeout — CORTANA ne répond pas. Relance Ollama via 1_OLLAMA.bat"}
    except Exception as e:
        return {"ok": False, "agent": "CORTANA", "error": str(e)}

async def _run_bruce(task: str) -> dict:
    """BRUCE — OpenHands autonome — utilise le client HTTP partagé."""
    if _http is None:
        return {"ok": False, "agent": "BRUCE", "error": "Client HTTP non initialisé — backend pas encore prêt."}
    try:
        r = await _http.post(
            f"{OPENHANDS_URL}/api/conversations",
            json={"initial_user_msg": task},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            return {"ok": False, "agent": "BRUCE", "error": f"OpenHands HTTP {r.status_code}. Lance: docker start nexus_bruce"}
        data = r.json()
        conv_id = data.get("conversation_id") or data.get("id") or "?"
        _agents_status["BRUCE"] = "active"
        return {
            "ok":      True,
            "agent":   "BRUCE",
            "model":   "OpenHands + qwen3:14b",
            "conv_id": conv_id,
            "result":  f"⬡ BRUCE mission launched — conversation {conv_id}.\nMonitor: {OPENHANDS_URL}\nTask: {task[:120]}",
        }
    except httpx.ConnectError:
        return {"ok": False, "agent": "BRUCE", "error": "BRUCE offline. Lance: docker start nexus_bruce"}
    except Exception as e:
        return {"ok": False, "agent": "BRUCE", "error": str(e)}

async def _run_jarvis(task: str) -> dict:
    """JARVIS — Claude Haiku, routing par défaut."""
    # Récupère le contexte Vault pertinent
    vault_context = ""
    try:
        from vault.memory_manager import vault_query
        memories = await vault_query(task, collections=["orchestration", "workflows", "conversations"])
        if memories:
            vault_context = "\n\nVault Context (relevant memories):\n" + "\n".join(
                f"- [{m['collection']}] {m['text'][:150]}" for m in memories[:3]
            )
    except Exception:
        pass

    # Ajoute le contexte au message si disponible
    enriched_task = task + vault_context if vault_context else task

    try:
        resp = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            temperature=0.3,
            system=AGENT_SYSTEM_PROMPTS["JARVIS"],
            messages=[{"role": "user", "content": enriched_task}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        _enregistrer_cout(
            resp.usage.input_tokens + resp.usage.output_tokens, CLAUDE_MODEL,
            input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
        )

        # Sauvegarde dans Vault conversations
        try:
            from vault.memory_manager import add_memory
            await add_memory("conversations",
                f"User: {task}\nJARVIS: {text}",
                metadata={"agent": "JARVIS", "model": CLAUDE_MODEL}
            )
        except Exception:
            pass

        return {"ok": True, "agent": "JARVIS", "model": CLAUDE_MODEL, "result": text}
    except Exception as e:
        return {"ok": False, "agent": "JARVIS", "error": str(e)}

class TaskRequest(BaseModel):
    agent: str = "JARVIS"
    task: str

@app.post("/task")
async def run_task(data: TaskRequest):
    """Pipeline multi-agents — route vers JARVIS/ULTRON/QWEN/CORTANA/BRUCE.
    Retourne toujours {"ok": bool, "result": str, "error": str|null} — jamais de 500 brut.
    """
    try:
        agent = data.agent.upper().strip()
        task  = data.task.strip()
        if not task:
            return {"ok": False, "result": "", "error": "task vide"}

        if agent not in _agents_status:
            _agents_status[agent] = "idle"
        _agents_status[agent] = "active"
        result: dict = {}
        try:
            if   agent == "BRUCE":   result = await _run_bruce(task)
            elif agent == "ULTRON":  result = await _run_ultron(task)
            elif agent == "QWEN":    result = await _run_qwen(task)
            elif agent == "CORTANA": result = await _run_cortana(task)
            else:                    result = await _run_jarvis(task)
        finally:
            _agents_status[agent] = "idle" if agent != "BRUCE" else _agents_status.get("BRUCE", "idle")

        # Vault orchestration log
        try:
            from vault.memory_manager import add_memory
            await add_memory("orchestration",
                f"Agent: {agent} | Task: {task[:200]} | Result: {result.get('result','')[:200]}",
                metadata={"agent": agent, "ok": str(result.get("ok", False))}
            )
        except Exception:
            pass

        # Normalise la réponse — toujours {ok, result, error}
        return {
            "ok":     result.get("ok", False),
            "result": result.get("result", ""),
            "error":  result.get("error", None),
            # Champs supplémentaires passés tels quels
            **{k: v for k, v in result.items() if k not in ("ok", "result", "error")},
        }

    except Exception as exc:
        _log_error_500("/task", exc)
        return {"ok": False, "result": "", "error": f"Erreur interne: {type(exc).__name__}: {exc}"}


@app.get("/v1/budget")
def get_budget():
    stats = budget_tracker.get_stats()
    stats["session"] = {
        "cost_usd":     round(_budget["cout_usd"], 6),
        "calls_claude": _budget["appels_claude"],
        "calls_ollama": _budget["appels_ollama"],
    }
    stats["budget_max"] = BUDGET_MAX_USD
    stats["budget_remaining"] = round(BUDGET_MAX_USD - _budget["cout_usd"], 6)
    return stats


@app.get("/v1/agents")
def agents_list():
    ollama_ok = is_ollama_available()
    bruce_url = os.getenv("OPENHANDS_URL", "http://localhost:3000")
    try:
        import httpx
        bruce_ok = httpx.get(f"{bruce_url}/api/options/models", timeout=2).status_code == 200
    except Exception:
        bruce_ok = False

    return {"agents": [
        # ── Hiérarchie principale ──────────────────────────────
        {
            "id":          "jarvis",
            "name":        "JARVIS",
            "provider":    "claude",
            "model":       CLAUDE_MODEL,
            "role":        "Orchestrateur central",
            "description": "Claude Haiku 4-5 — orchestre tous les agents, routing intelligent.",
            "status":      _agents_status.get("JARVIS", "online"),
        },
        {
            "id":          "ultron",
            "name":        "ULTRON",
            "provider":    "claude",
            "model":       CLAUDE_MODEL_GROS,
            "role":        "Analyse complexe & Décisions",
            "description": "Claude Sonnet 4-6 — raisonnement avancé, architecture, stratégie.",
            "status":      _agents_status.get("ULTRON", "idle"),
        },
        {
            "id":          "kaizen",
            "name":        "KAIZEN",
            "provider":    "meshy+local",
            "model":       "Meshy AI + trimesh + pymeshfix",
            "role":        "Ingénieur 3D — Fabrication",
            "description": "Meshy AI génère OBJ/STL. BRUCE (pymeshfix) répare. watertight garanti avant Bambu.",
            "status":      _agents_status.get("KAIZEN", "idle"),
        },
        {
            "id":          "qwen",
            "name":        "QWEN",
            "provider":    "ollama",
            "model":       OLLAMA_MODEL,
            "role":        "Intelligence générale & Recherche",
            "description": "Ollama qwen3:14b — tâches générales, recherche, analyse. Local & gratuit.",
            "status":      _agents_status.get("QWEN", "idle") if ollama_ok else "offline",
        },
        {
            "id":          "cortana",
            "name":        "CORTANA",
            "provider":    "ollama",
            "model":       "deepseek-coder:6.7b",  # TOUJOURS
            "role":        "Développement & Automatisation",
            "description": "deepseek-coder:6.7b — Python, FastAPI, React, scripts. Code complet toujours.",
            "status":      _agents_status.get("CORTANA", "idle") if ollama_ok else "offline",
        },
        {
            "id":          "bruce",
            "name":        "BRUCE",
            "provider":    "openhands",
            "model":       "qwen3:14b",  # TOUJOURS
            "role":        "Agent Autonome OpenHands",
            "description": "OpenHands + qwen3:14b — exécution autonome, lecture/écriture fichiers, git.",
            "status":      "active" if bruce_ok else _agents_status.get("BRUCE", "offline"),
        },
        # ── Agents STL Pipeline ────────────────────────────────
        {
            "id":          "stl_blender",
            "name":        "Blender Agent",
            "provider":    "mixed",
            "model":       OLLAMA_MODEL,
            "role":        "3D Generation & Repair",
            "description": "Meshy AI / Blender — génération STL, repair, simplification, export Bambu.",
            "status":      "idle",
        },
        {
            "id":          "stl_concept",
            "name":        "Concept Agent",
            "provider":    "claude",
            "model":       CLAUDE_MODEL,
            "role":        "Design & 3D Specifications",
            "description": "Brief technique low-poly fantasy, contraintes FDM, dimensions 15cm.",
            "status":      "idle",
        },
        {
            "id":          "stl_optim",
            "name":        "Optimizer",
            "provider":    "ollama",
            "model":       OLLAMA_MODEL,
            "role":        "Print Quality Audit",
            "description": "Scale 15cm, overhang map, printability score.",
            "status":      "idle",
        },
        {
            "id":          "stl_files",
            "name":        "File Manager",
            "provider":    "ollama",
            "model":       OLLAMA_MODEL,
            "role":        "STL Conversion & Validation",
            "description": "trimesh, pymeshfix, validation manifold, handoff Bambu Studio.",
            "status":      "idle",
        },
        {
            "id":          "stl_research",
            "name":        "Researcher",
            "provider":    "ollama",
            "model":       OLLAMA_MODEL,
            "role":        "STL Trends Intelligence",
            "description": "Rapport quotidien 21h — Thingiverse, Cults3D, Etsy top STL.",
            "status":      "idle",
        },
        # ── Business ───────────────────────────────────────────
        {
            "id":          "etsy",
            "name":        "Etsy Agent",
            "provider":    "claude",
            "model":       CLAUDE_MODEL,
            "role":        "Boutique D3Dprintix",
            "description": "Listings, SEO, images, pricing via n8n + Claude.",
            "status":      "idle",
        },
    ]}

@app.post("/v1/agents/{agent_name}/enable")
def enable_agent(agent_name: str):
    _agents_status[agent_name] = "active"
    print(f"[agent] ✅ {agent_name} activé")
    return {"ok": True, "agent": agent_name, "status": "active"}

@app.post("/v1/agents/{agent_name}/disable")
def disable_agent(agent_name: str):
    _agents_status[agent_name] = "idle"
    print(f"[agent] ⏸️  {agent_name} désactivé")
    return {"ok": True, "agent": agent_name, "status": "idle"}

@app.get("/v1/agents/{agent_name}/status")
def agent_status(agent_name: str):
    status = _agents_status.get(agent_name, "unknown")
    return {"agent": agent_name, "status": status}

# ════════════════════════════════════════════════════════
# ROUTES MÉMOIRE
# ════════════════════════════════════════════════════════

@app.get("/v1/memory")
def get_memory():
    return {"facts": load_facts(), "sessions": list_sessions()}

@app.post("/v1/memory/facts")
def update_facts(update: FactsUpdate):
    facts = load_facts()
    if update.user_name   is not None: facts["user_name"]   = update.user_name
    if update.full_name   is not None: facts["full_name"]   = update.full_name
    if update.location    is not None: facts["location"]    = update.location
    if update.projects    is not None: facts["projects"]    = update.projects
    if update.preferences is not None: facts["preferences"] = update.preferences
    if update.tech_stack  is not None: facts["tech_stack"]  = update.tech_stack
    if update.goals       is not None: facts["goals"]       = update.goals
    if update.notes       is not None: facts["notes"]       = update.notes
    save_facts(facts)
    return {"ok": True, "facts": facts}

@app.post("/v1/memory/note")
def add_note(body: dict):
    note = body.get("note", "")
    if not note:
        raise HTTPException(400, "Champ 'note' requis")
    facts = load_facts()
    facts.setdefault("notes", []).append(note)
    save_facts(facts)
    return {"ok": True, "notes": facts["notes"]}

@app.delete("/v1/memory/session/{session_id}")
def clear_session_route(session_id: str):
    clear_session(session_id)
    return {"ok": True, "cleared": session_id}

@app.delete("/v1/memory/facts")
def clear_facts():
    save_facts({
        "user_name": None, "projects": [], "preferences": [],
        "notes": [], "updated_at": None,
    })
    return {"ok": True}

# ════════════════════════════════════════════════════════
# ROUTES CREWAI
# ════════════════════════════════════════════════════════

@app.post("/v1/crew/run")
def run_crew_endpoint(req: CrewRequest, background: BackgroundTasks):
    job_id = f"crew_{int(time.time())}"
    _crew_jobs[job_id] = {
        "id":         job_id,
        "mission":    req.mission,
        "status":     "running",
        "started_at": time.time(),
        "result":     None,
    }

    def _run():
        try:
            from crew_factory import run_crew
            result = run_crew(req.mission, req.mission_type)
            _crew_jobs[job_id].update({
                "status":   "done",
                "result":   result,
                "ended_at": time.time(),
            })
        except Exception as e:
            _crew_jobs[job_id].update({
                "status":   "failed",
                "error":    str(e),
                "ended_at": time.time(),
            })
            print(f"[crew] erreur: {e}")

    background.add_task(_run)
    timeout = 300
    start   = time.time()
    while _crew_jobs[job_id]["status"] == "running":
        if time.time() - start > timeout:
            return {"error": "Timeout — crew trop long"}
        time.sleep(1)

    return _crew_jobs[job_id].get("result", {"error": _crew_jobs[job_id].get("error")})

@app.get("/v1/crew/jobs")
def list_crew_jobs():
    return {"jobs": list(_crew_jobs.values())}

@app.get("/v1/crew/jobs/{job_id}")
def get_crew_job(job_id: str):
    job = _crew_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Mission non trouvée")
    return job

# ════════════════════════════════════════════════════════
# CHAT PRINCIPAL
# ════════════════════════════════════════════════════════

_MEM_MIN_CHARS = 140
_DEBUG_KEYWORDS = (
    "debug", "erreur", "error", "bug", "traceback", "exception",
    "stack trace", "stacktrace", "crash", "plante", "marche pas",
    "fails", "failing", "not working",
)

# Docker keyword detector — triggers tool injection in Claude / status injection in Ollama
_DOCKER_KW = re.compile(
    r"\b(docker|container|compose|chromadb|postgres|redis|traefik|nexus_\w+)\b"
    r"|quel\s+(service|container)|les?\s+containers?|est[- ]ce\s+que\s+docker"
    r"|restart\s+\w+|stop\s+\w+container|start\s+\w+container"
    r"|logs?\s+(du\s+)?(container|service)",
    re.I,
)


def _needs_memory(msg: str) -> bool:
    """Déclenche l'injection brain/vault : message long, complexe, ou debug."""
    m = (msg or "").strip()
    if len(m) > _MEM_MIN_CHARS:
        return True
    if should_use_claude(m):
        return True
    low = m.lower()
    return any(k in low for k in _DEBUG_KEYWORDS)


@app.post("/v1/chat/completions")
def chat_completion(req: ChatRequest, request: Request):
    session_id = _get_session_id(req, request)

    # ── Session continuity — capturer AVANT add_message ──────
    _was_new_session = is_new_session(session_id)

    if req.messages:
        new_msgs = [
            {"role": m.role, "content": m.content}
            for m in req.messages
            if m.role in ("user", "assistant") and m.content.strip()  # skip empty-content (aborted stream placeholders)
        ]
        last_user = next(
            (m["content"] for m in reversed(new_msgs) if m["role"] == "user"),
            None
        )
        if last_user:
            add_message(session_id, "user", last_user)
        anthropic_messages = new_msgs

    elif req.message:
        add_message(session_id, "user", req.message)
        anthropic_messages = get_history(session_id)

    else:
        raise HTTPException(422, "Fournir 'message' ou 'messages'")

    last_user_msg = next(
        (m["content"] for m in reversed(anthropic_messages) if m["role"] == "user"),
        ""
    )

    # Detect whether this message is about Docker / containers
    _needs_docker = bool(_DOCKER_KW.search(last_user_msg))

    # ── Shortcut Docker STATUS — bypass LLM entièrement ─────
    # Si la question concerne l'affichage/liste des containers (pas une action start/stop/restart),
    # on formate la réponse directement depuis l'API Docker sans passer par Claude ou Ollama.
    _DOCKER_SHOW_KW = re.compile(
        r"\b(montre|liste|affiche|show|donne|quels?|combien|ps|status|statut|état|voir|check|ping)\b"
        r"|\bup\b|\bdown\b|\brunning\b",
        re.I,
    )
    _DOCKER_ACTION_KW = re.compile(
        r"\b(restart|redémarre|stop|arrête|start|démarre|lance|kill|rm|remove)\b", re.I
    )
    if _needs_docker and _DOCKER_SHOW_KW.search(last_user_msg) and not _DOCKER_ACTION_KW.search(last_user_msg):
        try:
            from tools.docker_tools import docker_status as _ds
            _dstat = _ds()
            if _dstat["ok"]:
                _up   = _dstat["up"]
                _tot  = _dstat["total"]
                _rows = []
                for _c in _dstat["containers"]:
                    _state = "UP  " if _c["running"] else "DOWN"
                    _name  = _c["name"].replace("nexus_", "")
                    # Ports : seulement les ports hote (ex: [8000, 5173])
                    _raw_ports = _c.get("ports", "") or ""
                    _plist = []
                    for _pp in _raw_ports.split(","):
                        _pp = _pp.strip()
                        if "->" in _pp:
                            _hp = _pp.split("->")[0].split(":")[-1]
                            if _hp and _hp not in _plist:
                                _plist.append(_hp)
                    _ports = f"  [{', '.join(_plist)}]" if _plist else ""
                    # Status : sans les parens de sante
                    _st = _c["status"].split("(")[0].strip()
                    _rows.append(f"  {_state}  {_name:<20}{_st}{_ports}")
                _docker_resp = f"{_up}/{_tot} containers en ligne.\n\n" + "\n".join(_rows)
            else:
                _docker_resp = f"Docker inaccessible : {_dstat.get('error', '?')}"
        except Exception as _de:
            _docker_resp = f"Erreur Docker : {_de}"
        add_message(session_id, "assistant", _docker_resp)
        _dreq_id = f"chatcmpl-docker-{int(time.time())}"
        # Le frontend envoie toujours stream=True — on retourne du SSE
        if req.stream:
            return StreamingResponse(
                _stream_text(_docker_resp, "docker-direct", _dreq_id),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return {
            "id":      _dreq_id,
            "object":  "chat.completion",
            "model":   "docker-direct",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": _docker_resp}, "finish_reason": "stop"}],
            "usage":   {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    # ── Shortcut SKILLS — liste directe sans LLM ─────────────
    _SKILL_LIST_KW = re.compile(
        r"\bskill?s?\b|skils?\b|comp[eé]tences?\b|capacit[eé]s?\b|\bsavoir-faire\b|\bprocédures?\b",
        re.I,
    )
    _SKILL_LIST_SHOW_KW = re.compile(
        r"\b(liste|list|montre|affiche|show|quels?|quelles?|donne|voir|dis.?moi|what|have|got|as-tu|avez)\b",
        re.I,
    )
    _skill_msg_short = len(last_user_msg.strip().split()) <= 4
    if _SKILL_LIST_KW.search(last_user_msg) and (
        _SKILL_LIST_SHOW_KW.search(last_user_msg) or _skill_msg_short
    ):
        try:
            from tools.skill_tools import skill_list as _sl
            _sdata = _sl()
            if _sdata["ok"] and _sdata["total"] > 0:
                _slines = [f"{_sdata['total']} skills installées :"]
                for _sk in _sdata["skills"]:
                    _slines.append(f"  {_sk['name']} — {_sk['description']}")
                _skill_resp = "\n".join(_slines)
            else:
                _skill_resp = "Aucune skill installée."
        except Exception as _se:
            _skill_resp = f"Erreur lecture skills : {_se}"
        add_message(session_id, "assistant", _skill_resp)
        _sreq_id = f"chatcmpl-skill-{int(time.time())}"
        if req.stream:
            return StreamingResponse(
                _stream_text(_skill_resp, "skill-direct", _sreq_id),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return {
            "id": _sreq_id, "object": "chat.completion", "model": "skill-direct",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": _skill_resp}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    # ── Shortcut JARVIS: RUN CHEAT CODE ─────────────────────
    if "jarvis" in last_user_msg.lower() and "cheat" in last_user_msg.lower():
        import asyncio as _asyncio
        from pipeline_runner import run_cheat_code
        try:
            report = _asyncio.run(run_cheat_code(voice=True))
        except Exception as _e:
            report = {"status": "error", "error": str(_e), "agents": {"online": 0, "total": 0, "details": []}, "pipelines": {}}
        agents_ok    = report["agents"]["online"]
        agents_total = report["agents"]["total"]
        vault_info   = report.get("vault", {})
        total_mems   = vault_info.get("total_memories", 0)
        eco          = report.get("ecosystem", {})
        eco_score    = eco.get("score", "—")
        eco_grade    = eco.get("grade", "—")
        daily_info   = report.get("daily_tasks", {})
        cheat_text   = (
            f"⚡ **CHEAT CODE ULTIME ACTIVÉ**\n\n"
            f"**Agents :** {agents_ok}/{agents_total} en ligne\n"
            + "".join(
                f"- {'✅' if a['ok'] else '❌'} {a['agent']}\n"
                for a in report["agents"]["details"]
            )
            + f"\n**Ecosystem :** {eco_score}/100 Grade {eco_grade}\n"
            + f"**Daily tasks :** {daily_info.get('passed','?')}/{daily_info.get('total','?')} OK\n"
            + f"**Vault :** {total_mems} mémoires · {'✅' if report.get('vault_id') else '⚠️ hors ligne'}\n"
            + f"**Statut :** {report['status'].upper()}\n\n"
            + "*Notification vocale envoyée.*"
        )
        add_message(session_id, "assistant", cheat_text)
        return {
            "id":      f"chatcmpl-cheat-{int(time.time())}",
            "object":  "chat.completion",
            "model":   "cheat-code",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": cheat_text}, "finish_reason": "stop"}],
            "usage":   {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    # ── Pipelines : START ALL · DAILY RESEARCH · RAPPORT · STL ──
    from pipeline_runner import detect_pipeline, execute_pipeline, format_response as _fmt_pipe
    _pipe = detect_pipeline(last_user_msg)
    if _pipe:
        import asyncio as _asyncio2
        _pipe_id, _pipe_arg = _pipe
        try:
            _result = _asyncio2.run(execute_pipeline(_pipe_id, _pipe_arg, voice=True))
        except Exception as _pe:
            _result = {"ok": False, "error": str(_pe)}
        _pipe_text = _fmt_pipe(_pipe_id, _result)
        add_message(session_id, "assistant", _pipe_text)
        return {
            "id":      f"chatcmpl-pipe-{int(time.time())}",
            "object":  "chat.completion",
            "model":   f"pipeline:{_pipe_id}",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": _pipe_text}, "finish_reason": "stop"}],
            "usage":   {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    ollama_available = is_ollama_available()

    # Si le JSON spécifie un modèle Ollama → forcer Ollama
    if req.model and ("qwen" in req.model or "llama" in req.model or "deepseek" in req.model):
        use_claude = False
    # Si le JSON spécifie un modèle Claude → forcer Claude
    elif req.model and "claude" in req.model:
        use_claude = True
    else:
        use_claude = should_use_claude(last_user_msg) or not ollama_available

    facts      = load_facts()
    system     = build_system_prompt(req.system or _build_base_system(), facts)  # relit config.json à chaque requête (TTL 30s)

    # ── Session continuity — inject résumé si nouvelle session ──
    _sc_cfg = load_config().get("session_continuity", {})
    if _was_new_session and _sc_cfg.get("inject_on_new_session", True):
        _prev_summary = get_last_session_summary(session_id)
        if _prev_summary:
            system = (
                "━━━ REPRISE DE SESSION ━━━\n"
                + _prev_summary
                + "\n━━━ FIN DU RÉSUMÉ — continue naturellement ━━━\n\n"
            ) + system

    # ── Memory compression — déclenche si seuil atteint ─────────
    compress_session_sync(session_id)

    # Rappel langue injecté à la fin du system prompt — modèles suivent mieux la dernière instruction
    # Lu depuis config.json (cache TTL 30s) — jamais hardcodé
    _chat_lang = load_config().get("jarvis", {}).get("language", "Français")
    _lang_lc   = _chat_lang.lower()
    if "english" in _lang_lc or "anglais" in _lang_lc:
        system += "\n\n[MANDATORY] Reply in ENGLISH only. 1-2 sentences max unless detail is explicitly requested. Plain text, no markdown, no lists, no headers. ZERO emoji — never."
    else:
        system += f"\n\n[OBLIGATOIRE] Tu réponds UNIQUEMENT en {_chat_lang}. 1 à 2 phrases maximum sauf si détail explicitement demandé. Texte brut — pas de markdown, pas de listes, pas de titres. ZERO emoji — aucun, jamais."

    # ── Skills catalog — injection compacte dans le system prompt ───────────
    try:
        _skill_cat = _skill_catalog_text()
        if _skill_cat:
            system += f"\n\n{_skill_cat}"
    except Exception:
        pass

    # ── Brain/Vault contextuel (option 2 — triggers: long / complexe / debug) ──
    memory_meta = {"retrieved": False, "fragments": 0, "ms": 0, "confidence": 0}
    if _needs_memory(last_user_msg):
        import asyncio as _aio_mem, time as _t_mem
        _m0 = _t_mem.perf_counter()
        try:
            from vault.memory_manager import vault_query
            _hits = _aio_mem.run(vault_query(last_user_msg))[:5]
        except Exception:
            _hits = []
        if _hits:
            system += "\n\n[Memory Retrieved — brain & vault]\n" + "\n".join(
                f"- [{h.get('collection','?')}] {h['text'][:160]}" for h in _hits
            )
            _top = max((h.get("score", 0) for h in _hits), default=0)
            memory_meta = {
                "retrieved":  True,
                "fragments":  len(_hits),
                "ms":         round((_t_mem.perf_counter() - _m0) * 1000),
                "confidence": round(max(0.0, min(1.0, _top)) * 100),
            }

    req_id     = f"chatcmpl-{int(time.time())}"
    text       = ""
    model_used = ""

    # ── Ollama (gratuit) ─────────────────────────────────
    if not use_claude and ollama_available:
        print("[chat] OLLAMA — gratuit")
        _budget["appels_ollama"] += 1
        budget_tracker.record_ollama_call()
        model_used  = OLLAMA_MODEL
        # Docker context injection for Ollama (no native tool_use in Ollama)
        # Fetched once, injected in BOTH system prompt AND user message for maximum compliance
        _ollama_sys    = system
        _docker_block  = ""
        if _needs_docker:
            try:
                _docker_block = _docker_quick_status()
                _ollama_sys += (
                    "\n\n[DONNEES DOCKER EN TEMPS REEL]\n"
                    + _docker_block
                    + "\n\nUtilise ces donnees reelles pour repondre. "
                    "Ne dis jamais 'exécutez docker ps'. Ne dis jamais 'je ne peux pas acceder'. "
                    "Les donnees sont ici, utilise-les."
                )
            except Exception as _de:
                print(f"[docker] quick_status_text error: {_de}")

        # Pour Ollama : rappel aussi dans le dernier message utilisateur
        ollama_msgs_raw = [{"role": "system", "content": _ollama_sys}] + anthropic_messages
        # Ajoute le rappel langue + brièveté en fin de message user (Ollama suit mieux la dernière instruction)
        ollama_msgs = []
        for i, msg in enumerate(ollama_msgs_raw):
            if i == len(ollama_msgs_raw) - 1 and msg["role"] == "user":
                if "english" in _lang_lc or "anglais" in _lang_lc:
                    _tail = "[English only. 1-2 sentences MAX. No markdown, no lists, no headers, no emoji.]"
                else:
                    _tail = f"[{_chat_lang} uniquement. MAX 2 phrases courtes. Texte brut, zéro markdown, zéro liste, zéro titre, ZERO emoji.]"
                # Si Docker requis : injecte les données directement dans le message user
                if _needs_docker and _docker_block:
                    _docker_inject = (
                        f"\n\n[Données Docker réelles]\n{_docker_block}\n"
                        "Réponds en utilisant ces données. Ne suggère jamais d'exécuter une commande."
                    )
                    ollama_msgs.append({"role": "user", "content": msg["content"] + _docker_inject + f"\n\n{_tail}"})
                else:
                    ollama_msgs.append({"role": "user", "content": msg["content"] + f"\n\n{_tail}"})
            else:
                ollama_msgs.append(msg)

        # ── Real streaming path — tokens arrive live, no 60s freeze ──────
        if req.stream:
            def _ollama_real_stream():
                full_text = ""
                _rid = req_id
                _mid = model_used
                _mem = memory_meta
                _sid = session_id
                # opening delta (role)
                yield _sse({
                    "id": _rid, "object": "chat.completion.chunk",
                    "model": _mid,
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}],
                })
                for _chunk in stream_ollama_chat(ollama_msgs, OLLAMA_MODEL):
                    full_text += _chunk
                    yield _sse({
                        "id": _rid, "object": "chat.completion.chunk",
                        "model": _mid,
                        "choices": [{"index": 0, "delta": {"content": _chunk}, "finish_reason": None}],
                    })
                # Fallback si Ollama retourne rien (crash / think-only / timeout)
                if not full_text.strip():
                    full_text = "Réponds à cette question." if False else (
                        ask_ollama_chat(
                            [{"role": "user", "content": last_user_msg}],
                            OLLAMA_MODEL,
                        ) or ""
                    )
                    if full_text:
                        full_text = strip_think_tags(full_text)
                        yield _sse({
                            "id": _rid, "object": "chat.completion.chunk",
                            "model": _mid,
                            "choices": [{"index": 0, "delta": {"content": full_text}, "finish_reason": None}],
                        })
                    else:
                        full_text = "Modele local indisponible. Relance Ollama ou utilise !claude."
                        yield _sse({
                            "id": _rid, "object": "chat.completion.chunk",
                            "model": _mid,
                            "choices": [{"index": 0, "delta": {"content": full_text}, "finish_reason": None}],
                        })
                # final chunk + [DONE]
                _final = {
                    "id": _rid, "object": "chat.completion.chunk",
                    "model": _mid,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                if _mem:
                    _final["memory"] = _mem
                yield _sse(_final)
                yield "data: [DONE]\n\n"
                # Persist to session after stream completes
                if full_text:
                    add_message(_sid, "assistant", full_text)
                    print(f"[chat] ollama-stream modèle={_mid} '{full_text[:50]}...'")
                else:
                    print("[chat] ollama-stream — pas de réponse")

            return StreamingResponse(
                _ollama_real_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control":     "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection":        "keep-alive",
                },
            )

        # ── Non-streaming path — collect full response, strip think tags ─
        text = ask_ollama_chat(ollama_msgs, OLLAMA_MODEL)
        if text:
            text = strip_think_tags(text)  # Remove <think>...</think> from qwen3/deepseek-r1
        if not text:
            use_claude = True

    # ── Claude (payant) ──────────────────────────────────
    if use_claude or not text:
        if not _budget_ok():
            text       = (
                f"🛑 Budget ${BUDGET_MAX_USD} atteint "
                f"(${_budget['cout_usd']:.3f} dépensé). "
                "Redémarre le backend pour continuer."
            )
            model_used = "bloqué"
        else:
            _auto_model = get_claude_model(last_user_msg, CLAUDE_MODEL, CLAUDE_MODEL_GROS)
            model_used  = (req.model if req.model and req.model.strip() else _auto_model)
            _tag = "SONNET" if model_used == CLAUDE_MODEL_GROS else "HAIKU"
            print(f"[chat] 🔵 CLAUDE {_tag} — routing auto")
            try:
                _docker_tools = _DOCKER_TOOL_DEFS if _needs_docker else []
                _all_tools    = _docker_tools + _SKILL_TOOL_DEFS
                _tool_msgs    = list(anthropic_messages)  # working copy for tool loop
                _total_in, _total_out = 0, 0

                while True:
                    _create_kw = dict(
                        model=model_used,
                        max_tokens=req.max_tokens,
                        temperature=req.temperature,
                        system=system,
                        messages=_tool_msgs,
                    )
                    if _all_tools:
                        _create_kw["tools"] = _all_tools

                    resp = claude.messages.create(**_create_kw)
                    _total_in  += resp.usage.input_tokens
                    _total_out += resp.usage.output_tokens

                    if resp.stop_reason == "tool_use":
                        # Execute each tool call and collect results
                        _tool_results = []
                        for _blk in resp.content:
                            if getattr(_blk, "type", None) == "tool_use":
                                _tname = _blk.name
                                print(f"[tool] calling {_tname} {_blk.input}")
                                if _tname.startswith("skill_"):
                                    _res_str = _skill_dispatch(_tname, _blk.input)
                                else:
                                    _res_str = _docker_dispatch(_tname, _blk.input)
                                _tool_results.append({
                                    "type":        "tool_result",
                                    "tool_use_id": _blk.id,
                                    "content":     _res_str,
                                })
                        # Append assistant turn + tool results for next loop
                        _tool_msgs.append({"role": "assistant", "content": resp.content})
                        _tool_msgs.append({"role": "user",      "content": _tool_results})
                    else:
                        text = "".join(
                            b.text for b in resp.content
                            if getattr(b, "type", None) == "text"
                        )
                        break

                _enregistrer_cout(
                    _total_in + _total_out,
                    model_used,
                    input_tokens=_total_in,
                    output_tokens=_total_out,
                )
            except APIError as e:
                _sc  = getattr(e, "status_code", 502)
                _msg = str(e)
                # ── Crédit Anthropic épuisé → fallback Ollama + message clair ──
                _is_credit = "credit balance" in _msg.lower() or "insufficient" in _msg.lower()
                if _is_credit:
                    print(f"[claude] ⚠️ Crédit épuisé — fallback Ollama")
                    model_used = OLLAMA_MODEL
                    if ollama_available:
                        _fb_msgs = [{"role": "system", "content": system}] + anthropic_messages
                        text = ask_ollama_chat(_fb_msgs, OLLAMA_MODEL)
                        if text:
                            text = strip_think_tags(text)
                    if not text:
                        text = (
                            "⚠️ **Crédits Anthropic épuisés.** Je bascule sur Ollama local.\n"
                            "Recharge les crédits sur https://console.anthropic.com/settings/billing\n"
                            "En attendant, je fonctionne en mode Ollama (qwen3:14b)."
                        )
                    # Mark account as credit-exhausted to skip future Claude calls this session
                    _budget["cout_usd"] = BUDGET_MAX_USD + 1.0
                elif _sc in (400, 422):
                    # Bad request — log but return friendly message instead of crashing
                    print(f"[claude] 400/422 APIError: {_msg[:200]}")
                    text = f"⚠️ Erreur API Claude ({_sc}). Basculement sur Ollama..."
                    if ollama_available:
                        _fb_msgs = [{"role": "system", "content": system}] + anthropic_messages
                        _fb_text = ask_ollama_chat(_fb_msgs, OLLAMA_MODEL)
                        if _fb_text:
                            text = strip_think_tags(_fb_text)
                            model_used = OLLAMA_MODEL
                else:
                    raise HTTPException(_sc, detail=_msg)
            except Exception as e:
                raise HTTPException(500, detail=str(e))

    if not text:
        text = "Désolé David, je n'ai pas pu générer de réponse. Réessaie."

    print(f"[chat] modèle={model_used} '{text[:50]}...'")
    add_message(session_id, "assistant", text)

    if req.stream:
        return StreamingResponse(
            _stream_text(text, model_used, req_id, memory=memory_meta),
            media_type="text/event-stream",
            headers={
                "Cache-Control":     "no-cache",
                "X-Accel-Buffering": "no",
                "Connection":        "keep-alive",
            },
        )

    return {
        "id":      req_id,
        "object":  "chat.completion",
        "model":   model_used,
        "created": int(time.time()),
        "memory": memory_meta,
        "choices": [{
            "index":         0,
            "message":       {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "total_tokens":      0,
        },
    }

# ════════════════════════════════════════════════════════
# ORCHESTRATION JARVIS
# ════════════════════════════════════════════════════════

class OrchestrateRequest(BaseModel):
    text: str
    model: str = "claude-haiku-4-5-20251001"

@app.post("/v1/orchestrate")
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

@app.get("/v1/orchestrate/classify")
async def classify_only(text: str):
    """Classification rapide d'une requête sans exécution."""
    return classify_intent(text)

# ════════════════════════════════════════════════════════
# SMOKE TESTS
# ════════════════════════════════════════════════════════

@app.post("/v1/smoke-test")
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


@app.get("/v1/smoke-test/quick")
async def quick_smoke_test():
    """Smoke test rapide des systèmes critiques seulement (5 tests)."""
    from smoke_tests import (
        test_backend_health,
        test_ollama_connectivity,
        test_vault_read,
        test_jarvis_orchestration,
        test_forge_endpoint,
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

@app.get("/v1/ecosystem/health")
async def ecosystem_health():
    """Score de santé pondéré de l'écosystème Nexus9 (0-100)."""
    return await compute_health_score()

@app.get("/v1/ecosystem/health/quick")
async def ecosystem_health_quick():
    """Score rapide sans tests Claude (évite les coûts)."""
    return await compute_health_score(skip_claude=True)

@app.get("/v1/ecosystem/forge/reliability")
def forge_reliability():
    """Métriques de fiabilité du pipeline Forge Room (success_rate, avg_score, bambu_ready_pct)."""
    return get_forge_reliability()


# ════════════════════════════════════════════════════════
# CHEAT CODE ULTIME — Orbital Pipeline HUB
# ════════════════════════════════════════════════════════

@app.post("/v1/cheat-code")
async def cheat_code_run(voice: bool = True):
    """
    One-Click Cheat Code : sync agents, vérifie pipelines, met à jour le Vault, notifie David.
    Déclenché aussi par JARVIS: RUN CHEAT CODE dans le chat.
    """
    from pipeline_runner import run_cheat_code
    report = await run_cheat_code(voice=voice)
    return report



@app.get("/v1/cheat-code/status")
def cheat_code_status():
    """Dernier rapport Cheat Code exécuté."""
    from pipeline_runner import get_last_report
    report = get_last_report()
    if not report:
        return {"status": "never_run", "message": "Lance POST /v1/cheat-code pour démarrer."}
    return report


# ════════════════════════════════════════════════════════
# DOCKER REST ENDPOINTS — direct access from frontend
# ════════════════════════════════════════════════════════

@app.get("/v1/docker/status")
def docker_status_endpoint():
    """Liste tous les containers Docker avec état, ports, santé."""
    from tools.docker_tools import docker_status
    return docker_status()


@app.get("/v1/docker/stats")
def docker_stats_endpoint(name: str = None):
    """CPU / RAM de tous les containers (ou d'un seul si name fourni)."""
    from tools.docker_tools import docker_stats
    return docker_stats(name)


@app.get("/v1/docker/logs/{name}")
def docker_logs_endpoint(name: str, lines: int = 40):
    """Dernières N lignes de logs d'un container."""
    from tools.docker_tools import docker_logs
    return docker_logs(name, lines)


@app.post("/v1/docker/action")
def docker_action_endpoint(body: dict):
    """start | stop | restart un container. Body: {name, action}."""
    from tools.docker_tools import docker_container_action
    return docker_container_action(
        name=body.get("name", ""),
        action=body.get("action", ""),
    )


@app.post("/v1/docker/compose")
def docker_compose_endpoint(body: dict):
    """docker compose up | down | ps | restart. Body: {action}."""
    from tools.docker_tools import docker_compose_action
    return docker_compose_action(action=body.get("action", "ps"))


# ════════════════════════════════════════════════════════
# PHASE 4 stubs — silence frontend boot 404s
# ════════════════════════════════════════════════════════

@app.get("/v1/info")
def server_info():
    """Lightweight server identity. Hit by the SPA on first paint."""
    return {
        "name":    "Nexus9 Backend",
        "version": "9.0.0",
        "phase":   4,
        "model":   CLAUDE_MODEL,
        "host":    os.getenv("HOSTNAME", "nexus_backend"),
    }

@app.get("/v1/connectors")
def list_connectors():
    """Connectors registry stub. Returns empty list until Phase X."""
    return {"connectors": [], "total": 0}


# ════════════════════════════════════════════════════════
# PHASE 5 — React SPA serving
# ════════════════════════════════════════════════════════

# Mount /assets (bundles JS/CSS produits par `npm run build`) si présents
if os.path.isdir(_SPA_ASSETS):
    app.mount("/assets", StaticFiles(directory=_SPA_ASSETS), name="spa_assets")

# Static files at the SPA root (favicon, pwa icons, robots, manifest, sw.js…)
_SPA_ROOT_FILES = {
    "manifest.webmanifest", "registerSW.js", "sw.js", "workbox-*.js",
    "robots.txt", "pwa-192x192.png", "pwa-512x512.png", "apple-touch-icon.png",
}
@app.get("/{filename}", include_in_schema=False)
async def serve_spa_root_file(filename: str):
    """Sert les fichiers statiques racine du SPA (PWA assets, etc.)."""
    candidate = os.path.join(_FRONTEND_DIST, filename)
    if (
        os.path.isfile(candidate)
        and (
            filename in _SPA_ROOT_FILES
            or filename.endswith(('.js', '.css', '.png', '.svg', '.ico', '.webmanifest', '.txt', '.html'))
        )
    ):
        return FileResponse(candidate)
    raise HTTPException(status_code=404)


# Catch-all : react-router SPA fallback pour toute route non-API non-statique
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """Toute route inconnue → sert index.html du SPA pour que react-router prenne le relais."""
    # Sécurité : ne jamais shadow les routes API/legacy
    blocked = ("v1/", "health", "callback", "assets/", "orbital_ui/",
               "favicon", "docs", "redoc", "openapi.json", "nexus9.html")
    if any(full_path.startswith(p) for p in blocked):
        raise HTTPException(status_code=404)
    if os.path.isfile(_SPA_INDEX):
        return FileResponse(_SPA_INDEX, media_type="text/html")
    # Fallback : si pas de build React, retourne Nexus9.html legacy
    return FileResponse(_NEXUS9_HTML, media_type="text/html")


# ── Entrypoint ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("BIND_HOST", "0.0.0.0"), port=PORT, reload=True)

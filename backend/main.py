"""
OpenJarvis Nexus — Backend v0.5.0
FastAPI + Claude + Ollama + CrewAI + SSE Streaming + Mémoire
"""

import os
import time
import json
import logging
import traceback
import tempfile
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
    load_facts, save_facts, build_system_prompt,
    get_last_session_summary,
)
from ollama_client import (
    is_ollama_available, list_local_models,
    ask_ollama_chat, should_use_claude,
    OLLAMA_MODEL,
)

# ── Environnement ────────────────────────────────────────
load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL      = os.getenv("CLAUDE_MODEL",      "claude-haiku-4-5")
CLAUDE_MODEL_GROS = os.getenv("CLAUDE_MODEL_GROS", "claude-sonnet-4-6")
PORT              = int(os.getenv("BACKEND_PORT", 8000))

_default_origins = (
    "http://localhost:5173,http://127.0.0.1:5173,"
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
BASE_SYSTEM = (
    "You are JARVIS, David's AI assistant and orchestration system. "
    "You understand French perfectly but you ALWAYS respond in English. "
    "Be direct, tactical, futuristic like Iron Man's JARVIS. "
    "You have READ access to David's Jarvis workspace via /v1/jarvis/files/ endpoints. "
    "Use /v1/jarvis/files/search to find relevant project files and notes. "
    "Use /v1/jarvis/files/report to save your reports and analyses. "
    "Always check workspace files before answering project-specific questions."
)

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

# ── App ──────────────────────────────────────────────────
app = FastAPI(title="OpenJarvis Nexus Backend", version="0.5.0")
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
app.include_router(stl_router)
app.include_router(research_router)
app.include_router(forge_router)
app.include_router(vault_router)
app.include_router(files_router)
app.include_router(commerce_router)
app.include_router(etsy_oauth_router)

# ── Sert Nexus9.html (UI principale) à la racine ─────────
# Permet l'accès micro (Web Speech API exige un contexte sécurisé : localhost OK, file:// bloqué)
_NEXUS9_HTML = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Nexus9.html"))

@app.get("/")
async def serve_nexus9_root():
    return FileResponse(_NEXUS9_HTML, media_type="text/html")

@app.get("/nexus9.html")
async def serve_nexus9_alias():
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
_ORBITAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "orbital_ui"))

@app.get("/orbital", include_in_schema=False)
async def serve_orbital():
    return FileResponse(os.path.join(_ORBITAL_DIR, "orbital.html"), media_type="text/html")

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
        subprocess.Popen(
            ["cmd", "/c", bat],
            cwd=r"C:\OpenJarvisNexus",
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_CONSOLE,
        )
        return {"status": "launched", "message": "START_ALL.bat lancé dans une nouvelle fenêtre"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Schedulers : STL researcher (21:00) + tâches quotidiennes (03:00) ────────
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

@app.on_event("startup")
async def startup_daily_scheduler():
    # Scheduler partagé — STL researcher 21:00 + tâches quotidiennes 03:00
    scheduler = create_scheduler()
    scheduler.add_job(
        generate_daily_report,
        CronTrigger(hour=21, minute=0),
        id="daily_stl_research",
        name="Daily: stl_research",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    app.state.scheduler = scheduler
    print("[Daily] Scheduler démarré — tâches quotidiennes à 03:00, STL researcher à 21:00")

@app.on_event("shutdown")
async def shutdown_daily_scheduler():
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        print("[Daily] Scheduler arrêté")

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
        task_vault_forge_analytics, task_vault_integrity, task_commerce_analytics,
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
        "vault_forge_analytics":     task_vault_forge_analytics,
        "vault_integrity":           task_vault_integrity,
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
    from one_click_cheat import run_daily_tasks, save_report
    daily = await run_daily_tasks()
    save_report("daily", daily)
    return daily


@app.post("/v1/report/save")
async def report_save(body: dict):
    """Sauvegarde un rapport dans C:\\Users\\bobby\\OneDrive\\Bureau\\Jarvis\\report\\{type}\\"""
    from one_click_cheat import save_report
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

def _stream_text(text: str, model_used: str, req_id: str):
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
    yield _sse({
        "id": req_id, "object": "chat.completion.chunk",
        "model": model_used,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
    })
    yield "data: [DONE]\n\n"

# ════════════════════════════════════════════════════════
# ROUTES SYSTÈME
# ════════════════════════════════════════════════════════

@app.get("/health")
def health():
    ollama_ok = is_ollama_available()
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


@app.get("/v1/health/deep")
async def health_deep():
    """Health check approfondi — teste chaque service avec timeout 3s.
    Retourne: backend, claude_api, ollama, forge_room, meshy_api, timestamp.
    """
    import asyncio

    now = datetime.now().isoformat(timespec="seconds")

    # ── 1. Claude API ────────────────────────────────────
    claude_status = "ok"
    try:
        resp = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: claude.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=5,
                    messages=[{"role": "user", "content": "ping"}],
                ),
            ),
            timeout=3.0,
        )
        _ = resp  # succès
    except asyncio.TimeoutError:
        claude_status = "timeout"
    except Exception as e:
        claude_status = f"error: {type(e).__name__}"

    # ── 2. Ollama ────────────────────────────────────────
    ollama_status = "ok" if is_ollama_available() else "offline"

    # ── 3. Forge Room — fichier cache présent ────────────
    try:
        from forge_room.fabrication_pipeline import FORGE_OUTPUT
        forge_status = "ok" if FORGE_OUTPUT.exists() else "error: forge_output absent"
    except Exception as e:
        forge_status = f"error: {e}"

    # ── 4. Meshy API ─────────────────────────────────────
    meshy_key = os.getenv("MESHY_API_KEY", "")
    if not meshy_key:
        meshy_status = "not_configured"
    else:
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                r = await c.get(
                    "https://api.meshy.ai/v2/text-to-3d",
                    headers={"Authorization": f"Bearer {meshy_key}"},
                )
            meshy_status = "ok" if r.status_code in (200, 401, 403) else f"error: HTTP {r.status_code}"
        except httpx.TimeoutException:
            meshy_status = "timeout"
        except Exception as e:
            meshy_status = f"error: {type(e).__name__}"

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

@app.get("/api/digest")
def api_digest():
    return {
        "summary":       "OpenJarvis Nexus en ligne.",
        "alerts":        [],
        "agents_active": len([j for j in _crew_jobs.values() if j["status"] == "running"]),
        "timestamp":     int(time.time()),
    }

@app.get("/v1/tts")
async def text_to_speech(
    text: str = Query(..., description="Texte à lire"),
    voice: str = Query("fr-FR-HenriNeural", description="Voix edge-tts"),
):
    """Synthèse vocale via Microsoft Edge TTS (gratuit, sans clé API)."""
    text = text[:1000].strip()
    if not text:
        raise HTTPException(400, "Texte vide")
    try:
        import edge_tts
    except ImportError:
        raise HTTPException(503, "edge-tts non installé — lance: pip install edge-tts")

    communicate = edge_tts.Communicate(text, voice)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_path = tmp.name
    tmp.close()

    await communicate.save(tmp_path)

    async def stream_and_delete():
        try:
            with open(tmp_path, "rb") as f:
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
    return {"available": True, "backend": "faster-whisper-base-local"}


@app.post("/v1/speech/transcribe")
async def speech_transcribe(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(400, "Fichier audio vide")

    suffix = ".webm"
    tmp_f  = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_f.write(audio_bytes)
    tmp_f.close()

    def _run(path: str):
        model = _get_whisper()
        segments, info = model.transcribe(
            path,
            task="translate",
            beam_size=5,
            no_speech_threshold=0.6,   # ignore silence/bruit de fond
            condition_on_previous_text=False,  # évite les répétitions hallucinées
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text, info

    try:
        import asyncio
        import traceback
        loop = asyncio.get_event_loop()
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
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    # Destination OneDrive selon le type de rapport
    import shutil
    if report_type == "status":
        onedrive_dir = r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STATUS REPORT"
    elif report_type == "memory":
        onedrive_dir = r"C:\Users\bobby\OneDrive\Bureau\Jarvis\MEMORY REPORT"
    else:
        onedrive_dir = r"C:\Users\bobby\OneDrive\Bureau\Jarvis"
    os.makedirs(onedrive_dir, exist_ok=True)
    onedrive_path = os.path.join(onedrive_dir, filename)
    shutil.copy2(filepath, onedrive_path)
    subprocess.Popen(["notepad.exe", onedrive_path])

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
    models = [{"id": CLAUDE_MODEL, "provider": "anthropic", "available": True}]
    if is_ollama_available():
        for m in list_local_models():
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
    """BRUCE — OpenHands autonome."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"{OPENHANDS_URL}/api/conversations",
                json={"initial_user_msg": task},
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
        return {"ok": False, "agent": "BRUCE", "error": f"BRUCE offline. Lance: docker start nexus_bruce"}
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

@app.post("/v1/chat/completions")
def chat_completion(req: ChatRequest, request: Request):
    session_id = _get_session_id(req, request)

    if req.messages:
        new_msgs = [
            {"role": m.role, "content": m.content}
            for m in req.messages
            if m.role in ("user", "assistant")
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

    # ── Shortcut JARVIS: RUN CHEAT CODE ─────────────────────
    if "jarvis" in last_user_msg.lower() and "cheat" in last_user_msg.lower():
        import asyncio as _asyncio
        from one_click_cheat import run_cheat_code
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
    system     = build_system_prompt(req.system or BASE_SYSTEM, facts)
    # Rappel langue injecté à la fin du system prompt — modèles suivent mieux la dernière instruction
    system    += "\n\n[MANDATORY] Your response language is ENGLISH. Write ONLY in English. No French words."
    req_id     = f"chatcmpl-{int(time.time())}"
    text       = ""
    model_used = ""

    # ── Ollama (gratuit) ─────────────────────────────────
    if not use_claude and ollama_available:
        print(f"[chat] OLLAMA — gratuit")
        _budget["appels_ollama"] += 1
        budget_tracker.record_ollama_call()
        model_used  = OLLAMA_MODEL
        # Pour Ollama : rappel aussi dans le dernier message utilisateur
        ollama_msgs_raw = [{"role": "system", "content": system}] + anthropic_messages
        # Ajoute le rappel de langue au dernier message user
        ollama_msgs = []
        for i, msg in enumerate(ollama_msgs_raw):
            if i == len(ollama_msgs_raw) - 1 and msg["role"] == "user":
                ollama_msgs.append({"role": "user", "content": msg["content"] + "\n\n[Reply in English only]"})
            else:
                ollama_msgs.append(msg)
        text        = ask_ollama_chat(ollama_msgs, OLLAMA_MODEL)
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
            print(f"[chat] 🔵 CLAUDE — question complexe")
            model_used = (req.model if req.model and req.model.strip() else CLAUDE_MODEL)
            try:
                resp = claude.messages.create(
                    model=model_used,
                    max_tokens=req.max_tokens,
                    temperature=req.temperature,
                    system=system,
                    messages=anthropic_messages,
                )
                text = "".join(
                    b.text for b in resp.content
                    if getattr(b, "type", None) == "text"
                )
                _enregistrer_cout(
                    resp.usage.input_tokens + resp.usage.output_tokens,
                    model_used,
                    input_tokens=resp.usage.input_tokens,
                    output_tokens=resp.usage.output_tokens,
                )
            except APIError as e:
                raise HTTPException(getattr(e, "status_code", 502), detail=str(e))
            except Exception as e:
                raise HTTPException(500, detail=str(e))

    if not text:
        text = "Désolé David, je n'ai pas pu générer de réponse. Réessaie."

    print(f"[chat] modèle={model_used} '{text[:50]}...'")
    add_message(session_id, "assistant", text)

    if req.stream:
        return StreamingResponse(
            _stream_text(text, model_used, req_id),
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
    model: str = "claude-haiku-4-5"

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
    from one_click_cheat import run_cheat_code
    report = await run_cheat_code(voice=voice)
    return report


@app.get("/v1/cheat-code/status")
def cheat_code_status():
    """Dernier rapport Cheat Code exécuté."""
    from one_click_cheat import get_last_report
    report = get_last_report()
    if not report:
        return {"status": "never_run", "message": "Lance POST /v1/cheat-code pour démarrer."}
    return report


# ── Entrypoint ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
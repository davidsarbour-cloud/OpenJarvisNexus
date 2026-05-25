"""
OpenJarvis Nexus — Backend v0.5.0
FastAPI + Claude + Ollama + CrewAI + SSE Streaming + Mémoire
"""

import json
import os
import re
import time
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from anthropic import APIError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from ollama_client import (
    OLLAMA_MODEL,
    ask_ollama_chat,
    get_claude_model,
    is_ollama_available,
    list_local_models,
    should_use_claude,
    stream_ollama_chat,
    strip_think_tags,
)
from pydantic import BaseModel

from memory import (
    add_message,
    build_system_prompt,
    compress_session_sync,
    get_history,
    get_last_session_summary,
    is_new_session,
    load_config,
    load_facts,
)
from tools.brain_tools import (
    CLAUDE_TOOL_DEFS as _BRAIN_TOOL_DEFS,
)
from tools.brain_tools import (
    dispatch as _brain_dispatch,
)
from tools.docker_tools import (
    CLAUDE_TOOL_DEFS as _DOCKER_TOOL_DEFS,
)
from tools.docker_tools import (
    dispatch as _docker_dispatch,
)
from tools.docker_tools import (
    quick_status_text as _docker_quick_status,
)
from tools.skill_tools import (
    CLAUDE_TOOL_DEFS as _SKILL_TOOL_DEFS,
)
from tools.skill_tools import (
    dispatch as _skill_dispatch,
)
from tools.skill_tools import (
    skill_catalog_text as _skill_catalog_text,
)

# ── Environnement ────────────────────────────────────────
load_dotenv(override=True)

from app_state import (
    BUDGET_MAX_USD,
    CLAUDE_MODEL,
    CLAUDE_MODEL_GROS,
    PORT,
    _budget,
    _budget_ok,
    _build_base_system,
    _enregistrer_cout,
    claude,
    get_http,
    set_http,
)


# ── Client HTTP partagé (connection pooling) ─────────────
# Vit dans app_state : set_http() dans le lifespan, get_http() partout.
@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Gère le cycle de vie de l'app (remplace @app.on_event deprecated)."""
    import asyncio as _asyncio

    # ── STARTUP ──────────────────────────────────────────
    set_http(httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    ))

    from memory import load_config as _lc
    _cfg = _lc().get("jarvis", {})

    # Pré-charger Kokoro si configuré (évite la latence au 1er appel TTS)
    if _cfg.get("tts_engine") == "kokoro":
        _voice = _cfg.get("tts_voice_kokoro", "bm_george")
        _lc_code = _voice[0] if _voice else "b"
        try:
            from speech_router import _get_kokoro_pipeline
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

        from config import OLLAMA_HOST as _OHB_HOST
        from config import OLLAMA_MODEL as _OHB_MODEL
        from config import OLLAMA_NUM_CTX as _OHB_CTX
        _hb_url = f"{_OHB_HOST}/api/generate"
        while True:
            await _aio.sleep(240)  # 4 minutes
            _hour = _dt.now().hour
            if 7 <= _hour < 23:
                try:
                    await get_http().post(_hb_url, json={
                        "model":  _OHB_MODEL,
                        "prompt": "",
                        "stream": False,
                        "options": {"num_predict": 1, "num_ctx": _OHB_CTX},
                    }, timeout=10.0)
                except Exception:
                    pass  # Ollama indisponible — silencieux

    app.state.ollama_heartbeat_task = _asyncio.create_task(_ollama_heartbeat())
    from config import OLLAMA_MODEL as _hb_model_name
    print(f"[Ollama] Heartbeat démarré — {_hb_model_name} restera chaud 07h-23h.")

    print("[Nexus9] Startup complet — client HTTP partagé prêt.")
    yield

    # ── SHUTDOWN ─────────────────────────────────────────
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        print("[Daily] Scheduler arrêté")
    if get_http() is not None:
        await get_http().aclose()
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
from agents_router import router as agents_router
from brain_router import router as brain_router
from commerce.commerce_router import router as commerce_router
from commerce.etsy_oauth import router as etsy_oauth_router
from crew_router import router as crew_router
from daily_briefing import router as briefing_router
from daily_router import router as daily_router
from daily_tasks import create_scheduler
from docker_router import router as docker_router
from forge_room.forge_engine import router as forge_router
from health_router import router as health_router
from jarvis_files import router as files_router
from memory_router import router as memory_router
from monitoring_router import router as monitoring_router
from orchestrate_router import router as orchestrate_router
from reports_router import router as reports_router
from speech_router import router as speech_router
from stl_agent import router as stl_router
from stl_researcher import generate_daily_report
from stl_researcher import router as research_router
from trend_hunter import router as trends_router
from vault.vault_router import router as vault_router
from ws_router import router as ws_router

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
app.include_router(docker_router)
app.include_router(speech_router)
app.include_router(reports_router)
app.include_router(memory_router)
app.include_router(brain_router)
app.include_router(daily_router)
app.include_router(health_router)
app.include_router(crew_router)
app.include_router(orchestrate_router)
app.include_router(agents_router)

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

# Docker status/action + Skill-list detectors — compiled once at import, used per request
_DOCKER_SHOW_KW = re.compile(
    r"\b(montre|liste|affiche|show|donne|quels?|combien|ps|status|statut|état|voir|check|ping)\b"
    r"|\bup\b|\bdown\b|\brunning\b",
    re.I,
)
_DOCKER_ACTION_KW = re.compile(
    r"\b(restart|redémarre|stop|arrête|start|démarre|lance|kill|rm|remove)\b", re.I
)
_SKILL_LIST_KW = re.compile(
    r"\bskill?s?\b|skils?\b|comp[eé]tences?\b|capacit[eé]s?\b|\bsavoir-faire\b|\bprocédures?\b",
    re.I,
)
_SKILL_LIST_SHOW_KW = re.compile(
    r"\b(liste|list|montre|affiche|show|quels?|quelles?|donne|voir|dis.?moi|what|have|got|as-tu|avez)\b",
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
    from pipeline_runner import detect_pipeline, execute_pipeline
    from pipeline_runner import format_response as _fmt_pipe
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
        import asyncio as _aio_mem
        import time as _t_mem
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
                _all_tools    = _docker_tools + _SKILL_TOOL_DEFS + _BRAIN_TOOL_DEFS
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
                                elif _tname.startswith("brain_"):
                                    _res_str = _brain_dispatch(_tname, _blk.input)
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
                    print("[claude] ⚠️ Crédit épuisé — fallback Ollama")
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

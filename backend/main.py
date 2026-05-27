"""
OpenJarvis Nexus — Backend v0.5.0
FastAPI + Claude + Ollama + CrewAI + SSE Streaming + Mémoire
"""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Boot identity — regenerated on every Python process start (= every
# uvicorn boot, even with --reload). The frontend compares this hex to
# its localStorage record and replays the intro overlay when it differs.
BOOT_ID = uuid.uuid4().hex
BOOT_AT = datetime.now(timezone.utc).isoformat(timespec="seconds")

# ── Environnement ────────────────────────────────────────
load_dotenv(override=True)

from app_state import (
    CLAUDE_MODEL,
    PORT,
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

    # ── Wire APScheduler → EventHub so the RightPanel sees every job fire ────
    # JOB_EXECUTED → info  · JOB_ERROR → alert  · JOB_MISSED → warn
    # The skill-completion notes attach their own clickable `note` link via
    # _write_skill_brain_note(); this listener only surfaces the firing itself.
    try:
        from apscheduler.events import (
            EVENT_JOB_ERROR,
            EVENT_JOB_EXECUTED,
            EVENT_JOB_MISSED,
        )
        from ws_router import emit_sync as _emit_sync

        def _on_scheduler_event(event) -> None:  # pyright: ignore[reportMissingParameterType]
            try:
                job = _scheduler.get_job(event.job_id)
                name = job.name if job else event.job_id
            except Exception:
                name = event.job_id
            if event.code == EVENT_JOB_EXECUTED:
                _emit_sync("info", "SCHEDULER", f"{name} · executed")
            elif event.code == EVENT_JOB_ERROR:
                exc = getattr(event, "exception", None)
                _emit_sync("alert", "SCHEDULER", f"{name} · error: {exc}")
            elif event.code == EVENT_JOB_MISSED:
                _emit_sync("warn", "SCHEDULER", f"{name} · missed run")

        _scheduler.add_listener(
            _on_scheduler_event,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED,
        )
        print("[Daily] Scheduler → EventHub listener attached.")
    except Exception as _e:
        print(f"[Daily] Scheduler event listener wiring failed: {_e}")

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

    # ── Snapshot publishers — broadcasts agents/jobs/world-cards on WS ─
    # Replaces ~15 HTTP polls/min/client with O(1) fan-out via EventHub.
    try:
        from snapshot_publisher import start_publishers
        app.state.snapshot_tasks = start_publishers(app)
        print(f"[Snapshots] {len(app.state.snapshot_tasks)} publishers started.")
    except Exception as _e:
        print(f"[Snapshots] Failed to start: {_e}")

    print("[Nexus9] Startup complet — client HTTP partagé prêt.")
    yield

    # ── SHUTDOWN ─────────────────────────────────────────
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        print("[Daily] Scheduler arrêté")
    if hasattr(app.state, "snapshot_tasks"):
        for _t in app.state.snapshot_tasks:
            _t.cancel()
        print("[Snapshots] publishers cancelled")
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

from agents_router import router as agents_router
from brain_router import router as brain_router
from chat_router import router as chat_router
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
from world_cards_router import router as world_cards_router
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
app.include_router(chat_router)
app.include_router(world_cards_router)

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


@app.get("/v1/boot/info")
def boot_info():
    """Per-process boot identity. The SPA reads this once on first paint
    and replays the intro overlay (NexusBootIntro) whenever ``boot_id``
    differs from the value it last persisted in localStorage. Restarting
    uvicorn → new ``BOOT_ID`` → intro plays once at the next page load."""
    return {"boot_id": BOOT_ID, "started_at": BOOT_AT}

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

"""Daily / system / pipeline endpoints — app launchers, morning routine,
daily research + task runners, report save.

Extracted from main.py. Self-contained: delegates to pipeline_runner and
daily_tasks; owns the desktop-launcher constants. No shared app state
(daily_status reads the scheduler via request.app.state).
"""

import os
import subprocess
import webbrowser
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["daily"])


# ─── moved verbatim from main.py ───
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

@router.post("/v1/system/open")
async def system_open(req: OpenRequest):
    """Lance une app locale (whitelistée) ou une URL."""
    return _launch_target(req.target, req.url)

@router.post("/v1/system/morning-routine")
async def morning_routine():
    """Routine matinale : YouTube + VS Code + Claude app dans l'ordre."""
    results = [
        _launch_target("youtube"),
        _launch_target("vscode"),
        _launch_target("claude"),
    ]
    return {"opened": results, "count_ok": sum(1 for r in results if r["ok"])}

@router.post("/v1/pipeline/start-all")
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

# (Scheduler démarré dans _lifespan — voir début du fichier)

@router.post("/v1/pipeline/daily/start")
def daily_research_start():
    """Lance le daily research en background — retourne immédiatement."""
    from pipeline_runner import start_daily_research_background
    return start_daily_research_background()


@router.get("/v1/pipeline/daily/status")
def daily_research_status():
    """Statut en temps réel du daily research (polling toutes les 5s)."""
    from pipeline_runner import get_research_state
    return get_research_state()


@router.post("/v1/daily/run-task")
async def daily_run_task(body: dict):
    """Exécute une daily task par nom. Body: {"task": "vault_cleanup"}"""
    # Source unique partagée avec pipeline_runner (Cheat Code) — voir daily_tasks.
    from daily_tasks import DAILY_TASK_MAP as _task_map
    name = body.get("task", "")
    fn   = _task_map.get(name)
    if not fn:
        raise HTTPException(404, f"Tâche inconnue: {name}. Dispo: {list(_task_map)}")
    # Emit a start/complete event pair so the RightPanel surfaces manual
    # runs in real time (the scheduler listener only catches cron-driven jobs).
    try:
        from ws_router import emit
        await emit("info", "DAILY", f"{name} · start")
    except Exception:
        pass
    try:
        await fn()
        try:
            from ws_router import emit
            await emit("info", "DAILY", f"{name} · done")
        except Exception:
            pass
        return {"ok": True, "task": name, "message": f"{name} exécutée avec succès"}
    except Exception as e:
        try:
            from ws_router import emit
            await emit("alert", "DAILY", f"{name} · error: {e}")
        except Exception:
            pass
        return {"ok": False, "task": name, "message": str(e)}


@router.post("/v1/daily/run-all")
async def daily_run_all():
    """Exécute toutes les daily tasks et retourne le rapport complet."""
    from pipeline_runner import run_daily_tasks, save_report
    daily = await run_daily_tasks()
    save_report("daily", daily)
    return daily


@router.post("/v1/report/save")
async def report_save(body: dict):
    """Sauvegarde un rapport dans le brain (08_Command-Center/reports/{type})."""
    from pipeline_runner import save_report
    type_ = body.get("type", "pipelines")
    data  = body.get("data", {})
    path  = save_report(type_, data)
    return {"ok": bool(path), "path": str(path) if path else None}


@router.get("/v1/daily/status")
def daily_status(request: Request):
    """Statut du scheduler de tâches quotidiennes."""
    if not hasattr(request.app.state, "scheduler"):
        return {"status": "not_started"}
    jobs = [
        {"id": j.id, "name": j.name, "next_run": str(j.next_run_time)}
        for j in request.app.state.scheduler.get_jobs()
    ]
    return {"status": "running", "jobs": jobs}

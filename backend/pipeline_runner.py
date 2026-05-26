"""
Pipeline Runner — exécution unifiée des pipelines Nexus9.
Appelable depuis : chat Jarvis, vocal Telegram, vocal Web, boutons Hub.
Chaque pipeline : exécute → TTS → sauvegarde rapport.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import httpx
from config import BRAIN_DIR, BRAIN_REPORTS_DIR, BRAIN_RESEARCH_DIR

REPORT_DIR          = BRAIN_REPORTS_DIR          # rapports pipelines -> brain (plus OneDrive)
RESEARCH_REPORT_DIR = BRAIN_RESEARCH_DIR         # daily research -> brain
CHEAT_REPORT_DIR    = BRAIN_DIR / "08_Command-Center" / "cheat_code"
TTS_VOICE           = "fr-FR-HenriNeural"
BACKEND_HOST        = os.getenv("BACKEND_HOST",  "http://localhost:8000")
BRUCE_HOST          = os.getenv("OPENHANDS_URL", "http://localhost:3000")
OLLAMA_HOST         = os.getenv("OLLAMA_HOST",   "http://127.0.0.1:11434")

# Cheat Code — agents surveillés + daily tasks exécutées
AGENTS = {
    "Ollama":  f"{OLLAMA_HOST}/api/tags",
    "Backend": f"{BACKEND_HOST}/health",
    "BRUCE":   f"{BRUCE_HOST}/health",
    "Claude":  "https://api.anthropic.com/v1/models",
}
DAILY_TASKS = [
    ("vault_cleanup",             "Nettoyage sessions Vault"),
    ("forge_analytics",           "Analytics Forge du jour"),
    ("stl_sync",                  "Sync STL → Jarvis/STL"),
    ("health_log",                "Log santé système"),
    ("error_log_cleanup",         "Nettoyage logs erreur"),
    ("vault_maintenance",         "Maintenance + intégrité Vault"),
    ("commerce_analytics",        "Analytics Commerce"),
    ("jarvis_workspace_index",    "Indexation workspace Jarvis"),
    ("daily_smoke_tests",         "Smoke tests quotidiens"),
    ("orchestration_diagnostics", "Diagnostics orchestration"),
]
_last_report: dict = {}

# ── État global du daily research (polling frontend) ──────────────────
_research_state: dict = {
    "status":      "idle",   # idle | running | done | error
    "current":     0,
    "total":       len([]),  # rempli au démarrage
    "current_task": "",
    "results":     [],
    "started_at":  None,
    "finished_at": None,
    "folder":      None,
}

def get_research_state() -> dict:
    return dict(_research_state)

def _reset_research_state():
    _research_state.update({
        "status": "running", "current": 0, "total": 8,
        "current_task": "", "results": [],
        "started_at": str(datetime.now()), "finished_at": None, "folder": None,
    })

# ── Masterlist (hardcodée ci-dessous) ──
RESEARCH_TASKS = [
    {
        "task_id": 1,
        "category": "Code Snippets / AI Scripts",
        "instruction": (
            "Lister 20 scripts Python ou JS pour IA (ex: NLP, CV, RL) "
            "avec description, usage et complexité. Format JSON."
        ),
        "model": "nova",   # deepseek-r1:7b — raisonnement
    },
    {
        "task_id": 2,
        "category": "3D Models / STL",
        "instruction": (
            "Lister 15 modèles 3D STL open source intéressants pour fabrication FDM, "
            "avec description, dimensions et licence. Format CSV."
        ),
        "model": "qwen",
    },
    {
        "task_id": 3,
        "category": "Thumbnails & Visuals",
        "instruction": (
            "Lister 30 idées de miniatures pour vidéos ou produits AI, "
            "avec thème, style et palette de couleurs. Format JSON."
        ),
        "model": "qwen",
    },
    {
        "task_id": 4,
        "category": "AI Innovation",
        "instruction": (
            "Lister 10 tendances récentes en IA (2026), "
            "avec domaine d'impact, potentiel marché et complexité technique. Format JSON."
        ),
        "model": "nova",
    },
    {
        "task_id": 5,
        "category": "Agent AI",
        "instruction": (
            "Lister 8 agents AI récents ou utiles pour automatisation de recherche et développement, "
            "avec description et workflow type. Format CSV."
        ),
        "model": "nova",
    },
    {
        "task_id": 6,
        "category": "AI Tools / Utilities",
        "instruction": (
            "Lister 25 outils AI (frameworks, SaaS, bibliothèques) pour data science, "
            "visualisation et optimisation, avec licence et compatibilité. Format JSON."
        ),
        "model": "qwen",
    },
    {
        "task_id": 7,
        "category": "Learning Resources",
        "instruction": (
            "Lister 15 tutoriels, cours et guides pour mastering AI et génération 3D, "
            "avec source, niveau et durée estimée. Format CSV."
        ),
        "model": "qwen",
    },
    {
        "task_id": 8,
        "category": "Project Ideas",
        "instruction": (
            "Lister 10 projets innovants AI/3D/STL à lancer en 2026, "
            "avec objectifs, ressources nécessaires et faisabilité. Format JSON."
        ),
        "model": "nova",
    },
]


# ── Helpers ───────────────────────────────────────────────────────────

def save_report(type_: str, data: dict) -> "Path | None":
    """Sauvegarde un rapport JSON dans REPORT_DIR/{type_}/ et retourne le chemin."""
    try:
        folder = REPORT_DIR / type_
        folder.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = folder / f"{type_}_{ts}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except Exception:
        return None


async def _tts(message: str):
    """TTS via edge-tts — fr-FR-HenriNeural."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(message[:300], TTS_VOICE)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")  # NOSONAR - instant sync I/O before async save
        tmp_path = tmp.name
        tmp.close()
        await communicate.save(tmp_path)
        ps = (
            f"Add-Type -AssemblyName presentationcore; "
            f"$mp = New-Object System.Windows.Media.MediaPlayer; "
            f"$mp.Open([uri]'{tmp_path}'); $mp.Play(); "
            f"Start-Sleep -Seconds 7; Remove-Item '{tmp_path}' -Force"
        )
        subprocess.Popen(  # NOSONAR - fire-and-forget TTS playback
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass


# ── Pipelines ──────────────────────────────────────────────────────────

async def run_start_all(voice: bool = True) -> dict:
    """Lance START_ALL.bat — démarre tous les services Nexus9."""
    bat = r"C:\OpenJarvisNexus\START_ALL.bat"
    try:
        subprocess.Popen(  # NOSONAR - intentional detached fire-and-forget
            ["cmd", "/c", bat], cwd=r"C:\OpenJarvisNexus",
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_CONSOLE,
        )
        result = {"ok": True, "message": "START_ALL.bat lancé — Ollama, Backend, Telegram, BRUCE, Crush démarrent."}
    except Exception as e:
        result = {"ok": False, "message": str(e)}
    save_report("pipelines", {"type": "start_all", "timestamp": str(datetime.now()), **result})
    if voice:
        msg = "START ALL lancé. Tous les services Nexus9 démarrent." if result["ok"] else "Erreur START ALL."
        await _tts(msg)
    return result


async def _run_research_task(task: dict, date_folder: Path) -> dict:
    """Exécute une tâche de recherche via Ollama local UNIQUEMENT. Jamais Claude."""
    import os

    import httpx as _httpx

    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    model_key   = task.get("model", "qwen")
    model_name  = os.getenv("OLLAMA_MODEL", "qwen3:14b") if model_key == "qwen" \
                  else os.getenv("DEEPSEEK_MODEL", "deepseek-r1:7b")

    msgs = [
        {
            "role": "system",
            "content": (
                "Tu es un agent de recherche Nexus9. "
                "Réponds en français, sois structuré et actionnable. "
                "David est créateur de D3Dprintix (Etsy 3D print) et développeur IA."
            ),
        },
        {"role": "user", "content": task["instruction"]},
    ]

    try:
        async with _httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                f"{OLLAMA_HOST}/api/chat",
                json={"model": model_name, "messages": msgs, "stream": False,
                      "options": {"temperature": 0.7, "num_predict": 2048}},
            )
            r.raise_for_status()
            result_text = r.json().get("message", {}).get("content", "")
            ok = bool(result_text)
    except Exception as e:
        result_text = f"[Ollama offline ou erreur] {e}"
        ok = False

    # Nom de fichier : task_01_Code_Snippets_AI_Scripts.txt
    safe_cat = task["category"].replace("/", "-").replace(" ", "_")
    filename = f"task_{task['task_id']:02d}_{safe_cat}.txt"
    filepath = date_folder / filename

    content = (
        f"{'='*60}\n"
        f"  TASK {task['task_id']} — {task['category'].upper()}\n"
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Modèle: {model_name}\n"
        f"{'='*60}\n\n"
        f"INSTRUCTION:\n{task['instruction']}\n\n"
        f"{'─'*60}\n\n"
        f"RÉSULTAT:\n{result_text or 'Aucune réponse'}\n"
    )
    try:
        filepath.write_text(content, encoding="utf-8")
    except Exception:
        pass

    return {"task_id": task["task_id"], "category": task["category"], "ok": ok, "file": filename, "model": model_name}


async def run_daily_research(voice: bool = True) -> dict:
    """
    Exécute les 8 tâches de la masterlist via Ollama local (QWEN + NOVA).
    Met à jour _research_state à chaque tâche pour le polling frontend.
    Sauvegarde dans RESEARCH REPORT/YYYY-MM-DD/ avec un fichier par tâche + summary.
    """
    import os

    import httpx as _httpx
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

    _reset_research_state()

    # Vérification Ollama obligatoire
    try:
        async with _httpx.AsyncClient(timeout=4) as c:
            r = await c.get(f"{OLLAMA_HOST}/api/tags")
            if r.status_code != 200:
                raise ConnectionError(f"HTTP {r.status_code}")
    except Exception as e:
        msg = f"Ollama offline — daily research annulé ({e})"
        _research_state["status"] = "error"
        _research_state["current_task"] = msg
        if voice:
            await _tts("Ollama est hors ligne. Lance Ollama et réessaie.")
        return {"ok": False, "error": msg, "passed": 0, "total": len(RESEARCH_TASKS)}

    today       = datetime.now().strftime("%Y-%m-%d")
    date_folder = RESEARCH_REPORT_DIR / today
    date_folder.mkdir(parents=True, exist_ok=True)
    _research_state["folder"] = str(date_folder)

    results = []
    for i, task in enumerate(RESEARCH_TASKS):
        _research_state["current"]      = i + 1
        _research_state["current_task"] = f"Task {task['task_id']} — {task['category']} [{task['model'].upper()}]"
        print(f"  📋 {_research_state['current_task']}...")

        res = await _run_research_task(task, date_folder)
        results.append(res)
        _research_state["results"] = list(results)

    passed = sum(1 for r in results if r["ok"])

    # Summary
    summary_path = date_folder / f"_SUMMARY_{today}.txt"
    lines = [
        "=" * 60,
        f"  DAILY RESEARCH SUMMARY — {today}",
        f"  {passed}/{len(results)} tâches OK",
        "=" * 60, "",
    ]
    for r in results:
        icon = "✅" if r["ok"] else "❌"
        lines.append(f"  {icon} Task {r['task_id']} — {r['category']} ({r['model']})")
        lines.append(f"     → {r.get('file','?')}")
        lines.append("")
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    result = {
        "ok": passed > 0, "passed": passed, "total": len(results),
        "date": today, "folder": str(date_folder), "tasks": results,
    }
    save_report("daily", {"type": "daily_research", "timestamp": str(datetime.now()), **result})

    _research_state.update({
        "status": "done", "current": len(results),
        "current_task": f"✅ {passed}/{len(results)} tâches complétées",
        "finished_at": str(datetime.now()),
    })

    # ── Google Sheets ─────────────────────────────────────────
    _research_state["current_task"] = f"✅ {passed}/{len(results)} · Sauvegarde Google Sheets…"
    try:
        from google_sheets import is_configured
        from google_sheets import save_daily_research as _gsheets
        if is_configured():
            # Ajoute le preview du résultat pour chaque tâche
            for r in results:
                txt_file = date_folder / r.get("file", "")
                if txt_file.exists():
                    content = txt_file.read_text(encoding="utf-8", errors="replace")
                    # Extrait juste la section RÉSULTAT
                    idx = content.find("RÉSULTAT:")
                    r["result_preview"] = content[idx+9:idx+400].strip() if idx >= 0 else content[:400]
                else:
                    r["result_preview"] = ""
            ok_sheets = _gsheets(results, today)
            _research_state["google_sheets"] = "✅ sauvegardé" if ok_sheets else "⚠️ erreur"
        else:
            print("ℹ️  Google Sheets non configuré — GOOGLE_SHEETS_ID manquant dans .env")
            _research_state["google_sheets"] = "non configuré"
    except Exception as _ge:
        print(f"⚠️  Google Sheets: {_ge}")
        _research_state["google_sheets"] = f"erreur: {_ge}"

    # ── Ouvrir le rapport ─────────────────────────────────────
    try:
        import subprocess as _sp
        _sp.Popen(["notepad.exe", str(summary_path)])  # NOSONAR - fire-and-forget GUI launch
        print(f"📄 Rapport ouvert : {summary_path}")
    except Exception as _oe:
        print(f"⚠️  Ouverture rapport: {_oe}")

    if voice:
        sheets_msg = "Sauvegardé dans Google Sheets." if _research_state.get("google_sheets") == "✅ sauvegardé" else ""
        await _tts(
            f"Daily research terminé. {passed} sur {len(results)} tâches complétées. "
            f"{sheets_msg} Rapport ouvert."
        )
    return result


def start_daily_research_background():
    """Lance run_daily_research en thread background — retourne immédiatement."""
    import threading
    if _research_state.get("status") == "running":
        return {"ok": False, "message": "Daily research déjà en cours"}
    def _run():
        asyncio.run(run_daily_research(voice=True))
    threading.Thread(target=_run, daemon=True, name="daily-research").start()
    return {"ok": True, "message": "Daily research lancé en background", "total": len(RESEARCH_TASKS)}


async def run_rapport(voice: bool = True) -> dict:
    """Génère un rapport Nexus9 complet et le sauvegarde."""
    import datetime as dt
    now      = dt.datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{date_str}_system.txt"

    reports_dir = Path(os.path.dirname(__file__)) / "reports"
    reports_dir.mkdir(exist_ok=True)
    filepath = reports_dir / filename

    lines = [
        "=" * 60,
        "  JARVIS — NEXUS9 DAILY REPORT",
        f"  {now.strftime('%Y-%m-%d %H:%M')}  |  David Arbour",
        "=" * 60,
        "",
        "  Généré via Pipeline Hub / commande vocale.",
        "",
    ]
    content = "\n".join(lines)
    try:
        filepath.write_text(content, encoding="utf-8")
        # Copier aussi dans le brain
        brain_copy = REPORT_DIR / "reports"
        brain_copy.mkdir(parents=True, exist_ok=True)
        (brain_copy / filename).write_text(content, encoding="utf-8")
        result = {"ok": True, "filename": filename, "path": str(filepath)}
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    if voice:
        await _tts(f"Rapport Nexus9 généré : {filename}")
    return result


async def run_stl(prompt: str, voice: bool = True) -> dict:
    """Lance une mission STL via /v1/forge/mission — Meshy AI → trimesh → Bambu."""
    import os

    import httpx as _httpx
    if not prompt.strip():
        return {"ok": False, "error": "Prompt STL manquant — décris l'objet à imprimer."}
    backend = os.getenv("BACKEND_HOST", "http://localhost:8000")
    try:
        async with _httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                f"{backend}/v1/forge/mission",
                json={"prompt": prompt.strip()},
            )
            data = r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}"}
            mid  = data.get("mission_id", "?")
            result = {"ok": r.status_code == 200, "mission_id": mid, "prompt": prompt, **data}
    except Exception as e:
        result = {"ok": False, "error": str(e), "prompt": prompt}
    # Pas de save ici — 1 seule save à la FIN dans ForgeHub._showForgeMetrics()
    if voice:
        mid = result.get("mission_id", "?")
        msg = f"Mission STL {mid} démarrée. Suivi dans le Forge Hub." if result["ok"] \
              else "Erreur STL pipeline. Vérifie que le backend tourne."
        await _tts(msg)
    return result


# ── Détection de commande dans le texte ───────────────────────────────

_PATTERNS = {
    "docker": re.compile(
        r"(ouvre|open|start|run|lance|d[eé]marre|d[eé]marrer|allume)\s+docker"
        r"|docker\s+(up|start|compose|on|ouvre|lance)"
        r"|run\s+docker"
        r"|docker\s+compose\s+up"
        r"|monte\s+les?\s+containers?"
        r"|start\s+containers?",
        re.I
    ),
    "start_all": re.compile(
        r"start[\s_-]?all|démarre\s+tout|lance\s+tous\s+les\s+services|démarrer\s+nexus",
        re.I
    ),
    "daily": re.compile(
        r"daily[\s_-]?research|recherche\s+(quotidienne|du\s+jour)|tendances\s+3d|top\s+5\s+(idées|produits)",
        re.I
    ),
    "rapport": re.compile(
        r"(génère|generate|lance|run|crée)\s+(un\s+)?rapport|rapport\s+nexus|jarvis[:\s]+rapport",
        re.I
    ),
    "stl": re.compile(
        r"\bstl\b"                                             # mot "stl" n'importe où
        r"|stl[\s_]pipeline"
        r"|forge\s+mission"
        r"|(génère|crée|imprime|make|print|lance|run)\s+(un\s+|le\s+|la\s+)?stl"
        r"|(génère|crée|imprime|print)\s+(un\s+|le\s+)?(modèle|objet|figurine|pièce|dragon|boitier|engrenage|support)"
        r"|\bmeshy\b"
        r"|3d[\s-]?print\s+\w"
        r"|jarvis[:\s]+forge",
        re.I
    ),
}

_STL_EXTRACT = re.compile(
    r"(?:stl|forge|imprime|génère|crée|3d\s*print|meshy|print)[:\s]+(.{3,})",
    re.I
)


def _pids_on_port(port: int) -> list[int]:
    """Retourne les PIDs des processus natifs (non-Docker) qui écoutent sur ce port."""
    pids = []
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True, stderr=subprocess.DEVNULL, timeout=5,
        )
        for line in out.splitlines():
            # Cherche les lignes LISTENING sur ce port
            if f":{port}" in line and ("LISTENING" in line or "LISTEN" in line):
                parts = line.split()
                raw_pid = parts[-1]
                try:
                    pids.append(int(raw_pid))
                except ValueError:
                    pass
    except Exception:
        pass
    return list(set(pids))


def _kill_native_conflicts() -> list[str]:
    """
    Tue les processus natifs (non-Docker) sur les ports que Docker va prendre.
    Ports surveillés : 8000 (backend), 5173 (frontend), 11434 (ollama).
    Les processus Docker eux-mêmes (com.docker.backend) sont ignorés.
    Retourne la liste des processus tués.
    """

    # Noms de processus Docker — ne jamais les tuer
    DOCKER_PROCS = {"com.docker.backend", "dockerd", "docker", "docker-proxy", "vpnkit"}
    # Ports gérés par Docker Compose (natif → Docker)
    CONFLICT_PORTS = [8000, 5173, 11434]

    killed = []
    for port in CONFLICT_PORTS:
        for proc_id in _pids_on_port(port):
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {proc_id}", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=3,
                )
                proc_name = ""
                for row in result.stdout.strip().splitlines():
                    parts = row.strip('"').split('","')
                    if parts:
                        proc_name = parts[0].lower().replace(".exe", "")
                        break

                if proc_name in DOCKER_PROCS or "docker" in proc_name:
                    continue  # c'est Docker lui-même, on ne touche pas

                # Tuer le processus natif
                subprocess.run(["taskkill", "/F", "/PID", str(proc_id)],
                               capture_output=True, timeout=5)
                killed.append(f"{proc_name}:{port}")
                print(f"[docker-pipeline] Tué processus natif {proc_name} (PID {proc_id}) sur port {port}")
            except Exception as e:
                print(f"[docker-pipeline] Impossible de tuer PID {proc_id} sur port {port}: {e}")

    return killed


async def run_docker(voice: bool = True) -> dict:
    """
    Lance Docker Desktop si endormi, résout les conflits de ports avec START_ALL.bat,
    puis `docker compose up -d`. Retourne l'état de chaque container.

    Conflits gérés automatiquement :
      :8000  uvicorn natif  → remplacé par nexus_backend
      :5173  npm run dev    → remplacé par nexus_frontend
      :11434 ollama natif   → remplacé par nexus_ollama (si présent)
    """
    import asyncio as _asyncio

    compose_dir = Path(__file__).parent.parent  # racine du projet (docker-compose.yml)

    # ── 1. Daemon Docker vivant ? ────────────────────────────────────────
    def _daemon_alive() -> bool:
        try:
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    # ── 2. Lancer Docker Desktop si nécessaire ───────────────────────────
    docker_desktop = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if not _daemon_alive():
        if os.path.exists(docker_desktop):
            subprocess.Popen([docker_desktop], creationflags=subprocess.DETACHED_PROCESS)
            for _ in range(12):
                await _asyncio.sleep(5)
                if _daemon_alive():
                    break
            else:
                return {"ok": False, "error": "Docker Desktop n'a pas démarré en 60s", "containers": [], "killed": []}
        else:
            return {"ok": False, "error": "Docker Desktop introuvable", "containers": [], "killed": []}

    # ── 3. Résoudre les conflits avec START_ALL.bat ──────────────────────
    # Tue les processus natifs (uvicorn, node/vite, ollama) sur les ports Docker
    killed = await _asyncio.to_thread(_kill_native_conflicts)
    if killed:
        print(f"[docker-pipeline] Conflits résolus : {killed}")
        await _asyncio.sleep(1)  # laisser les ports se libérer

    # ── 4. docker compose up -d ──────────────────────────────────────────
    try:
        proc = await _asyncio.create_subprocess_exec(
            "docker", "compose", "up", "-d",
            cwd=str(compose_dir),
            stdout=_asyncio.subprocess.PIPE,
            stderr=_asyncio.subprocess.STDOUT,
        )
        stdout, _ = await _asyncio.wait_for(proc.communicate(), timeout=120)
        compose_ok = proc.returncode == 0
    except _asyncio.TimeoutError:
        return {"ok": False, "error": "docker compose up a pris plus de 120s", "containers": [], "killed": killed}
    except Exception as e:
        return {"ok": False, "error": str(e), "containers": [], "killed": killed}

    # ── 5. Lire l'état des containers ────────────────────────────────────
    containers = []
    try:
        ps = await _asyncio.create_subprocess_exec(
            "docker", "compose", "ps", "--format", "json",
            cwd=str(compose_dir),
            stdout=_asyncio.subprocess.PIPE,
            stderr=_asyncio.subprocess.DEVNULL,
        )
        ps_out, _ = await ps.communicate()
        for line in ps_out.decode(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                containers.append({
                    "name":   c.get("Name", "?"),
                    "status": c.get("Status", "?"),
                })
            except Exception:
                pass
    except Exception:
        pass

    result = {
        "ok":         compose_ok,
        "containers": containers,
        "count":      len(containers),
        "up":         sum(1 for c in containers if "Up" in c.get("status", "")),
        "killed":     killed,
    }

    if voice:
        up  = result["up"]
        tot = result["count"]
        msg = f"Docker lancé. {up} containers actifs sur {tot}." if compose_ok \
              else "Erreur au démarrage de Docker Compose."
        if killed:
            msg = f"Conflits résolus. {msg}"
        await _tts(msg)

    return result


def detect_pipeline(text: str) -> tuple[str, str] | None:
    """
    Retourne (pipeline_id, arg) si une commande pipeline est détectée, sinon None.
    pipeline_id: 'start_all' | 'daily' | 'rapport' | 'stl'
    arg: prompt STL extrait (vide pour les autres)
    """
    for pid, pat in _PATTERNS.items():
        if pat.search(text):
            arg = ""
            if pid == "stl":
                m = _STL_EXTRACT.search(text)
                arg = m.group(1).strip() if m else text.strip()
            return (pid, arg)
    return None


async def execute_pipeline(pipeline_id: str, arg: str = "", voice: bool = True) -> dict:
    """Exécute le pipeline et retourne le résultat."""
    if pipeline_id == "docker":
        return await run_docker(voice)
    if pipeline_id == "start_all":
        return await run_start_all(voice)
    if pipeline_id == "daily":
        return start_daily_research_background()
    if pipeline_id == "rapport":
        return await run_rapport(voice)
    if pipeline_id == "stl":
        return await run_stl(arg, voice)
    return {"ok": False, "error": f"Pipeline inconnu : {pipeline_id}"}


def format_response(pipeline_id: str, result: dict) -> str:
    """Formate la réponse chat pour chaque pipeline."""
    ok = result.get("ok", False)

    if pipeline_id == "docker":
        up     = result.get("up", 0)
        tot    = result.get("count", 0)
        ctrs   = result.get("containers", [])
        killed = result.get("killed", [])
        if not ok:
            return f"🐳 **DOCKER ❌**\n\n{result.get('error', 'Erreur inconnue')}"
        lines = [f"🐳 **DOCKER ✅ — {up}/{tot} containers actifs**\n"]
        if killed:
            lines.append(f"⚡ *Conflits START_ALL résolus : `{'`, `'.join(killed)}`*\n")
        for c in ctrs:
            icon = "✅" if "Up" in c.get("status", "") else "⏸"
            name = c.get("name", "?").replace("nexus_", "")
            lines.append(f"{icon} `{name}` — {c.get('status','?')}")
        return "\n".join(lines)

    if pipeline_id == "start_all":
        return (
            f"▶ **START ALL {'✅' if ok else '❌'}**\n\n"
            f"{result.get('message', '')}\n\n"
            "*Services en démarrage : Ollama · Backend · Telegram · BRUCE · Crush AI + Morning Routine.*"
        )
    if pipeline_id == "daily":
        passed  = result.get("passed", 0)
        total   = result.get("total", 0)
        folder  = result.get("folder", "RESEARCH REPORT")
        tasks   = result.get("tasks", [])
        lines   = [f"◑ **DAILY RESEARCH {'✅' if ok else '❌'} — {passed}/{total} tâches**\n"]
        for t in tasks:
            lines.append(f"- {'✅' if t['ok'] else '❌'} Task {t['task_id']} · {t['category']}")
        lines.append(f"\n📁 `{folder}`")
        return "\n".join(lines)
    if pipeline_id == "rapport":
        fname = result.get("filename", "—")
        return (
            f"▣ **RAPPORT {'✅' if ok else '❌'}**\n\n"
            f"Fichier : `{fname}`\n"
            f"Sauvegardé dans `backend/reports/` et `Jarvis/report/reports/`"
        )
    if pipeline_id == "stl":
        mid = result.get("mission_id", "—")
        prompt = result.get("prompt", "")
        if ok:
            return (
                f"⬡ **STL PIPELINE ✅ — Mission `{mid}`**\n\n"
                f"Prompt : *{prompt[:80]}*\n\n"
                "Pipeline démarré : ULTRON Planning → Meshy AI → trimesh → validation → Bambu.\n"
                "*Suivi live dans le **Forge Hub** (bas-droit).*"
            )
        else:
            return f"⬡ **STL PIPELINE ❌**\n\n{result.get('error', 'Erreur inconnue')}"
    return f"Pipeline `{pipeline_id}` : {'✅' if ok else '❌'}"


# ════════════════════════════════════════════════════════════════════════
# CHEAT CODE ULTIME — orchestration globale
# Déclenché par : POST /v1/cheat-code  ou  JARVIS: RUN CHEAT CODE
# ════════════════════════════════════════════════════════════════════════

async def _check_agent(name: str, url: str) -> dict:
    headers = {}
    if "anthropic.com" in url:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"agent": name, "ok": False, "note": "clé manquante"}
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(url, headers=headers)
            ok = r.status_code < 400
    except Exception:
        ok = False
    return {"agent": name, "ok": ok, "url": url}


async def sync_agents() -> list[dict]:
    """Vérifie la disponibilité de chaque agent en parallèle."""
    print("🔄 Synchronisation des agents...")
    results = await asyncio.gather(*[_check_agent(n, u) for n, u in AGENTS.items()])
    for r in results:
        print(f"  {'✅' if r['ok'] else '❌'} {r['agent']}")
    print()
    return list(results)


async def _run_one_task(name: str, label: str) -> dict:
    """Exécute une daily task via POST /v1/daily/run-task."""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{BACKEND_HOST}/v1/daily/run-task", json={"task": name})
            if r.status_code == 200:
                data = r.json()
                ok  = data.get("ok", True)
                msg = data.get("message", "OK")
                print(f"  {'✅' if ok else '⚠️ '} {label}")
                return {"task": name, "label": label, "ok": ok, "message": msg}
            print(f"  ⚠️  {label} — HTTP {r.status_code}")
            return {"task": name, "label": label, "ok": False, "message": f"HTTP {r.status_code}"}
    except Exception as e:
        print(f"  ❌ {label} — {e}")
        return {"task": name, "label": label, "ok": False, "message": str(e)}


# Tâches qui écrivent dans ChromaDB → séquentiel (évite les locks SQLite).
_VAULT_WRITERS = {
    "forge_analytics", "vault_maintenance",
    "orchestration_diagnostics", "jarvis_workspace_index",
    "daily_smoke_tests", "commerce_analytics",
}


async def run_daily_tasks() -> dict:
    """
    Exécute les daily tasks et retourne le rapport.
    Indépendantes (fichiers/HTTP) en parallèle, écritures ChromaDB en séquence.
    """
    print("⚙️  Exécution des daily tasks...")
    parallel   = [(n, l) for n, l in DAILY_TASKS if n not in _VAULT_WRITERS]
    sequential = [(n, l) for n, l in DAILY_TASKS if n in _VAULT_WRITERS]

    par_results = await asyncio.gather(*[_run_one_task(n, l) for n, l in parallel])
    seq_results = [await _run_one_task(n, l) for n, l in sequential]
    results = list(par_results) + seq_results

    passed = sum(1 for r in results if r["ok"])
    print(f"\n  Total : {passed}/{len(results)} tâches OK\n")
    return {"results": results, "passed": passed, "total": len(results), "timestamp": str(datetime.now())}


async def fetch_vault_stats() -> dict:
    """Stats collections ChromaDB + jobs planifiés."""
    result = {"collections": {}, "scheduled_jobs": [], "total_memories": 0}
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{BACKEND_HOST}/v1/vault/stats")
            if r.status_code == 200:
                data = r.json()
                result["collections"] = data.get("collections", {})
                result["total_memories"] = sum(result["collections"].values())
            r2 = await c.get(f"{BACKEND_HOST}/v1/daily/status")
            if r2.status_code == 200:
                result["scheduled_jobs"] = r2.json().get("jobs", [])
    except Exception:
        pass
    return result


async def fetch_ecosystem_score() -> dict:
    """Score de santé 0-100 de l'écosystème Nexus9."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{BACKEND_HOST}/v1/ecosystem/health")
            if r.status_code == 200:
                data = r.json()
                score = data.get("score", data.get("health_score", 0))
                grade = data.get("grade", "—")
                print(f"  ✅ Ecosystem — {score}/100 Grade {grade}")
                return {"score": score, "grade": grade, "details": data}
    except Exception as e:
        print(f"  ⚠️  Ecosystem — {e}")
    return {"score": None, "grade": "—"}


async def update_vault(agents: list[dict], daily: dict, vault_stats: dict) -> str | None:
    try:
        from vault.memory_manager import add_memory
        agents_ok  = sum(1 for a in agents if a["ok"])
        total_mems = vault_stats.get("total_memories", 0)
        passed     = daily.get("passed", 0)
        total_t    = daily.get("total", 0)
        summary = (
            f"Cheat Code exécuté le {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
            f"Agents : {agents_ok}/{len(agents)}. "
            f"Daily tasks : {passed}/{total_t}. "
            f"Vault : {total_mems} mémoires."
        )
        mid = await add_memory(
            "orchestration",
            summary,
            {
                "type":        "cheat_code_report",
                "agents":      json.dumps([a["agent"] + ("✅" if a["ok"] else "❌") for a in agents]),
                "tasks_ok":    str(passed),
                "vault_total": str(total_mems),
                "timestamp":   str(datetime.now()),
            },
        )
        print(f"💾 Rapport persisté dans Vault — ID: {mid}\n")
        return mid
    except Exception as e:
        print(f"⚠️  Vault inaccessible : {e}\n")
        return None


async def run_cheat_code(voice: bool = True) -> dict:
    """
    Cheat Code Ultime — POST /v1/cheat-code ou JARVIS: RUN CHEAT CODE.
    Sync agents → daily tasks → vault stats → persistance Vault → rapport JSON+texte → TTS.
    """
    global _last_report
    started_at = datetime.now()
    print("=== ONE-CLICK CHEAT CODE ULTIME ACTIVÉ ===\n")

    agents, vault_stats, ecosystem = await asyncio.gather(
        sync_agents(), fetch_vault_stats(), fetch_ecosystem_score(),
    )
    daily    = await run_daily_tasks()
    vault_id = await update_vault(agents, daily, vault_stats)

    agents_ok    = sum(1 for a in agents if a["ok"])
    agents_total = len(agents)
    status       = "success" if agents_ok >= agents_total // 2 and daily["passed"] >= daily["total"] // 2 else "degraded"

    report = {
        "started_at":  str(started_at),
        "finished_at": str(datetime.now()),
        "status":      status,
        "agents":      {"online": agents_ok, "total": agents_total, "details": agents},
        "ecosystem":   ecosystem,
        "daily_tasks": daily,
        "vault": {
            "collections":    vault_stats.get("collections", {}),
            "total_memories": vault_stats.get("total_memories", 0),
            "scheduled_jobs": vault_stats.get("scheduled_jobs", []),
        },
        "vault_id": vault_id,
    }
    _last_report = report
    CHEAT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _ts_file = started_at.strftime("%Y-%m-%d_%H-%M-%S")
    (CHEAT_REPORT_DIR / f"cheat-code-{_ts_file}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    eco_score = ecosystem.get("score")
    eco_grade = ecosystem.get("grade", "—")
    msg = (
        f"Cheat Code terminé. {agents_ok} agents en ligne. "
        f"Ecosystem {eco_score}/100 Grade {eco_grade}. "
        f"{daily['passed']} sur {daily['total']} tâches complétées."
    )
    print(f"=== VAULT CENTRAL OPTIMISÉ ✅ ===\n{msg}")

    # Rapport Markdown dans le brain Obsidian
    try:
        ts_label    = started_at.strftime("%Y-%m-%d %H:%M")
        eco_str     = f"{eco_score}/100 Grade {eco_grade}" if eco_score is not None else "—"
        vault_total = report["vault"]["total_memories"]
        md = [
            "---",
            "domain: command-center",
            "type: cheat-code-report",
            "tags: [cheat-code, orchestration, agents, daily-tasks, vault]",
            f"date: {ts_label}",
            f"status: {status}",
            "---",
            "",
            f"# Cheat Code — {ts_label}",
            "",
            f"## Agents — {agents_ok}/{agents_total} en ligne",
        ]
        for a in agents:
            md.append(f"- {'✅' if a['ok'] else '❌'} {a['agent']}")
        md += ["", f"## Ecosystem — {eco_str}", "", f"## Daily tasks — {daily['passed']}/{daily['total']} OK"]
        for t in daily.get("results", []):
            md.append(f"- {'✅' if t['ok'] else '❌'} {t['label']}")
        md += ["", f"## Vault — {vault_total} mémoires", ""]
        md_path = CHEAT_REPORT_DIR / f"cheat-code-{_ts_file}.md"
        md_path.write_text("\n".join(md), encoding="utf-8")
        print(f"📄 Rapport écrit : {md_path}")
    except Exception as _e:
        print(f"⚠️  Écriture rapport: {_e}")

    # Brain sync — réindexe le brain (dont ce rapport) dans le Vault
    try:
        from vault.brain_index import index_brain
        bres = await index_brain()
        report["brain_indexed"] = bres.get("indexed")
        print(f"🧠 Brain réindexé : {bres.get('indexed', '?')} notes")
    except Exception as _be:
        print(f"⚠️  Brain sync: {_be}")

    if voice:
        await _tts(msg)
    return report


def get_last_report() -> dict:
    return _last_report


if __name__ == "__main__":
    asyncio.run(run_cheat_code())

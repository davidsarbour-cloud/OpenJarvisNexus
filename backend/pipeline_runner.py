"""
Pipeline Runner — exécution unifiée des pipelines Nexus9.
Appelable depuis : chat Jarvis, vocal Telegram, vocal Web, boutons Hub.
Chaque pipeline : exécute → TTS → sauvegarde rapport.
"""
from __future__ import annotations
import asyncio, json, os, re, subprocess, tempfile
from datetime import datetime
from pathlib import Path

REPORT_DIR          = Path(r"C:\Users\bobby\OneDrive\Bureau\Jarvis\report")
RESEARCH_REPORT_DIR = Path(r"C:\Users\bobby\OneDrive\Bureau\Jarvis\RESEARCH REPORT")
TTS_VOICE           = "fr-FR-HenriNeural"

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

# ── Masterlist — C:\Users\bobby\OneDrive\Bureau\Jarvis\DAYLY RESEARCH MASTER LIST TXT.txt
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

def _save(type_: str, data: dict):
    try:
        folder = REPORT_DIR / type_
        folder.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = folder / f"{type_}_{ts}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


async def _tts(message: str):
    """TTS via edge-tts — fr-FR-HenriNeural."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(message[:300], TTS_VOICE)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_path = tmp.name
        tmp.close()
        await communicate.save(tmp_path)
        ps = (
            f"Add-Type -AssemblyName presentationcore; "
            f"$mp = New-Object System.Windows.Media.MediaPlayer; "
            f"$mp.Open([uri]'{tmp_path}'); $mp.Play(); "
            f"Start-Sleep -Seconds 7; Remove-Item '{tmp_path}' -Force"
        )
        subprocess.Popen(
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
        subprocess.Popen(
            ["cmd", "/c", bat], cwd=r"C:\OpenJarvisNexus",
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_CONSOLE,
        )
        result = {"ok": True, "message": "START_ALL.bat lancé — Ollama, Backend, Telegram, BRUCE, Crush démarrent."}
    except Exception as e:
        result = {"ok": False, "message": str(e)}
    _save("pipelines", {"type": "start_all", "timestamp": str(datetime.now()), **result})
    if voice:
        msg = "START ALL lancé. Tous les services Nexus9 démarrent." if result["ok"] else f"Erreur START ALL."
        await _tts(msg)
    return result


async def _run_research_task(task: dict, date_folder: Path) -> dict:
    """Exécute une tâche de recherche via Ollama local UNIQUEMENT. Jamais Claude."""
    import os, httpx as _httpx

    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
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
    import os, httpx as _httpx
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

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
    _save("daily", {"type": "daily_research", "timestamp": str(datetime.now()), **result})

    _research_state.update({
        "status": "done", "current": len(results),
        "current_task": f"✅ {passed}/{len(results)} tâches complétées",
        "finished_at": str(datetime.now()),
    })

    # ── Google Sheets ─────────────────────────────────────────
    _research_state["current_task"] = f"✅ {passed}/{len(results)} · Sauvegarde Google Sheets…"
    try:
        from google_sheets import save_daily_research as _gsheets, is_configured
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
        _sp.Popen(["notepad.exe", str(summary_path)], creationflags=subprocess.CREATE_NO_WINDOW)
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
        # Copier aussi dans le dossier OneDrive
        onedrive = REPORT_DIR / "reports"
        onedrive.mkdir(parents=True, exist_ok=True)
        (onedrive / filename).write_text(content, encoding="utf-8")
        result = {"ok": True, "filename": filename, "path": str(filepath)}
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    if voice:
        await _tts(f"Rapport Nexus9 généré : {filename}")
    return result


async def run_stl(prompt: str, voice: bool = True) -> dict:
    """Lance une mission STL via /v1/forge/mission — Meshy AI → trimesh → Bambu."""
    import os, httpx as _httpx
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

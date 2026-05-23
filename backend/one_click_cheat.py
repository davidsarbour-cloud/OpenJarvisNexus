"""
One-Click Cheat Code Ultime — Nexus9 Orbital Pipeline HUB
Synchronise les agents, exécute les daily tasks, met à jour le Vault, sauvegarde les rapports.
Déclenché par : JARVIS: RUN CHEAT CODE  ou  POST /v1/cheat-code
"""
from __future__ import annotations
import asyncio
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import httpx

OLLAMA_HOST  = os.getenv("OLLAMA_HOST",   "http://localhost:11434")
BRUCE_HOST   = os.getenv("OPENHANDS_URL", "http://localhost:3000")
BACKEND_HOST = os.getenv("BACKEND_HOST",  "http://localhost:8000")
TTS_VOICE    = "fr-FR-HenriNeural"

# Dossier de sauvegarde des rapports David
REPORT_DIR = Path(r"C:\Users\bobby\OneDrive\Bureau\Jarvis\report")

AGENTS = {
    "Ollama":  f"{OLLAMA_HOST}/api/tags",
    "Backend": f"{BACKEND_HOST}/health",
    "BRUCE":   f"{BRUCE_HOST}/health",
    "Claude":  "https://api.anthropic.com/v1/models",
}

# Daily tasks à exécuter (nom → endpoint /v1/daily/run-task)
DAILY_TASKS = [
    ("vault_cleanup",          "Nettoyage sessions Vault"),
    ("forge_analytics",        "Analytics Forge du jour"),
    ("stl_sync",               "Sync STL → Jarvis/STL"),
    ("health_log",             "Log santé système"),
    ("error_log_cleanup",      "Nettoyage logs erreur"),
    ("vault_maintenance",      "Maintenance Vault ChromaDB"),
    ("vault_forge_analytics",  "Analytics Forge → Vault"),
    ("vault_integrity",        "Intégrité Vault"),
    ("commerce_analytics",     "Analytics Commerce"),
    ("jarvis_workspace_index", "Indexation workspace Jarvis"),
    ("daily_smoke_tests",      "Smoke tests quotidiens"),
    ("orchestration_diagnostics", "Diagnostics orchestration"),
]

_last_report: dict = {}


# ── Helpers ───────────────────────────────────────────────────

def save_report(type_: str, data: dict) -> Path | None:
    """Sauvegarde un rapport JSON dans REPORT_DIR/{type_}/."""
    try:
        folder = REPORT_DIR / type_
        folder.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = folder / f"{type_}_{ts}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"💾 Sauvegardé : {path}")
        return path
    except Exception as e:
        print(f"⚠️  Save échoué ({type_}): {e}")
        return None


# ── Agent sync ────────────────────────────────────────────────

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


# ── Daily tasks ───────────────────────────────────────────────

async def _run_one_task(name: str, label: str) -> dict:
    """Exécute une daily task via POST /v1/daily/run-task."""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{BACKEND_HOST}/v1/daily/run-task",
                json={"task": name},
            )
            if r.status_code == 200:
                data = r.json()
                ok  = data.get("ok", True)
                msg = data.get("message", "OK")
                print(f"  {'✅' if ok else '⚠️ '} {label}")
                return {"task": name, "label": label, "ok": ok, "message": msg}
            else:
                print(f"  ⚠️  {label} — HTTP {r.status_code}")
                return {"task": name, "label": label, "ok": False, "message": f"HTTP {r.status_code}"}
    except Exception as e:
        print(f"  ❌ {label} — {e}")
        return {"task": name, "label": label, "ok": False, "message": str(e)}


async def run_daily_tasks() -> dict:
    """Exécute toutes les daily tasks en séquence et retourne le rapport."""
    print("⚙️  Exécution des daily tasks...")
    results = []
    for name, label in DAILY_TASKS:
        result = await _run_one_task(name, label)
        results.append(result)
    passed = sum(1 for r in results if r["ok"])
    print(f"\n  Total : {passed}/{len(results)} tâches OK\n")
    return {
        "results":  results,
        "passed":   passed,
        "total":    len(results),
        "timestamp": str(datetime.now()),
    }


# ── Vault stats ───────────────────────────────────────────────

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


# ── Vault persistence ─────────────────────────────────────────

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


# ── TTS ───────────────────────────────────────────────────────

async def notify_tts(message: str):
    try:
        import edge_tts
        communicate = edge_tts.Communicate(message, TTS_VOICE)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")  # NOSONAR - instant sync before async TTS save
        tmp_path = tmp.name
        tmp.close()
        await communicate.save(tmp_path)
        ps_cmd = (
            f"Add-Type -AssemblyName presentationcore; "
            f"$mp = New-Object System.Windows.Media.MediaPlayer; "
            f"$mp.Open([uri]'{tmp_path}'); $mp.Play(); "
            f"Start-Sleep -Seconds 7; Remove-Item '{tmp_path}' -Force"
        )
        subprocess.Popen(  # NOSONAR - fire-and-forget TTS playback
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print(f"🔊 Notification vocale : {message}")
    except Exception as e:
        print(f"⚠️  TTS désactivé : {e}")


# ── Point d'entrée ────────────────────────────────────────────

async def run_cheat_code(voice: bool = True) -> dict:
    """
    Appelé par : POST /v1/cheat-code  ou  JARVIS: RUN CHEAT CODE
    1. Sync agents (parallèle)
    2. Run daily tasks
    3. Fetch vault stats
    4. Persist rapport dans Vault
    5. Save JSON dans REPORT_DIR/cheat_code/
    6. TTS notification
    """
    global _last_report
    started_at = datetime.now()
    print("=== ONE-CLICK CHEAT CODE ULTIME ACTIVÉ ===\n")

    # Agents + vault stats en parallèle, daily tasks en séquence
    agents, vault_stats, ecosystem = await asyncio.gather(
        sync_agents(),
        fetch_vault_stats(),
        fetch_ecosystem_score(),
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
        "agents": {
            "online":  agents_ok,
            "total":   agents_total,
            "details": agents,
        },
        "ecosystem": ecosystem,
        "daily_tasks": daily,
        "vault": {
            "collections":    vault_stats.get("collections", {}),
            "total_memories": vault_stats.get("total_memories", 0),
            "scheduled_jobs": vault_stats.get("scheduled_jobs", []),
        },
        "vault_id": vault_id,
    }
    _last_report = report

    # Save to OneDrive report folder
    report_path = save_report("cheat_code", report)

    eco_score = ecosystem.get("score")
    eco_grade = ecosystem.get("grade", "—")
    msg = (
        f"Cheat Code terminé. {agents_ok} agents en ligne. "
        f"Ecosystem {eco_score}/100 Grade {eco_grade}. "
        f"{daily['passed']} sur {daily['total']} tâches complétées."
    )
    print(f"=== VAULT CENTRAL OPTIMISÉ ✅ ===\n{msg}")

    # ── Rapport texte lisible + Notepad ──────────────────────
    try:
        today     = started_at.strftime("%Y-%m-%d")
        ts_label  = started_at.strftime("%Y-%m-%d %H:%M")
        txt_lines = [
            "=" * 60,
            "  ONE-CLICK CHEAT CODE — RAPPORT NEXUS9",
            f"  {ts_label}  |  David Arbour",
            "=" * 60, "",
            f"  AGENTS  :  {agents_ok}/{agents_total} en ligne",
        ]
        for a in agents:
            txt_lines.append(f"    {'✅' if a['ok'] else '❌'}  {a['agent']}")
        eco_str = f"{eco_score}/100 Grade {eco_grade}" if eco_score is not None else "—"
        txt_lines += [
            "",
            f"  ECOSYSTEM :  {eco_str}",
            "",
            f"  DAILY TASKS :  {daily['passed']}/{daily['total']} OK",
        ]
        for t in daily.get("results", []):
            txt_lines.append(f"    {'✅' if t['ok'] else '❌'}  {t['label']}")
        vault_total = report["vault"]["total_memories"]
        txt_lines += [
            "",
            f"  VAULT  :  {vault_total} mémoires",
            "",
            "=" * 60,
        ]
        txt_content = "\n".join(txt_lines)
        txt_folder  = REPORT_DIR / "cheat_code"
        txt_folder.mkdir(parents=True, exist_ok=True)
        txt_path = txt_folder / f"cheat_{today}.txt"
        txt_path.write_text(txt_content, encoding="utf-8")
        subprocess.Popen(["notepad.exe", str(txt_path)])  # NOSONAR - fire-and-forget GUI
        print(f"📄 Rapport ouvert : {txt_path}")
    except Exception as _e:
        print(f"⚠️  Ouverture rapport: {_e}")

    if voice:
        await notify_tts(msg)

    return report


def get_last_report() -> dict:
    return _last_report


if __name__ == "__main__":
    asyncio.run(run_cheat_code())

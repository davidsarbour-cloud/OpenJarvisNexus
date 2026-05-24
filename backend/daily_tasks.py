"""
Système de tâches quotidiennes automatisées Nexus9.
Exécuté à 03:00 chaque nuit par APScheduler.
"""
from __future__ import annotations
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger("nexus9.daily")

BACKEND_DIR = Path(__file__).parent

# ── Tâches ────────────────────────────────────────────────

async def task_vault_cleanup():
    """Nettoie les sessions Vault anciennes (>30 jours)."""
    try:
        sessions_file = BACKEND_DIR / "sessions.json"
        if not sessions_file.exists(): return
        data = json.loads(sessions_file.read_text(encoding="utf-8"))
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        if isinstance(data, dict):
            before = len(data)
            data = {k: v for k, v in data.items()
                    if (v.get("updated_at") or v.get("created_at") or "9999") >= cutoff}
            sessions_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Vault cleanup: {before} → {len(data)} sessions")
    except Exception as e:
        logger.error(f"Vault cleanup failed: {e}")

async def task_forge_analytics():
    """Rapport quotidien des missions Forge — fichier JSON + mémoire Vault."""
    try:
        cache_file = BACKEND_DIR / "forge_missions_cache.json"
        if not cache_file.exists(): return
        missions = json.loads(cache_file.read_text(encoding="utf-8"))
        today = datetime.now().isoformat()[:10]
        today_missions = [m for m in missions.values()
                          if m.get("created_at", "")[:10] == today]
        completed = [m for m in today_missions if m.get("status") == "completed"]
        failed    = [m for m in today_missions if m.get("status") == "failed"]
        avg_score = sum(m.get("report", {}).get("printability_score", 0)
                        for m in completed if m.get("report")) / max(len(completed), 1)
        report = {
            "date": today,
            "total_missions": len(today_missions),
            "completed": len(completed),
            "failed": len(failed),
            "avg_score": round(avg_score, 1),
            "generated_at": datetime.now().isoformat(),
        }
        report_path = BACKEND_DIR / "forge_reports" / f"daily_{today}.json"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info(f"Forge analytics: {len(completed)} completed, avg={avg_score:.1f}/100")

        # Mémoire Vault (cherchable) — fusionné depuis vault_forge_analytics
        try:
            from vault.memory_manager import add_memory
            from vault.analytics import get_vault_analytics
            forge = get_vault_analytics().get("forge", {})
            await add_memory("forge_reports",
                f"Daily Forge Analytics {today}: "
                f"{forge.get('completed',0)} missions complétées, "
                f"score moyen {forge.get('avg_score',0)}/100, "
                f"{forge.get('bambu_ready',0)} Bambu-ready",
                metadata={"type": "daily_analytics", "date": today})
        except Exception as ve:
            logger.error(f"Forge vault analytics failed: {ve}")
    except Exception as e:
        logger.error(f"Forge analytics failed: {e}")

async def task_stl_directory_sync():
    """Synchronise les STL vers le dossier Jarvis (si non déjà copié)."""
    try:
        forge_output = BACKEND_DIR / "forge_output"
        jarvis_dir = Path(os.getenv("JARVIS_STL_DIR", r"C:\Users\bobby\OneDrive\Bureau\Jarvis\STL"))
        jarvis_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        for stl in forge_output.glob("*_final.stl"):
            dest = jarvis_dir / stl.name
            if not dest.exists():
                shutil.copy2(str(stl), str(dest))
                copied += 1
        if copied:
            logger.info(f"STL sync: {copied} fichiers copiés vers {jarvis_dir}")
    except Exception as e:
        logger.error(f"STL sync failed: {e}")

async def task_system_health_log():
    """Log l'état de santé du système."""
    try:
        import httpx
        async with httpx.AsyncClient() as c:
            r = await c.get("http://localhost:8000/v1/health/deep", timeout=10)
            health = r.json() if r.status_code == 200 else {"error": r.status_code}
        health["timestamp"] = datetime.now().isoformat()
        log_path = BACKEND_DIR / "error_logs" / f"health_{datetime.now():%Y%m%d}.json"
        log_path.parent.mkdir(exist_ok=True)
        log_path.write_text(json.dumps(health, indent=2), encoding="utf-8")
        logger.info(f"Health log: {health.get('backend')} | claude={health.get('claude_api')} | ollama={health.get('ollama')}")
    except Exception as e:
        logger.error(f"Health log failed: {e}")

async def task_error_logs_cleanup():
    """Archive les vieux logs d'erreur (>7 jours)."""
    try:
        error_dir = BACKEND_DIR / "error_logs"
        if not error_dir.exists(): return
        cutoff = datetime.now() - timedelta(days=7)
        cleaned = 0
        for f in error_dir.glob("*.log"):
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()
                cleaned += 1
        if cleaned:
            logger.info(f"Log cleanup: {cleaned} vieux fichiers supprimés")
    except Exception as e:
        logger.error(f"Log cleanup failed: {e}")


async def task_jarvis_workspace_index():
    """Indexe les nouveaux fichiers du workspace Jarvis dans le Vault."""
    try:
        from jarvis_files import JARVIS_READ_DIR, TEXT_EXTENSIONS, _read_text
        from vault.memory_manager import add_memory, search_memory

        indexed = 0
        for path in JARVIS_READ_DIR.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if path.stat().st_size > 500_000:  # skip files > 500KB
                continue
            try:
                content = _read_text(path, max_chars=2000)
                rel = str(path.relative_to(JARVIS_READ_DIR))
                # Vérifie si déjà indexé (recherche par nom de fichier)
                existing = await search_memory("agent_memory", rel, n_results=1)
                already = any(rel in (r.get("metadata", {}).get("file_path","")) for r in existing)
                if not already:
                    await add_memory("agent_memory",
                        f"[File: {rel}]\n{content}",
                        metadata={"source": "jarvis_workspace", "file_path": rel, "file_name": path.name}
                    )
                    indexed += 1
            except Exception:
                pass
        if indexed:
            logger.info(f"Jarvis workspace: {indexed} nouveaux fichiers indexés dans Vault")
        else:
            logger.info("Jarvis workspace: aucun nouveau fichier à indexer")
    except Exception as e:
        logger.error(f"Jarvis workspace index failed: {e}")


# ── Scheduler ─────────────────────────────────────────────

async def task_vault_maintenance():
    """Maintenance + intégrité du Vault — stats, check counts, purge stub.

    Garde-fou futur (volontairement non implémenté) : purge des vieilles
    conversations. À activer quand la collection `conversations` dépassera
    durablement ~500 entrées. Politique prévue : supprimer les conversations
    non-pinned ET plus vieilles que 60 jours, au-delà des 300 plus récentes,
    via col.get(include=["metadatas"]) puis col.delete(ids=[...]).
    """
    try:
        from vault.vault_core import get_collection, COLLECTIONS
        from vault.analytics import get_vault_analytics
        analytics = get_vault_analytics()
        total = analytics.get("total_memories", 0)
        cols  = analytics.get("collections", {})

        # Intégrité — fusionné depuis vault_integrity
        issues = [f"Collection {name}: count négatif ({cols.get(name, 0)})"
                  for name in COLLECTIONS if cols.get(name, 0) < 0]
        if issues:
            logger.warning(f"Vault integrity issues: {issues}")
        active = len([c for c in cols.values() if c > 0])
        logger.info(f"Vault maintenance: {total} mémoires actives, {active} collections actives")

        # Seuil d'archivage conservé pour la future implémentation de la purge.
        cutoff = (datetime.now() - timedelta(days=60)).isoformat()  # noqa: F841
        col = get_collection("conversations")
        if col.count() > 500:
            # TODO(vault-purge): purge réelle à implémenter (voir docstring).
            logger.info(f"Vault: purge conversations anciennes ({col.count()} → 300 max)")
    except Exception as e:
        logger.error(f"Vault maintenance failed: {e}")


async def task_orchestration_diagnostics():
    """Diagnostics quotidiens du système d'orchestration."""
    try:
        from orchestrator import classify_intent
        from vault.memory_manager import vault_query

        results = []

        # Test classification
        test_cases = [
            ("crée un dragon STL 15cm FDM", "fabrication"),
            ("écris un script Python", "coding"),
            ("installe numpy via pip", "execution"),
            ("bonjour comment vas tu", "conversation"),
            ("analyse l'architecture du projet", "reasoning"),
        ]
        for text, expected in test_cases:
            got = classify_intent(text)["intent"]
            ok  = got == expected
            results.append(f"{'✓' if ok else '✗'} [{expected}] '{text[:30]}' → {got}")

        # Test Vault query
        memories = await vault_query("dragon STL fabrication")
        results.append(f"✓ Vault query: {len(memories)} memories retrieved")

        # Log résultats
        passed = sum(1 for r in results if r.startswith('✓'))
        total  = len(results)
        logger.info(f"Orchestration diagnostics: {passed}/{total} passed")
        for r in results:
            logger.info(f"  {r}")

        # Save in vault
        from vault.memory_manager import add_memory
        await add_memory("orchestration",
            f"Daily diagnostics {datetime.now():%Y-%m-%d}: {passed}/{total} passed\n" + "\n".join(results),
            metadata={"type": "diagnostic", "passed": str(passed), "total": str(total)}
        )
    except Exception as e:
        logger.error(f"Orchestration diagnostics failed: {e}")


async def task_morning_briefing():
    """
    Brief matinal automatique — tous les jours à l'heure configurée.
    Génère le brief et le sauvegarde dans le vault BRAIN/02_Daily/.
    """
    try:
        from daily_briefing import build_morning_briefing
        result = await build_morning_briefing()
        if not result.get("enabled"):
            logger.info("Daily briefing: désactivé dans config.json")
            return

        # Sauvegarde dans le vault BRAIN
        from pathlib import Path
        today     = datetime.now().strftime("%Y-%m-%d")
        brain_dir = Path(__file__).parent / "BRAIN" / "BRAIN" / "02_Daily"
        brain_dir.mkdir(parents=True, exist_ok=True)
        out_file  = brain_dir / f"{today}.md"

        # Injecte le brief dans la note quotidienne (section Brief) si elle existe,
        # sinon crée-la avec le brief en tête.
        md = result.get("markdown", "")
        if out_file.exists():
            existing = out_file.read_text(encoding="utf-8")
            # Vérifie le marqueur H1 exact généré par build_morning_briefing
            if f"# ☀️ Brief Matinal — " not in existing:
                out_file.write_text(
                    existing.rstrip() + "\n\n---\n\n" + md,
                    encoding="utf-8",
                )
            else:
                logger.info(f"Morning briefing: déjà présent dans {out_file.name}, skip")
        else:
            out_file.write_text(md, encoding="utf-8")

        logger.info(f"Morning briefing: généré et sauvegardé → {out_file.name}")
    except Exception as e:
        logger.error(f"Morning briefing failed: {e}")


async def task_trend_hunt():
    """
    Trend Hunter — tous les jours à l'heure configurée.
    Fetch les tickers Yahoo Finance + Reddit hot posts et persiste le snapshot.
    """
    try:
        from trend_hunter import run_trend_hunt
        result = await run_trend_hunt()
        if not result.get("enabled", True):
            logger.info("Trend hunter: désactivé dans config.json")
            return

        meta = result.get("_meta", {})
        logger.info(
            f"Trend hunt: {meta.get('symbols_fetched', 0)} tickers · "
            f"{meta.get('subreddits_fetched', 0)} subreddits · "
            f"snapshot {result.get('timestamp', '?')[:10]}"
        )
    except Exception as e:
        logger.error(f"Trend hunt failed: {e}")


async def task_brain_autolink():
    """
    Obsidian Knowledge Auto-Linker — tâche hebdomadaire (dimanche 02:30).
    - Normalise les tags frontmatter
    - Crée les MOCs manquants
    - Détecte les backlinks implicites
    - Génère le rapport d'audit dans BRAIN/05_Resources/Research/
    """
    try:
        from brain_autolinker import run_autolink
        result = run_autolink(dry_run=False)
        logger.info(
            f"Brain autolink: {len(result.get('mocs_created', []))} MOCs créés | "
            f"{len(result.get('tags_fixed', []))} tags normalisés | "
            f"{result.get('implicit_links_added', 0)} backlinks ajoutés | "
            f"{result.get('elapsed_ms', 0)}ms"
        )
        if result.get("broken_links"):
            logger.warning(
                f"Brain autolink: {len(result['broken_links'])} notes avec liens brisés "
                f"— vérification manuelle requise"
            )
    except Exception as e:
        logger.error(f"Brain autolink failed: {e}")


async def task_brain_reindex():
    """Re-indexe le brain Obsidian dans ChromaDB (filet de securite apres les syncs nocturnels).
    La re-indexation post-sync est deja declenchee en temps reel par le sidecar vault_graph
    via POST /v1/brain/reindex — cette tache sert de securite si le sidecar etait offline."""
    try:
        from vault.brain_index import index_brain
        result = await index_brain()
        logger.info(
            f"Brain re-index: {result.get('indexed')} indexed / "
            f"{result.get('skipped')} skipped / {result.get('total')} total in ChromaDB"
        )
    except Exception as e:
        logger.error(f"Brain re-index failed: {e}")


async def task_daily_smoke_tests():
    """Lance les smoke tests quotidiens et sauvegarde le rapport."""
    try:
        from smoke_tests import run_smoke_tests
        report = await run_smoke_tests()

        summary = report["summary"]
        health  = report["health_pct"]

        # Sauvegarde le rapport dans le workspace Jarvis
        from jarvis_files import write_jarvis_report
        content = f"""# Nexus9 Daily Smoke Test — {datetime.now():%Y-%m-%d}

## Summary
- Health: {health}%
- Passed: {summary['passed']}/{summary['total']}
- Failed: {summary['failed']}

## Results
""" + "\n".join(
            f"- {'✓' if r['status'] == 'pass' else '✗'} {r['name']}: {r['message']} ({r['duration_ms']}ms)"
            for r in report["results"]
        )
        write_jarvis_report("smoke_test_daily", content, "")

        # Sauvegarde dans Vault
        from vault.memory_manager import add_memory
        await add_memory("orchestration",
            f"Daily smoke test {datetime.now():%Y-%m-%d}: {summary['passed']}/{summary['total']} passed ({health}%)",
            {"type": "daily_smoke_test", "health_pct": str(health), "passed": str(summary['passed'])}
        )

        logger.info(f"Daily smoke test: {summary['passed']}/{summary['total']} passed, health={health}%")

        # Alerte si santé < 70%
        if health < 70:
            logger.warning(f"ECOSYSTEM HEALTH LOW: {health}% — check smoke test report")

    except Exception as e:
        logger.error(f"Daily smoke test failed: {e}")


async def task_commerce_analytics():
    """Analytics quotidien du pipeline commerce."""
    try:
        from commerce.pipeline import list_pipelines
        pipelines = list_pipelines()
        total     = len(pipelines)
        published = len([p for p in pipelines if p.get('status') == 'published'])
        pending   = len([p for p in pipelines if p.get('status') == 'approval'])
        errors    = len([p for p in pipelines if p.get('status') == 'error'])

        logger.info(f"Commerce analytics: {total} total, {published} published, {pending} pending approval, {errors} errors")

        if pending > 0:
            logger.warning(f"COMMERCE: {pending} produit(s) en attente d'approbation")

        # Save in Vault
        from vault.memory_manager import add_memory
        await add_memory("workflows",
            f"Commerce daily: {published} publiés, {pending} en attente, {errors} erreurs",
            {"type": "commerce_analytics", "published": str(published), "pending": str(pending)}
        )
    except Exception as e:
        logger.error(f"Commerce analytics failed: {e}")


def create_scheduler():
    """Crée et configure l'APScheduler avec toutes les tâches quotidiennes."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler(timezone="America/Toronto")

    # Tâches quotidiennes à 03:00
    daily_tasks = [
        ("vault_cleanup",             task_vault_cleanup,             "03:00"),
        ("forge_analytics",           task_forge_analytics,           "03:05"),
        ("stl_sync",                  task_stl_directory_sync,        "03:10"),
        ("health_log",                task_system_health_log,         "03:15"),
        ("error_log_cleanup",         task_error_logs_cleanup,        "03:20"),
        ("vault_maintenance",         task_vault_maintenance,         "03:25"),
        ("orchestration_diagnostics", task_orchestration_diagnostics, "03:35"),
        ("jarvis_workspace_index",    task_jarvis_workspace_index,    "03:45"),
        # Re-index apres les syncs nocturnels — filet de securite si sidecar offline.
        # (Le sidecar vault_graph declenche aussi ce re-index en temps reel apres chaque sync.)
        ("brain_reindex",             task_brain_reindex,             "03:55"),
        ("daily_smoke_tests",         task_daily_smoke_tests,         "04:00"),
        ("commerce_analytics",        task_commerce_analytics,        "04:10"),
    ]

    for name, func, time_str in daily_tasks:
        hour, minute = time_str.split(":")
        scheduler.add_job(
            func,
            trigger=CronTrigger(hour=int(hour), minute=int(minute)),
            id=name,
            name=f"Daily: {name}",
            replace_existing=True,
            misfire_grace_time=3600,  # tolère 1h de retard
        )
        logger.info(f"Scheduled: {name} at {time_str}")

    # ── Tâches dynamiques — heure lue depuis config.json au démarrage ──────────
    import json as _json
    _cfg_file = BACKEND_DIR / "config.json"
    try:
        _cfg = _json.loads(_cfg_file.read_text(encoding="utf-8")) if _cfg_file.exists() else {}
    except Exception:
        _cfg = {}

    # Trend Hunter — heure depuis config.trend_hunter
    _th_cfg = _cfg.get("trend_hunter", {})
    if _th_cfg.get("enabled", True):
        _th_h = int(_th_cfg.get("schedule_hour",  6))
        _th_m = int(_th_cfg.get("schedule_minute", 0))
        scheduler.add_job(
            task_trend_hunt,
            trigger=CronTrigger(hour=_th_h, minute=_th_m),
            id="trend_hunt",
            name=f"Daily: trend_hunt ({_th_h:02d}:{_th_m:02d})",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info(f"Scheduled: trend_hunt at {_th_h:02d}:{_th_m:02d}")
    else:
        logger.info("Trend hunter: désactivé (config.json)")

    # Morning Briefing — heure depuis config.daily_briefing
    _bf_cfg = _cfg.get("daily_briefing", {})
    if _bf_cfg.get("enabled", True):
        _bf_h = int(_bf_cfg.get("schedule_hour",   7))
        _bf_m = int(_bf_cfg.get("schedule_minute", 30))
        scheduler.add_job(
            task_morning_briefing,
            trigger=CronTrigger(hour=_bf_h, minute=_bf_m),
            id="morning_briefing",
            name=f"Daily: morning_briefing ({_bf_h:02d}:{_bf_m:02d})",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info(f"Scheduled: morning_briefing at {_bf_h:02d}:{_bf_m:02d}")
    else:
        logger.info("Morning briefing: désactivé (config.json)")

    # Tâche hebdomadaire — dimanche 02:30
    scheduler.add_job(
        task_brain_autolink,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=30),
        id="brain_autolink",
        name="Weekly: brain_autolink",
        replace_existing=True,
        misfire_grace_time=7200,  # tolère 2h de retard (hebdo)
    )
    logger.info("Scheduled: brain_autolink (weekly Sunday 02:30)")

    return scheduler

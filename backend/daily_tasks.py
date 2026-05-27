"""
Système de tâches quotidiennes automatisées Nexus9.
Exécuté à 03:00 chaque nuit par APScheduler.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

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
            from vault.analytics import get_vault_analytics
            from vault.memory_manager import add_memory
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
        from vault.analytics import get_vault_analytics
        from vault.vault_core import COLLECTIONS, get_collection
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
            if "# ☀️ Brief Matinal — " not in existing:
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


# ─────────────────────────────────────────────────────────────────────────
# Skill-driven scheduled jobs (daily + weekly)
#
# Maps directly to entries in backend/skills/ (TOML auto-exec) and
# backend/skills/hermes/ (markdown protocols). Each run writes a markdown
# note in BRAIN/02_Daily/YYYY-MM-DD/skill-<name>.md with a [[…]] link to
# the Hermes reference note in BRAIN/05_Resources/Research/hermes/<name>.md
# so the autolinker picks it up and Obsidian shows the backlinks.
#
# When a skill's underlying tool is not yet wired into the backend (e.g.
# blogwatcher-cli, Polymarket API, Claude-based ideation), the task writes
# a "stub" note with instructions on how to invoke the skill manually.
# This keeps the schedule visible in /v1/daily/status and the
# AUTOMATION SCHEDULE card so the calendar slot is always documented.
# ─────────────────────────────────────────────────────────────────────────

def _write_skill_brain_note(
    skill_name: str,
    kind: str,
    body: str,
    when: str = "daily",
) -> Path | None:
    """Write a skill-run report to BRAIN/02_Daily/<today>/skill-<name>.md and
    publish a completion event in the EventHub so the RightPanel shows it
    live with a clickable note link.

    Returns the path (or None if BRAIN_DIR isn't writable, which we never
    raise on — scheduled jobs must not crash the scheduler).
    """
    note_path: Path | None = None
    relative_note: str | None = None
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        brain_root = BACKEND_DIR / "BRAIN" / "BRAIN"
        day_dir = brain_root / "02_Daily" / today
        day_dir.mkdir(parents=True, exist_ok=True)
        note_path = day_dir / f"skill-{skill_name}.md"
        relative_note = f"02_Daily/{today}/skill-{skill_name}.md"
        front_matter = (
            "---\n"
            f"nexus9_skill: {skill_name}\n"
            f"nexus9_kind: {kind}\n"
            f"nexus9_schedule: {when}\n"
            f"nexus9_run_at: {datetime.now().isoformat(timespec='seconds')}\n"
            f"tags: [skill-run, {skill_name}, automated]\n"
            f"related: [[../../05_Resources/Research/hermes/{skill_name}]]\n"
            "---\n\n"
        )
        note_path.write_text(front_matter + body, encoding="utf-8")
    except Exception as e:
        logger.error(f"Skill brain note write failed for {skill_name}: {e}")
        return None

    # Publish a completion event — fire-and-forget so a publish failure
    # never crashes the scheduler loop.
    try:
        import asyncio as _aio

        from ws_router import hub
        evt = {
            "level":  "info",
            "source": "SKILL",
            "msg":    f"{skill_name} · {when} complete",
            "note":   relative_note,
            "skill":  skill_name,
        }
        loop = _aio.get_event_loop()
        if loop.is_running():
            loop.create_task(hub.publish(evt))
        else:
            _aio.run(hub.publish(evt))
    except Exception as e:
        logger.debug(f"Event publish failed for {skill_name}: {e}")

    return note_path


async def task_skill_docker_health():
    """Daily 03:00 — snapshot container health (TOML skill `docker-health`)."""
    try:
        from tools.docker_tools import docker_status
        s = docker_status()
        if not s.get("ok"):
            body = (
                "# Docker Health · snapshot failed\n\n"
                f"```\n{s.get('error', 'unknown error')}\n```\n"
            )
        else:
            up    = s.get("up", 0)
            total = s.get("total", 0)
            rows  = [f"| {c['name']} | {'✅ UP' if c.get('running') else '❌ DOWN'} | {c.get('image','?')} |"
                     for c in s.get("containers", [])]
            body = (
                f"# Docker Health · {up}/{total} UP\n\n"
                f"Snapshot pris à {datetime.now().strftime('%H:%M:%S')}.\n\n"
                "| Container | Status | Image |\n|---|---|---|\n"
                + "\n".join(rows) + "\n"
            )
        _write_skill_brain_note("docker-health", "TOML", body, "daily")
    except Exception as e:
        logger.error(f"task_skill_docker_health: {e}")


async def task_skill_blogwatcher():
    """Daily 06:00 — monitor RSS/Atom feeds (Hermes skill `blogwatcher`)."""
    body = (
        "# Blogwatcher · scheduled run\n\n"
        "**Status**: `blogwatcher-cli` not yet wired into the Nexus9 backend.\n\n"
        "## To run manually\n"
        "- UI : `/world/jarvis` → Quick Actions → BLOGWATCHER\n"
        "- Chat : *applique blogwatcher sur <feed-url>*\n\n"
        "## What this slot is for\n"
        "Daily 06:00 sweep of subscribed RSS / Atom feeds → digest of new posts,\n"
        "scored by relevance to BRAIN tags (trading, dropshipping, IA tools).\n"
    )
    _write_skill_brain_note("blogwatcher", "Hermes", body, "daily")


async def task_skill_polymarket():
    """Daily 21:00 — Polymarket market snapshot (Hermes skill `polymarket`)."""
    body = (
        "# Polymarket · scheduled snapshot\n\n"
        "**Status**: Polymarket API not yet wired into the Nexus9 backend.\n\n"
        "## To run manually\n"
        "- UI : `/world/jarvis` → Quick Actions → POLYMARKET\n"
        "- Chat : *utilise polymarket pour les marchés hot ce soir*\n\n"
        "## What this slot is for\n"
        "Evening snapshot of top-moving prediction markets so the weekly\n"
        "digest (Sun 18:00) has 7 days of data to aggregate.\n"
    )
    _write_skill_brain_note("polymarket", "Hermes", body, "daily")


async def task_skill_codebase_inspection():
    """Weekly Sunday 02:00 — pygount LOC trend (Hermes skill `codebase-inspection`)."""
    import subprocess

    repo_paths = [
        str(BACKEND_DIR),
        str(BACKEND_DIR.parent / "frontend" / "src"),
    ]
    body = "# Codebase Inspection · weekly\n\n"
    try:
        # Skip backend/.venv + frontend/node_modules with --suffix filter
        proc = subprocess.run(
            ["pygount", "--format=summary", *repo_paths],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=180,
        )
        body += "```\n" + (proc.stdout or "").strip() + "\n```\n"
        if proc.returncode != 0:
            body += "\n**stderr**\n```\n" + (proc.stderr or "").strip() + "\n```\n"
    except FileNotFoundError:
        body += "**Status**: `pygount` introuvable. `pip install pygount` dans backend/.venv.\n"
    except Exception as e:
        body += f"**Status**: failed — {type(e).__name__}: {e}\n"
    _write_skill_brain_note("codebase-inspection", "Hermes", body, "weekly")


async def task_skill_polymarket_digest():
    """Weekly Sunday 18:00 — aggregate the week's polymarket runs."""
    body = (
        "# Polymarket · weekly digest\n\n"
        "**Status**: Stub — aggregate of the 7 daily polymarket runs not yet\n"
        "implemented (needs the daily polymarket fetch wired first).\n\n"
        "## Expected output once live\n"
        "- Top 5 movers of the week (price delta)\n"
        "- New high-volume markets created this week\n"
        "- Resolved markets vs. predicted probability\n"
    )
    _write_skill_brain_note("polymarket-digest", "Hermes", body, "weekly")


async def task_skill_ideation():
    """Weekly Friday 14:00 — fresh STL/Etsy idea batch (Hermes skill `ideation`)."""
    body = (
        "# Ideation · weekly Friday batch\n\n"
        "**Status**: Stub — requires a Claude or Ollama call. Auto-run is disabled\n"
        "until budget-guarded routing is wired into the scheduler.\n\n"
        "## To run manually\n"
        "- UI : `/world/jarvis` → Quick Actions → IDEATION\n"
        "- Chat : *utilise ideation pour 10 idées STL Etsy*\n\n"
        "## What this slot is for\n"
        "Friday afternoon idea batch: 10 fresh product ideas crossing\n"
        "current trends × your STL/Etsy niches, ready for the weekend.\n"
    )
    _write_skill_brain_note("ideation", "Hermes", body, "weekly")


async def task_weekly_vault_growth():
    """Weekly Sunday 20:00 — vault growth & health report.

    Counts notes added / modified in the last 7 days, top tags, orphans,
    largest sub-folders, and writes a markdown brief to the brain. The
    completion event surfaces in RightPanel ALERTS & EVENTS with a
    clickable obsidian:// deep-link to the report."""
    import re
    from collections import Counter
    from datetime import timedelta

    brain_root = BACKEND_DIR / "BRAIN" / "BRAIN"
    if not brain_root.exists():
        logger.warning("task_weekly_vault_growth: BRAIN/ not found, skipping")
        _write_skill_brain_note(
            "vault-growth-report", "report",
            "# Vault Growth Report\n\n**Status**: BRAIN/ vault not found on disk.\n",
            "weekly",
        )
        return

    now = datetime.now()
    week_ago = now - timedelta(days=7)
    today = now.date()

    total = 0
    added_this_week  = 0
    modif_this_week  = 0
    by_day: Counter[str] = Counter()
    by_tag: Counter[str] = Counter()
    by_folder: Counter[str] = Counter()
    orphan_count = 0
    recent_notes: list[tuple[datetime, str]] = []
    tag_pattern = re.compile(r"(?:^|[\s,])#([a-zA-Z][\w-]*)")
    link_pattern = re.compile(r"\[\[([^\]]+)\]\]")

    try:
        for md in brain_root.rglob("*.md"):
            if any(p in md.parts for p in (".obsidian", ".trash", "node_modules")):
                continue
            total += 1
            try:
                stat = md.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                ctime = datetime.fromtimestamp(stat.st_ctime)
                rel_folder = md.relative_to(brain_root).parts[0] if md.relative_to(brain_root).parts else "(root)"
                by_folder[rel_folder] += 1

                # Read once for tags + backlinks. Skip files > 256 KB
                # (paste dumps etc.) so the report stays fast.
                if stat.st_size < 262144:
                    content = md.read_text(encoding="utf-8", errors="ignore")
                    for m in tag_pattern.finditer(content):
                        by_tag[m.group(1).lower()] += 1
                    if not link_pattern.search(content):
                        orphan_count += 1

                if ctime >= week_ago:
                    added_this_week += 1
                if mtime >= week_ago and mtime != ctime:
                    modif_this_week += 1
                if mtime >= week_ago:
                    by_day[mtime.strftime("%Y-%m-%d")] += 1
                    recent_notes.append((mtime, str(md.relative_to(brain_root)).replace("\\", "/")))
            except Exception:                                         # noqa: BLE001 - per-file errors must not kill the loop
                continue
    except Exception as e:                                            # noqa: BLE001
        logger.error(f"task_weekly_vault_growth: scan failed: {e}")

    recent_notes.sort(reverse=True)
    week_iso = today.strftime("%G-W%V")

    def _bar(value: int, top: int, width: int = 24) -> str:
        if top <= 0:
            return ""
        filled = int(round(width * value / top))
        return "█" * filled + "·" * (width - filled)

    # Daily activity sparkline-ish bar chart (last 7 days)
    day_chart_lines = []
    top_day = max(by_day.values(), default=0)
    for delta in range(6, -1, -1):
        d = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
        n = by_day.get(d, 0)
        day_chart_lines.append(f"  {d}  {n:>3}  {_bar(n, top_day, 30)}")

    top_tags    = by_tag.most_common(10)
    top_folders = by_folder.most_common(8)

    body_lines: list[str] = [
        f"# Vault Growth Report · week {week_iso}",
        "",
        f"_Generated automatically Sunday 20:00 · run_at: {now.isoformat(timespec='seconds')}_",
        "",
        "## Headline",
        f"- **Total notes** in vault: **{total}**",
        f"- **Added this week**: **{added_this_week}**",
        f"- **Modified this week**: **{modif_this_week}**",
        f"- **Orphan notes** (no `[[backlinks]]`): **{orphan_count}**  "
        f"({(orphan_count / total * 100) if total else 0:.1f}% of vault)",
        "",
        "## Daily activity (last 7 days)",
        "```",
        *day_chart_lines,
        "```",
        "",
        "## Top tags",
    ]
    if top_tags:
        for tag, n in top_tags:
            body_lines.append(f"- `#{tag}` — {n}")
    else:
        body_lines.append("- _(no `#tags` detected)_")
    body_lines.extend([
        "",
        "## Top folders",
    ])
    for folder, n in top_folders:
        body_lines.append(f"- `{folder}/` — {n} notes")

    body_lines.extend(["", "## 10 most recently touched notes"])
    for mtime, rel in recent_notes[:10]:
        body_lines.append(f"- `{mtime.strftime('%Y-%m-%d %H:%M')}` · `{rel}`")

    body_lines.extend([
        "",
        "## Health flags",
    ])
    if total == 0:
        body_lines.append("- ⚠️ Vault is empty")
    if orphan_count > total * 0.30 and total > 20:
        body_lines.append(
            f"- ⚠️ Orphan ratio > 30 % ({orphan_count}/{total}) — consider running brain-autolink"
        )
    if added_this_week == 0 and modif_this_week == 0:
        body_lines.append("- ⚠️ No vault activity this week")
    if not [ln for ln in body_lines if ln.startswith("- ⚠️")]:
        body_lines.append("- ✅ All clear")

    body = "\n".join(body_lines) + "\n"
    _write_skill_brain_note("vault-growth-report", "report", body, "weekly")


async def task_daily_brain_stubs_check():
    """Daily 22:00 — list vault notes that look like stubs (empty body,
    `stub: true` in frontmatter, or under 100 chars of content). Output
    is a brain note + WS event so the RightPanel surfaces it.

    Heuristic for "stub":
      - explicit `stub: true` in YAML frontmatter, or
      - explicit `tags: [stub]` / `tags: [..., stub, ...]`, or
      - body (post-frontmatter) shorter than 100 non-blank characters.
    """
    import re
    brain_root = BACKEND_DIR / "BRAIN" / "BRAIN"
    if not brain_root.exists():
        _write_skill_brain_note(
            "brain-stubs-check", "report",
            "# Brain Stubs Check\n\n**Status**: BRAIN/ not found.\n", "daily",
        )
        return

    stubs: list[tuple[str, str]] = []   # (relative_path, reason)
    scanned = 0
    fm_re   = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)

    try:
        for md in brain_root.rglob("*.md"):
            if any(p in md.parts for p in (".obsidian", ".trash", "node_modules", "_snapshots")):
                continue
            scanned += 1
            try:
                if md.stat().st_size > 524288:   # > 512 KB → not a stub
                    continue
                content = md.read_text(encoding="utf-8", errors="ignore")
                rel = str(md.relative_to(brain_root)).replace("\\", "/")

                # Strip frontmatter
                fm_match = fm_re.match(content)
                frontmatter = fm_match.group(1) if fm_match else ""
                body = content[fm_match.end():] if fm_match else content

                # Explicit stub markers
                if re.search(r"^\s*stub\s*:\s*true\b", frontmatter, re.MULTILINE | re.IGNORECASE):
                    stubs.append((rel, "frontmatter `stub: true`"))
                    continue
                tags_match = re.search(r"^\s*tags\s*:\s*\[([^\]]*)\]", frontmatter, re.MULTILINE | re.IGNORECASE)
                if tags_match and re.search(r"\bstub\b", tags_match.group(1), re.IGNORECASE):
                    stubs.append((rel, "tag `stub`"))
                    continue

                # Body length heuristic — strip blank lines + markdown noise
                lean = re.sub(r"^\s*#+ .*$", "", body, flags=re.MULTILINE)   # headings
                lean = re.sub(r"\s+", " ", lean).strip()
                if len(lean) < 100:
                    stubs.append((rel, f"body < 100 chars ({len(lean)})"))
            except Exception:                                                  # noqa: BLE001
                continue
    except Exception as e:                                                     # noqa: BLE001
        logger.error(f"task_daily_brain_stubs_check: scan failed: {e}")

    body_lines = [
        f"# Brain Stubs Check · daily {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"_Scanned {scanned} notes — found **{len(stubs)} stubs** to fill in._",
        "",
    ]
    if not stubs:
        body_lines.append("## ✅ No stubs detected — vault is fully fleshed out")
    else:
        # Top 30 — anything more is noise in the daily ping
        body_lines.append("## Notes flagged (top 30)")
        for rel, reason in stubs[:30]:
            body_lines.append(f"- `{rel}` — {reason}")
        if len(stubs) > 30:
            body_lines.append(f"- _… +{len(stubs) - 30} more_")

    body = "\n".join(body_lines) + "\n"
    _write_skill_brain_note("brain-stubs-check", "report", body, "daily")


async def task_monthly_repo_audit():
    """Monthly 1st 03:00 — repo health audit: LOC by language, test count,
    outdated dependencies (npm + pip). Writes a brain note for trend
    tracking (compare against last month's report by hand)."""
    import asyncio as _aio
    import subprocess
    repo_root = BACKEND_DIR.parent

    # ── LOC count by extension (backend Python + frontend TS) ───────────
    loc_by_ext: dict[str, int] = {}
    file_count_by_ext: dict[str, int] = {}
    scope = [
        ("backend",  ".py"),
        ("frontend/src", ".ts"),
        ("frontend/src", ".tsx"),
        ("frontend/src", ".css"),
    ]
    skip_parts = {".venv", "node_modules", "__pycache__", "dist", "build", ".vite"}
    for sub, ext in scope:
        root = repo_root / sub
        if not root.exists():
            continue
        total_lines = 0
        files = 0
        for f in root.rglob(f"*{ext}"):
            if any(p in f.parts for p in skip_parts):
                continue
            try:
                total_lines += sum(1 for _ in f.open(encoding="utf-8", errors="ignore"))
                files += 1
            except Exception:                                                  # noqa: BLE001
                continue
        loc_by_ext[ext] = loc_by_ext.get(ext, 0) + total_lines
        file_count_by_ext[ext] = file_count_by_ext.get(ext, 0) + files

    # ── Test counts ─────────────────────────────────────────────────────
    py_tests = len(list((repo_root / "backend" / "tests").rglob("test_*.py"))) if (repo_root / "backend" / "tests").exists() else 0
    ts_tests = sum(1 for _ in (repo_root / "frontend" / "src").rglob("*.test.ts*")) + \
               sum(1 for _ in (repo_root / "frontend" / "src").rglob("*.spec.ts*"))

    # ── Outdated deps ───────────────────────────────────────────────────
    async def _run(cmd: list[str], cwd: Path, timeout: int = 90) -> tuple[int, str]:
        try:
            proc = await _aio.to_thread(
                subprocess.run, cmd, cwd=str(cwd),
                capture_output=True, text=True, timeout=timeout, shell=False,
            )
            return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
        except Exception as e:                                                 # noqa: BLE001
            return -1, f"error: {e}"

    npm_outdated_count = 0
    npm_summary = ""
    try:
        _, npm_out = await _run(["npm", "outdated", "--json"], repo_root / "frontend", timeout=60)
        if npm_out.strip():
            data = json.loads(npm_out)
            if isinstance(data, dict):
                npm_outdated_count = len(data)
                top = sorted(data.items())[:10]
                lines = []
                for name, info in top:
                    cur = info.get("current", "?")
                    lat = info.get("latest", "?")
                    lines.append(f"  - `{name}` : `{cur}` → `{lat}`")
                npm_summary = "\n".join(lines)
                if npm_outdated_count > 10:
                    npm_summary += f"\n  - _… +{npm_outdated_count - 10} more_"
    except Exception as e:                                                     # noqa: BLE001
        npm_summary = f"  - _error parsing npm outdated: {e}_"

    pip_outdated_count = 0
    pip_summary = ""
    try:
        venv_python = repo_root / "backend" / ".venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            venv_python = Path("python")
        _, pip_out = await _run([str(venv_python), "-m", "pip", "list", "--outdated", "--format=json"], repo_root, timeout=120)
        if pip_out.strip():
            data = json.loads(pip_out)
            if isinstance(data, list):
                pip_outdated_count = len(data)
                top = sorted(data, key=lambda d: d.get("name", ""))[:10]
                lines = []
                for d in top:
                    name = d.get("name", "?")
                    cur  = d.get("version", "?")
                    lat  = d.get("latest_version", "?")
                    lines.append(f"  - `{name}` : `{cur}` → `{lat}`")
                pip_summary = "\n".join(lines)
                if pip_outdated_count > 10:
                    pip_summary += f"\n  - _… +{pip_outdated_count - 10} more_"
    except Exception as e:                                                     # noqa: BLE001
        pip_summary = f"  - _error parsing pip outdated: {e}_"

    # ── Compose report ──────────────────────────────────────────────────
    total_loc = sum(loc_by_ext.values())
    total_files = sum(file_count_by_ext.values())
    body_lines = [
        f"# Monthly Repo Audit · {datetime.now().strftime('%Y-%m')}",
        "",
        "_Generated automatically 1st of month 03:00 — compare with previous month's note in `02_Daily/`._",
        "",
        "## Codebase size",
        f"- **Total LOC** (source files): **{total_loc:,}**",
        f"- **Total source files**: **{total_files}**",
        "",
    ]
    for ext in sorted(loc_by_ext):
        body_lines.append(f"- `{ext}` : {loc_by_ext[ext]:,} lines across {file_count_by_ext[ext]} files")
    body_lines.extend([
        "",
        "## Tests",
        f"- Backend `pytest` files: **{py_tests}**",
        f"- Frontend `*.test.ts*` / `*.spec.ts*`: **{ts_tests}**",
        f"- **Combined**: {py_tests + ts_tests} test files",
        "",
        "## Dependencies",
        f"- **npm outdated**: **{npm_outdated_count}**",
    ])
    if npm_summary:
        body_lines.append(npm_summary)
    body_lines.extend([
        "",
        f"- **pip outdated**: **{pip_outdated_count}**",
    ])
    if pip_summary:
        body_lines.append(pip_summary)
    body_lines.extend(["", "## Health flags"])
    if npm_outdated_count > 30:
        body_lines.append(f"- ⚠️ npm has {npm_outdated_count} outdated deps — bulk upgrade overdue")
    if pip_outdated_count > 30:
        body_lines.append(f"- ⚠️ pip has {pip_outdated_count} outdated deps — bulk upgrade overdue")
    if py_tests + ts_tests < 20:
        body_lines.append(f"- ⚠️ Test count low ({py_tests + ts_tests}) — coverage hasn't grown")
    if not [ln for ln in body_lines if ln.startswith("- ⚠️")]:
        body_lines.append("- ✅ All clear")

    body = "\n".join(body_lines) + "\n"
    _write_skill_brain_note("monthly-repo-audit", "report", body, "monthly")


async def task_monthly_brain_snapshot():
    """Monthly 1st 04:00 — tarball snapshot of BRAIN/BRAIN/ outside the
    repo to survive accidental `rm -rf` / vault corruption. Keeps the
    last 6 snapshots rolling (older ones auto-pruned)."""
    import tarfile
    brain_root = BACKEND_DIR / "BRAIN" / "BRAIN"
    if not brain_root.exists():
        _write_skill_brain_note(
            "monthly-brain-snapshot", "report",
            "# Monthly Brain Snapshot\n\n**Status**: BRAIN/ not found.\n", "monthly",
        )
        return

    # Snapshots live OUTSIDE the repo so a `git clean -fdx` doesn't wipe
    # them. ~/.nexus9/brain-snapshots/ works on Windows + Unix.
    out_root = Path.home() / ".nexus9" / "brain-snapshots"
    out_root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m")
    archive_path = out_root / f"brain-{stamp}.tar.gz"

    skipped_dirs = {".obsidian", ".trash", "node_modules", "_snapshots"}
    files_archived = 0
    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            for md in brain_root.rglob("*"):
                if md.is_dir():
                    continue
                if any(p in md.parts for p in skipped_dirs):
                    continue
                try:
                    tar.add(md, arcname=str(md.relative_to(brain_root)))
                    files_archived += 1
                except Exception:                                              # noqa: BLE001
                    continue
        archive_size_mb = archive_path.stat().st_size / 1024 / 1024
    except Exception as e:                                                     # noqa: BLE001
        logger.error(f"task_monthly_brain_snapshot: failed to write archive: {e}")
        _write_skill_brain_note(
            "monthly-brain-snapshot", "report",
            f"# Monthly Brain Snapshot\n\n**Status**: FAILED — `{e}`\n", "monthly",
        )
        return

    # Rotate — keep last 6 snapshots
    snapshots = sorted(out_root.glob("brain-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed: list[str] = []
    for old in snapshots[6:]:
        try:
            old.unlink()
            removed.append(old.name)
        except Exception:                                                      # noqa: BLE001
            continue

    body_lines = [
        f"# Monthly Brain Snapshot · {stamp}",
        "",
        "_Generated automatically 1st of month 04:00._",
        "",
        "## Archive",
        f"- **Path**: `{archive_path}`",
        f"- **Files archived**: {files_archived}",
        f"- **Size**: {archive_size_mb:.1f} MB",
        "",
        "## Rotation",
        f"- Snapshots kept: {min(len(snapshots), 6)}",
    ]
    if removed:
        body_lines.append(f"- Removed (rolling 6-month window): {', '.join(removed)}")
    body_lines.extend([
        "",
        "## Restore",
        "If you ever need to restore this snapshot:",
        "```pwsh",
        f"tar -xzf '{archive_path}' -C 'C:/OpenJarvisNexus/backend/BRAIN/BRAIN/'",
        "```",
        "",
    ])

    _write_skill_brain_note("monthly-brain-snapshot", "report", "\n".join(body_lines), "monthly")


def create_scheduler():
    """Crée et configure l'APScheduler avec toutes les tâches quotidiennes."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler(timezone="America/Toronto")

    # ── Daily 03:00-04:10 maintenance jobs DISABLED ─────────────────────────
    # The 10 maintenance tasks (vault_cleanup, forge_analytics, stl_sync,
    # health_log, error_log_cleanup, vault_maintenance, orchestration_diagnostics,
    # jarvis_workspace_index, daily_smoke_tests, commerce_analytics) and the
    # brain_reindex job used to run automatically at 03:00-04:10.
    #
    # They are now triggered ON-DEMAND via the Cheat Code pipeline
    # (`POST /v1/cheat-code` → `run_daily_tasks()` + `index_brain()`), which
    # is the user's normal entry point. Nightly schedule was pure redundancy.
    #
    # The task functions themselves stay defined in this module — Cheat Code
    # invokes them via `POST /v1/daily/run-task` (see daily_router.py).
    #
    # See BRAIN/07_Schemas/system/cheat-code-pipeline.md for the full Cheat
    # Code flow that absorbed these tasks.
    logger.info("Daily 03:00-04:10 maintenance jobs are now triggered via Cheat Code, not the scheduler.")

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

    # ── Skill jobs — 3 daily + 3 weekly ─────────────────────────────────────
    # Each writes a markdown note to BRAIN/02_Daily/<today>/skill-<name>.md
    # with a wikilink to the skill's Hermes reference note. Naming follows
    # the `Daily:`/`Weekly:` prefix convention so the AUTOMATION SCHEDULE
    # frontend card buckets them correctly.

    skill_jobs = [
        # (task,                         id,                          name,                                                  cron kwargs,                        grace)
        (task_skill_docker_health,       "skill_docker_health",       "Daily: skill-docker-health (03:00)",                  {"hour":  3, "minute":  0},        3600),
        (task_skill_blogwatcher,         "skill_blogwatcher",         "Daily: skill-blogwatcher (06:00)",                    {"hour":  6, "minute":  0},        3600),
        (task_skill_polymarket,          "skill_polymarket",          "Daily: skill-polymarket (21:00)",                     {"hour": 21, "minute":  0},        3600),
        (task_skill_codebase_inspection, "skill_codebase_inspection", "Weekly: skill-codebase-inspection (Sun 02:00)",       {"day_of_week": "sun", "hour":  2}, 7200),
        (task_skill_ideation,            "skill_ideation",            "Weekly: skill-ideation (Fri 14:00)",                  {"day_of_week": "fri", "hour": 14}, 7200),
        (task_skill_polymarket_digest,   "skill_polymarket_digest",   "Weekly: skill-polymarket-digest (Sun 18:00)",         {"day_of_week": "sun", "hour": 18}, 7200),
        (task_weekly_vault_growth,       "weekly_vault_growth",       "Weekly: vault-growth-report (Sun 20:00)",             {"day_of_week": "sun", "hour": 20}, 7200),
        (task_daily_brain_stubs_check,   "daily_brain_stubs_check",   "Daily: brain-stubs-check (22:00)",                    {"hour": 22, "minute": 0},          3600),
        (task_monthly_repo_audit,        "monthly_repo_audit",        "Monthly: repo-audit (1st 03:00)",                     {"day": 1, "hour":  3, "minute": 0}, 7200),
        (task_monthly_brain_snapshot,    "monthly_brain_snapshot",    "Monthly: brain-snapshot (1st 04:00)",                 {"day": 1, "hour":  4, "minute": 0}, 7200),
    ]
    for fn, job_id, job_name, cron_kwargs, grace in skill_jobs:
        scheduler.add_job(
            fn,
            trigger=CronTrigger(**cron_kwargs),
            id=job_id,
            name=job_name,
            replace_existing=True,
            misfire_grace_time=grace,
        )
        logger.info(f"Scheduled: {job_name}")

    return scheduler

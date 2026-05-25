"""Brain (Obsidian vault) endpoints — read/write/search/reindex/autolink,
plus /v1/setup/import which syncs config.json + memory.json from nexus9-setup.md.

Extracted from main.py. Self-contained: delegates to tools.brain_tools,
brain_autolinker, vault.brain_index and the memory module; no shared app state.
"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from memory import save_facts
from tools.brain_tools import brain_read as _brain_read_fn
from tools.brain_tools import brain_search as _brain_search_fn
from tools.brain_tools import brain_write as _brain_write_fn

router = APIRouter(tags=["brain"])


# ─── endpoints below were moved verbatim from main.py ───
class _BrainWriteReq(BaseModel):
    path:    str
    content: str
    append:  bool = False

@router.get("/v1/brain/read")
async def brain_read_endpoint(path: str):
    result = _brain_read_fn(path)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result

@router.post("/v1/brain/write")
async def brain_write_endpoint(req: _BrainWriteReq):
    result = _brain_write_fn(req.path, req.content, req.append)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.get("/v1/brain/search")
async def brain_search_endpoint(q: str, max_results: int = 10):
    return _brain_search_fn(q, max_results)

# ── Brain re-index endpoint (appelé par le vault_graph sidecar après chaque sync) ──

@router.post("/v1/brain/reindex")
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


@router.post("/v1/brain/autolink")
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


@router.post("/v1/brain/autolink/sync")
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

@router.post("/v1/setup/import")
async def import_setup():
    """
    Lit BRAIN/08_Command-Center/nexus9-setup.md et met à jour config.json + memory.json.
    Déclencher via : POST /v1/setup/import
    Ou depuis le chat : "JARVIS, importe la configuration nexus9-setup"
    """
    import re as _re

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
    from memory import load_facts
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

"""
Daily Briefing — Nexus9
Consolide en un seul appel : santé système, vault, tendances STL,
watchlist et projets actifs.

Endpoints:
  GET  /v1/briefing/morning   → brief complet (markdown + JSON structuré)
  POST /v1/briefing/morning   → même chose (pour déclencher depuis un scheduler)
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/v1/briefing", tags=["briefing"])

BACKEND_DIR = Path(__file__).parent
_LOCALE_DAYS   = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
_LOCALE_MONTHS = [
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


# ── Config ──────────────────────────────────────────────────────────────────

def _cfg() -> dict:
    f = BACKEND_DIR / "config.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except Exception:
        return {}


def _bf_cfg() -> dict:
    return _cfg().get("daily_briefing", {})


def _french_date(dt: datetime) -> str:
    return f"{_LOCALE_DAYS[dt.weekday()]} {dt.day} {_LOCALE_MONTHS[dt.month]} {dt.year}"


# ── Sections ─────────────────────────────────────────────────────────────────

async def _section_health() -> dict[str, Any]:
    """État du système Nexus9."""
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://127.0.0.1:8000/v1/ecosystem/health/quick")
        if r.status_code == 200:
            d = r.json()
            score  = d.get("score", "?")
            status = d.get("status", "?")
            grade  = d.get("grade", "?")
            try:
                score_int = int(score)
                icon = "🟢" if score_int >= 80 else ("🟡" if score_int >= 60 else "🔴")
            except (ValueError, TypeError):
                icon = "❓"
            return {
                "ok":      True,
                "score":   score,
                "status":  status,
                "grade":   grade,
                "summary": f"{icon} Système `{score}/100` — Grade `{grade}` — {status}",
            }
    except Exception as e:
        return {"ok": False, "summary": f"⚠️ Système — Indisponible ({e})"}
    return {"ok": False, "summary": "⚠️ Système — Aucune donnée"}


async def _section_vault_stubs() -> dict[str, Any]:
    """Nombre de notes à remplir dans le vault Obsidian."""
    try:
        brain_dir = BACKEND_DIR / "BRAIN" / "BRAIN"
        if not brain_dir.exists():
            return {"ok": False, "summary": "🧠 Vault — Introuvable"}

        all_notes   = list(brain_dir.rglob("*.md"))
        stub_count  = 0
        stub_names: list[str] = []
        for p in all_notes:
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")[:400]
                if "_a remplir_" in txt or "TODO" in txt:
                    stub_count += 1
                    stub_names.append(p.stem)
            except Exception:
                pass

        examples = ", ".join(f"`{s}`" for s in stub_names[:5])
        suffix   = f" (ex: {examples})" if examples else ""
        return {
            "ok":         True,
            "total":      len(all_notes),
            "stubs":      stub_count,
            "stub_names": stub_names,
            "summary":    f"🧠 Vault — {len(all_notes)} notes · {stub_count} stubs{suffix}",
        }
    except Exception as e:
        return {"ok": False, "summary": f"🧠 Vault — ⚠️ Erreur: {e}"}


async def _section_stl_trends() -> dict[str, Any]:
    """Dernières tendances STL depuis research_logs/."""
    try:
        research_dir = BACKEND_DIR / "research_logs"
        snaps = sorted(research_dir.glob("*.json"), reverse=True) if research_dir.exists() else []
        if not snaps:
            return {"ok": False, "summary": "📦 Tendances 3D — Aucun rapport disponible"}

        snap = json.loads(snaps[0].read_text(encoding="utf-8"))
        date = snaps[0].stem
        lines = [f"📦 **Tendances 3D** — {date}"]

        for source in ("thingiverse", "cults3d", "etsy"):
            items = snap.get(source, [])
            if isinstance(items, list) and items:
                top = items[0].get("title", "?")[:60]
                lines.append(f"  • **{source.capitalize()}**: {top}")

        summary_txt = snap.get("summary", "")
        return {
            "ok":      True,
            "date":    date,
            "summary": "\n".join(lines),
            "raw_summary": summary_txt,
        }
    except Exception as e:
        return {"ok": False, "summary": f"📦 Tendances 3D — ⚠️ Erreur: {e}"}


async def _section_watchlist() -> dict[str, Any]:
    """Prix des tickers depuis le dernier snapshot trend_hunter."""
    hcfg = _cfg().get("trend_hunter", {})
    tickers   = hcfg.get("tickers", [])
    crypto    = hcfg.get("crypto", [])
    all_syms  = tickers + crypto

    if not all_syms:
        return {
            "ok":      False,
            "summary": "📈 Watchlist — Aucun ticker configuré (`config.json → trend_hunter.tickers`)",
        }

    snap_dir  = BACKEND_DIR / hcfg.get("snapshot_dir", "trend_snapshots")
    today     = datetime.now().strftime("%Y-%m-%d")
    snap_file = snap_dir / f"trends-{today}.json"

    # Fallback to latest available
    if not snap_file.exists():
        snaps = sorted(snap_dir.glob("trends-*.json"), reverse=True) if snap_dir.exists() else []
        snap_file = snaps[0] if snaps else None

    if not snap_file or not snap_file.exists():
        return {
            "ok":      False,
            "summary": (
                f"📈 Watchlist — {', '.join(all_syms)} · "
                f"Pas de snapshot (fetch à {hcfg.get('schedule_hour', 6):02d}h00)"
            ),
        }

    try:
        data   = json.loads(snap_file.read_text(encoding="utf-8"))
        tdata  = data.get("tickers", {})
        lines  = [f"📈 **Watchlist** — `{snap_file.stem}`"]
        for sym in all_syms:
            info = tdata.get(sym, {})
            if "error" in info:
                lines.append(f"  ⚠️ **{sym}**: erreur")
            else:
                price      = info.get("price", "?")
                change_pct = float(info.get("change_pct") or 0)
                arrow      = "🟢" if change_pct >= 0 else "🔴"
                lines.append(f"  {arrow} **{sym}**: `{price}` ({change_pct:+.2f}%)")
        return {
            "ok":       True,
            "snapshot": snap_file.name,
            "summary":  "\n".join(lines),
        }
    except Exception as e:
        return {"ok": False, "summary": f"📈 Watchlist — ⚠️ Erreur: {e}"}


async def _section_tasks() -> dict[str, Any]:
    """Projets actifs et prochaines étapes depuis memory.json."""
    try:
        mem_file = BACKEND_DIR / "memory.json"
        if not mem_file.exists():
            return {"ok": False, "summary": "✅ Projets — Aucun fichier memory.json"}

        facts     = json.loads(mem_file.read_text(encoding="utf-8"))
        projects  = facts.get("projects", [])
        goals     = facts.get("goals", [])
        nexts     = facts.get("session_plan", {}).get("next_steps", [])

        lines = ["✅ **Projets actifs**"]
        for p in projects[:6]:
            lines.append(f"  • {p}")

        if nexts:
            lines.append("\n⏳ **Prochaines étapes**")
            for s in nexts[:4]:
                lines.append(f"  ▸ {s}")

        if goals:
            lines.append("\n🎯 **Objectifs 2026**")
            for g in goals[:3]:
                lines.append(f"  ◆ {g}")

        return {
            "ok":       True,
            "projects": projects,
            "nexts":    nexts,
            "summary":  "\n".join(lines) if len(lines) > 1 else "✅ Projets — Aucun projet enregistré",
        }
    except Exception as e:
        return {"ok": False, "summary": f"✅ Projets — ⚠️ Erreur: {e}"}


# ── Section registry ─────────────────────────────────────────────────────────

_SECTIONS: dict[str, Callable[[], Coroutine[Any, Any, dict]]] = {
    "health":      _section_health,
    "vault_stubs": _section_vault_stubs,
    "stl_trends":  _section_stl_trends,
    "watchlist":   _section_watchlist,
    "tasks":       _section_tasks,
}

SECTION_ICONS = {
    "health":      "🔧",
    "vault_stubs": "🧠",
    "stl_trends":  "📦",
    "watchlist":   "📈",
    "tasks":       "✅",
}


# ── Core ─────────────────────────────────────────────────────────────────────

async def build_morning_briefing() -> dict[str, Any]:
    """Construit le brief matinal consolidé (async)."""
    bf_cfg = _bf_cfg()

    if not bf_cfg.get("enabled", True):
        return {
            "enabled":  False,
            "markdown": "Daily briefing désactivé — `config.json → daily_briefing.enabled: true`",
        }

    sections_keys = bf_cfg.get(
        "sections",
        ["health", "vault_stubs", "stl_trends", "watchlist", "tasks"],
    )
    greeting_tpl = bf_cfg.get(
        "greeting_template",
        "Bonjour David. Voici ton brief du {date}.",
    )

    now     = datetime.now()
    date_fr = _french_date(now)
    time_str = now.strftime("%H:%M")

    greeting = greeting_tpl.format(date=date_fr, time=time_str)

    # Fetch all sections in parallel
    valid_keys = [k for k in sections_keys if k in _SECTIONS]
    coros      = [_SECTIONS[k]() for k in valid_keys]
    raw        = await asyncio.gather(*coros, return_exceptions=True)

    section_data: dict[str, dict] = {}
    for key, result in zip(valid_keys, raw):
        if isinstance(result, Exception):
            section_data[key] = {"ok": False, "summary": f"{SECTION_ICONS.get(key, '?')} {key} — ⚠️ Exception: {result}"}
        else:
            section_data[key] = result

    # Build markdown
    lines = [
        f"# ☀️ Brief Matinal — {date_fr}",
        f"*{time_str} · Nexus9 JARVIS*",
        "",
        f"> {greeting}",
        "",
        "---",
        "",
    ]
    for key in valid_keys:
        sec = section_data.get(key, {})
        lines.append(sec.get("summary", f"*{key} — données manquantes*"))
        lines.append("")

    lines += [
        "---",
        f"*Généré le {now.strftime('%Y-%m-%d %H:%M:%S')} — Nexus9 v0.5.0*",
    ]

    return {
        "enabled":  True,
        "date":     now.isoformat()[:10],
        "time":     time_str,
        "greeting": greeting,
        "sections": {k: v.get("summary", "") for k, v in section_data.items()},
        "details":  section_data,
        "markdown": "\n".join(lines),
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/morning")
@router.post("/morning")
async def morning_briefing():
    """Brief matinal consolidé : santé, vault, tendances, watchlist, projets."""
    return await build_morning_briefing()

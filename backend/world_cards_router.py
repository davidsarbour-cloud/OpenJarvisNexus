"""
World Cards Snapshot Router — aggregates metrics for the /world/* dashboard
cards that can be derived from local data (filesystem, existing endpoints,
in-process state). One endpoint, one fetch per poll cycle, distributed to
each live card wrapper on the frontend via a React context.

Cards NOT included here (require external auth or hardware not connected):
  - MESHY CREDITS (Meshy AI API key + balance endpoint)
  - ETSY ORDERS, LISTING PERFORMANCE (Etsy OAuth)
  - BAMBU QUEUE (Bambu Lab network printer)
  - API RATE LIMITS (Anthropic response header parsing)

Endpoint: GET /v1/world/cards/snapshot
Polling: clients should poll every 30s — most metrics change slowly.
"""
from __future__ import annotations

import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil
from fastapi import APIRouter

router = APIRouter(tags=["world-cards"])

BACKEND_DIR = Path(__file__).parent
BRAIN_DIR   = BACKEND_DIR / "BRAIN" / "BRAIN"
FORGE_OUT   = BACKEND_DIR / "forge_output"
ERROR_LOGS  = BACKEND_DIR / "error_logs"


def _humanize_bytes(n: int) -> str:
    """Convert bytes to GB string."""
    gb = n / (1024 ** 3)
    return f"{gb:.0f}GB" if gb >= 1 else f"{n // (1024**2)}MB"


def _humanize_age(ts: datetime) -> str:
    """Compact 'time since' label."""
    delta = datetime.now() - ts
    s = int(delta.total_seconds())
    if s < 60:        return f"{s}s ago"
    if s < 3600:      return f"{s // 60}m ago"
    if s < 86400:     return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


# ── STL OUTPUT (Forge) ──────────────────────────────────────────────────────

def _stl_output_snapshot() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = 0
    total_count = 0
    if FORGE_OUT.exists():
        for stl in FORGE_OUT.glob("*_final.stl"):
            total_count += 1
            mtime = datetime.fromtimestamp(stl.stat().st_mtime)
            if mtime.strftime("%Y-%m-%d") == today:
                today_count += 1
    return {
        "status": "active" if total_count else "standby",
        "metrics": [
            {"label": "TODAY",  "value": str(today_count)},
            {"label": "TOTAL",  "value": str(total_count)},
        ],
    }


# ── APPROVAL QUEUE (Commerce) ───────────────────────────────────────────────

def _approval_queue_snapshot() -> dict:
    try:
        from commerce.approval_queue import get_pending_approvals
        pending = get_pending_approvals()
        n = len(pending)
        oldest = "—"
        if pending:
            timestamps = [p.get("created_at", "") for p in pending if p.get("created_at")]
            if timestamps:
                oldest_ts = min(timestamps)
                try:
                    dt = datetime.fromisoformat(oldest_ts.replace("Z", "+00:00").rstrip("+00:00"))
                    oldest = _humanize_age(dt)
                except Exception:
                    oldest = "?"
        return {
            "status": "active" if n else "standby",
            "metrics": [
                {"label": "PENDING", "value": str(n)},
                {"label": "OLDEST",  "value": oldest},
            ],
        }
    except Exception:
        return {
            "status": "standby",
            "metrics": [
                {"label": "PENDING", "value": "—"},
                {"label": "OLDEST",  "value": "—"},
            ],
        }


# ── TOKEN BUDGET (Commerce) ─────────────────────────────────────────────────

def _token_budget_snapshot() -> dict:
    try:
        from app_state import BUDGET_MAX_USD, _budget
        spent = _budget.get("session", {}).get("cost_usd", 0.0)
        used_pct = (spent / BUDGET_MAX_USD * 100) if BUDGET_MAX_USD else 0
        return {
            "status": "active",
            "metrics": [
                {"label": "SPENT",  "value": f"${spent:.2f}"},
                {"label": "BUDGET", "value": f"{used_pct:.0f}%"},
            ],
        }
    except Exception:
        return {
            "status": "standby",
            "metrics": [
                {"label": "SPENT",  "value": "—"},
                {"label": "BUDGET", "value": "—"},
            ],
        }


# ── GPU TEMP (Cyberdeck) — derives from existing /v1/system/metrics ─────────

def _gpu_temp_snapshot() -> dict:
    try:
        # nvidia-smi (VRAM + util + temp en 1 seul appel, caché ~2s) via helper
        from health_router import _read_vram
        v = _read_vram()
        util = v.get("gpu_util")
        temp = v.get("gpu_temp")
        return {
            "status": "active" if util is not None else "standby",
            "metrics": [
                {"label": "TEMP", "value": f"{temp}°C" if temp is not None else "—"},
                {"label": "UTIL", "value": f"{util}%"   if util is not None else "—"},
            ],
        }
    except Exception:
        return {
            "status": "standby",
            "metrics": [
                {"label": "TEMP", "value": "—"},
                {"label": "UTIL", "value": "—"},
            ],
        }


# ── ERROR LOG TAIL (Cyberdeck) ──────────────────────────────────────────────

def _error_log_snapshot() -> dict:
    if not ERROR_LOGS.exists():
        return {"status": "standby", "metrics": [
            {"label": "24H",  "value": "0"},
            {"label": "LAST", "value": "—"},
        ]}

    cutoff = datetime.now() - timedelta(hours=24)
    recent = []
    for f in ERROR_LOGS.glob("*.json"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                recent.append((mtime, f))
        except Exception:
            continue

    n = len(recent)
    last = "—"
    if recent:
        latest = max(recent, key=lambda t: t[0])
        last = _humanize_age(latest[0])

    return {
        "status": "active",
        "metrics": [
            {"label": "24H",  "value": str(n)},
            {"label": "LAST", "value": last},
        ],
    }


# ── VAULT GROWTH (Vault) ────────────────────────────────────────────────────

def _vault_growth_snapshot() -> dict:
    if not BRAIN_DIR.exists():
        return {"status": "standby", "metrics": [
            {"label": "TODAY", "value": "0"},
            {"label": "TOTAL", "value": "0"},
        ]}
    try:
        s = _vault_stats()
        total_count = s["total_count"]
        today_count = s["today_count"]
    except Exception:
        return {"status": "standby", "metrics": [
            {"label": "TODAY", "value": "0"},
            {"label": "TOTAL", "value": "0"},
        ]}

    total_label = f"{total_count // 1000}.{(total_count % 1000) // 100}K" if total_count >= 1000 else str(total_count)

    return {
        "status": "active",
        "metrics": [
            {"label": "TODAY", "value": str(today_count)},
            {"label": "TOTAL", "value": total_label},
        ],
    }


# ── VAULT SCAN PARTAGÉ (Vault Growth + Orphan Alert) ───────────────────────
# Avant : 2 rglob complets du vault (growth + orphans) à chaque snapshot.
# Maintenant : 1 seul parcours, caché ~30s (le vault bouge lentement, le front
# poll à 30s). Les deux cartes consomment la même mesure.
#   • total_count  = TOUS les fichiers .md         → carte Vault Growth (TOTAL)
#   • unique_count = stems uniques (lowercased)    → carte Orphan Alert (TOTAL)
# Ces deux totaux sont volontairement distincts — sémantiques d'origine préservées.

_LINK_RE = re.compile(r"\[\[([^\]|#\n]+?)(?:\|[^\]]*)?\]\]")

_vault_cache: dict = {"data": None, "ts": 0.0}
_vault_lock = threading.Lock()
# Le front poll à 30s : un TTL ≤ 30s raterait à chaque appel. 60s → ~1 hit / 2,
# et le scan ne coûte que ~20ms de toute façon. Le vault bouge lentement.
_VAULT_TTL = 60.0


def _compute_vault_stats() -> dict:
    """Parcours unique du vault : croissance + graphe de liens (orphelins)."""
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = 0
    total_count = 0
    all_files: dict[str, Path] = {}
    outgoing: dict[str, set[str]] = {}

    for md in BRAIN_DIR.rglob("*.md"):
        if ".obsidian" in md.parts:
            continue
        total_count += 1
        try:
            mtime = datetime.fromtimestamp(md.stat().st_mtime)
            if mtime.strftime("%Y-%m-%d") == today:
                today_count += 1
        except Exception:
            pass
        stem = md.stem.lower()
        all_files[stem] = md
        try:
            txt = md.read_text(encoding="utf-8", errors="replace")
            outgoing[stem] = {
                m.group(1).strip().split("/")[-1].lower()
                for m in _LINK_RE.finditer(txt)
            }
        except Exception:
            outgoing[stem] = set()

    incoming: dict[str, int] = {k: 0 for k in all_files}
    for _src, links in outgoing.items():
        for target in links:
            if target in incoming:
                incoming[target] += 1

    orphan_count = sum(
        1 for stem, n in incoming.items()
        if n == 0 and len(outgoing.get(stem, set())) == 0
    )

    return {
        "today_count":  today_count,
        "total_count":  total_count,       # tous les fichiers (Vault Growth)
        "unique_count": len(all_files),    # stems uniques (Orphan Alert)
        "orphan_count": orphan_count,
    }


def _vault_stats() -> dict:
    """Accès caché (TTL ~30s) au scan vault, double-checked locking."""
    now = time.time()
    cached = _vault_cache["data"]
    if cached is not None and (now - _vault_cache["ts"]) < _VAULT_TTL:
        return cached
    with _vault_lock:
        now = time.time()
        cached = _vault_cache["data"]
        if cached is not None and (now - _vault_cache["ts"]) < _VAULT_TTL:
            return cached
        data = _compute_vault_stats()
        _vault_cache["data"] = data
        _vault_cache["ts"] = time.time()
        return data


# ── ORPHAN ALERT (Vault) — notes sans [[backlinks]], depuis le scan partagé ──

def _orphan_alert_snapshot() -> dict:
    if not BRAIN_DIR.exists():
        return {"status": "standby", "metrics": [
            {"label": "ORPHANS", "value": "—"},
            {"label": "TOTAL",   "value": "—"},
        ]}
    try:
        s = _vault_stats()
        return {
            "status": "active",
            "metrics": [
                {"label": "ORPHANS", "value": str(s["orphan_count"])},
                {"label": "TOTAL",   "value": str(s["unique_count"])},
            ],
        }
    except Exception:
        return {
            "status": "standby",
            "metrics": [
                {"label": "ORPHANS", "value": "—"},
                {"label": "TOTAL",   "value": "—"},
            ],
        }


# ── MORNING BRIEF (Vault) ───────────────────────────────────────────────────

def _morning_brief_snapshot() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    note = BRAIN_DIR / "02_Daily" / f"{today}.md"
    if not note.exists():
        return {
            "status": "standby",
            "metrics": [
                {"label": "GENERATED", "value": "—"},
                {"label": "ITEMS",     "value": "0"},
            ],
        }

    try:
        txt = note.read_text(encoding="utf-8", errors="replace")
        marker = "# ☀️ Brief Matinal"
        has_brief = marker in txt
        if not has_brief:
            return {
                "status": "standby",
                "metrics": [
                    {"label": "GENERATED", "value": "—"},
                    {"label": "ITEMS",     "value": "0"},
                ],
            }
        # Time the brief was generated (file mtime)
        mtime = datetime.fromtimestamp(note.stat().st_mtime)
        gen_label = mtime.strftime("%H:%M")
        # Count bullet items in the brief
        items = len(re.findall(r"^\s*[-*]\s+", txt, re.MULTILINE))
        return {
            "status": "active",
            "metrics": [
                {"label": "GENERATED", "value": gen_label},
                {"label": "ITEMS",     "value": str(items)},
            ],
        }
    except Exception:
        return {
            "status": "standby",
            "metrics": [
                {"label": "GENERATED", "value": "—"},
                {"label": "ITEMS",     "value": "—"},
            ],
        }


# ── DISK USAGE (Docker) ─────────────────────────────────────────────────────

def _disk_usage_snapshot() -> dict:
    try:
        path = "C:/" if os.name == "nt" else "/"
        u = psutil.disk_usage(path)
        free_gb = u.free / (1024 ** 3)
        used_pct = u.percent
        return {
            "status": "active",
            "metrics": [
                {"label": "FREE", "value": f"{free_gb:.0f}GB"},
                {"label": "USED", "value": f"{used_pct:.0f}%"},
            ],
        }
    except Exception:
        return {
            "status": "standby",
            "metrics": [
                {"label": "FREE", "value": "—"},
                {"label": "USED", "value": "—"},
            ],
        }


# ── CONTAINER LOGS (Docker) — count active containers + recent error lines ─

_docker_cache: dict = {"data": None, "ts": 0.0}
_docker_lock = threading.Lock()
# `docker ps` coûte ~190ms (le poste le plus lourd du snapshot). Le compteur de
# conteneurs bouge très lentement → TTL 120s : au polling 30s, ~3 hits / 4
# (coût moyen ~48ms vs 190ms à chaque appel). Le Pipeline Hub a son propre
# endpoint pour le contrôle temps réel ; cette carte n'est qu'un compteur passif.
_DOCKER_TTL = 120.0


def _container_logs_snapshot() -> dict:
    try:
        now = time.time()
        st = _docker_cache["data"]
        if st is None or (now - _docker_cache["ts"]) >= _DOCKER_TTL:
            with _docker_lock:
                now = time.time()
                st = _docker_cache["data"]
                if st is None or (now - _docker_cache["ts"]) >= _DOCKER_TTL:
                    from tools.docker_tools import docker_status
                    st = docker_status()
                    _docker_cache["data"] = st
                    _docker_cache["ts"] = time.time()
        containers = st.get("containers", [])
        active = sum(1 for c in containers if c.get("running"))
        # Estimating errors would require scanning each container's logs;
        # for the snapshot we return 0 unless wired to a real log aggregator.
        return {
            "status": "active",
            "metrics": [
                {"label": "ACTIVE", "value": str(active)},
                {"label": "ERRORS", "value": "0"},
            ],
        }
    except Exception:
        return {
            "status": "standby",
            "metrics": [
                {"label": "ACTIVE", "value": "—"},
                {"label": "ERRORS", "value": "—"},
            ],
        }


# ── TELEGRAM ACTIVITY (Cyberdeck) ──────────────────────────────────────────

def _telegram_activity_snapshot() -> dict:
    try:
        from app_state import _telegram_state
        # Roll counter if day changed
        today = datetime.now().strftime("%Y-%m-%d")
        if _telegram_state.get("today_date") != today:
            count = 0
        else:
            count = int(_telegram_state.get("messages_today", 0))
        last_ts = _telegram_state.get("last_message_ts")
        last_label = "—"
        if isinstance(last_ts, datetime):
            last_label = _humanize_age(last_ts)
        return {
            "status": "active" if count else "standby",
            "metrics": [
                {"label": "MESSAGES", "value": str(count)},
                {"label": "LAST",     "value": last_label},
            ],
        }
    except Exception:
        return {
            "status": "standby",
            "metrics": [
                {"label": "MESSAGES", "value": "—"},
                {"label": "LAST",     "value": "—"},
            ],
        }


# ── MODEL ROUTING (Cyberdeck) ──────────────────────────────────────────────

def _model_routing_snapshot() -> dict:
    try:
        from app_state import _routing_state
        today = datetime.now().strftime("%Y-%m-%d")
        if _routing_state.get("today_date") != today:
            total = 0
            top_label = "—"
        else:
            total = int(_routing_state.get("total", 0))
            counts: dict[str, int] = _routing_state.get("counts", {})  # type: ignore[assignment]
            if counts and total:
                top_intent = max(counts, key=lambda k: counts[k])
                pct = round(counts[top_intent] / total * 100)
                top_label = f"{pct}%"
            else:
                top_label = "0%"
        return {
            "status": "active" if total else "standby",
            "metrics": [
                {"label": "ROUTED", "value": str(total)},
                {"label": "TOP",    "value": top_label},
            ],
        }
    except Exception:
        return {
            "status": "standby",
            "metrics": [
                {"label": "ROUTED", "value": "—"},
                {"label": "TOP",    "value": "—"},
            ],
        }


# ── Snapshot endpoint ───────────────────────────────────────────────────────

def _safe(fn) -> dict:
    """Exécute un collecteur sans jamais propager d'exception au snapshot global."""
    try:
        return fn()
    except Exception:
        return {"status": "standby", "metrics": []}


@router.get("/v1/world/cards/snapshot")
def world_cards_snapshot() -> dict[str, Any]:
    """Aggregate metrics for all live-wired world cards in a single response.

    Les 12 collecteurs sont I/O-bound (FS, subprocess, état partagé). On les
    lance en parallèle dans un threadpool : la latence totale tombe au plus
    lent au lieu de la somme. Les scans vault (growth + orphans) partagent un
    cache verrouillé, donc une seule passe même en concurrence.
    """
    jobs = {
        # Forge
        "stl_output":        _stl_output_snapshot,
        # Commerce
        "approval_queue":    _approval_queue_snapshot,
        "token_budget":      _token_budget_snapshot,
        # Cyberdeck
        "gpu_temp":          _gpu_temp_snapshot,
        "error_log":         _error_log_snapshot,
        # Vault
        "vault_growth":      _vault_growth_snapshot,
        "orphan_alert":      _orphan_alert_snapshot,
        "morning_brief":     _morning_brief_snapshot,
        # Docker
        "disk_usage":        _disk_usage_snapshot,
        "container_logs":    _container_logs_snapshot,
        # Cyberdeck (state-tracked)
        "telegram_activity": _telegram_activity_snapshot,
        "model_routing":     _model_routing_snapshot,
    }
    out: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        futures = {ex.submit(_safe, fn): key for key, fn in jobs.items()}
        for fut, key in futures.items():
            out[key] = fut.result()
    out["generated_at"] = datetime.now().isoformat()
    return out

"""
trend_memory/store.py
Persistent trend memory: successful niches, failed tests, seasonal spikes.
Stored as JSON in trend_snapshots/trend_memory.json.
Thread-safe via in-process lock (single-process FastAPI).
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from trend_engine.scoring import TrendScore

_LOCK = threading.Lock()

_DEFAULT_PATH = Path(__file__).parent.parent / "trend_snapshots" / "trend_memory.json"

# ── Schema ────────────────────────────────────────────────────────────────────
#
# {
#   "niches": {
#     "cable management": {
#       "keyword":      str,
#       "status":       "WINNER" | "TESTING" | "FAILED" | "WATCHING",
#       "first_seen":   iso8601,
#       "last_updated": iso8601,
#       "peak_score":   float,
#       "scores_history": [float, ...],   # last 30 snapshots
#       "alert_level":  str,
#       "stage":        str,
#       "competition":  str,
#       "platforms":    [str, ...],
#       "notes":        str,
#       "seasonal_flags": [str, ...]   # e.g. ["christmas", "back-to-school"]
#     },
#     ...
#   },
#   "failed_niches":  [str, ...],   # keywords confirmed not worth pursuing
#   "seasonal_spikes": {
#     "christmas":      [str, ...],  # keywords that spike at Christmas
#     "summer":         [...],
#   },
#   "meta": {
#     "updated_at": iso8601,
#     "total_tracked": int,
#   }
# }


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"niches": {}, "failed_niches": [], "seasonal_spikes": {}, "meta": {}}


def _save(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["meta"] = {
        "updated_at":    _now_iso(),
        "total_tracked": len(data.get("niches", {})),
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Public API ────────────────────────────────────────────────────────────────

def record_trend(
    trend_score: TrendScore,
    status: str = "WATCHING",
    notes: str = "",
    path: Path | None = None,
) -> dict[str, Any]:
    """
    Upsert a trend into memory. Creates or updates the niche entry.

    status: "WINNER" | "TESTING" | "FAILED" | "WATCHING"
    Returns the saved niche dict.
    """
    path = path or _DEFAULT_PATH
    kw = trend_score.keyword.lower().strip()

    with _LOCK:
        data = _load(path)
        niches = data.setdefault("niches", {})

        existing = niches.get(kw, {})
        history  = existing.get("scores_history", [])
        history.append(trend_score.score)
        history = history[-30:]  # keep last 30

        peak = max(history)

        niches[kw] = {
            "keyword":        trend_score.keyword,
            "status":         status if status != "WATCHING" else existing.get("status", "WATCHING"),
            "first_seen":     existing.get("first_seen", _now_iso()),
            "last_updated":   _now_iso(),
            "peak_score":     peak,
            "scores_history": history,
            "alert_level":    trend_score.alert_level,
            "stage":          trend_score.stage,
            "competition":    trend_score.competition,
            "platforms":      trend_score.platforms,
            "notes":          notes or existing.get("notes", ""),
            "seasonal_flags": existing.get("seasonal_flags", []),
        }

        _save(data, path)
        return niches[kw]


def mark_winner(keyword: str, notes: str = "", path: Path | None = None) -> None:
    """Mark a keyword as a confirmed WINNER niche."""
    path = path or _DEFAULT_PATH
    with _LOCK:
        data = _load(path)
        kw = keyword.lower().strip()
        if kw in data.get("niches", {}):
            data["niches"][kw]["status"] = "WINNER"
            data["niches"][kw]["last_updated"] = _now_iso()
            if notes:
                data["niches"][kw]["notes"] = notes
        _save(data, path)


def mark_failed(keyword: str, reason: str = "", path: Path | None = None) -> None:
    """
    Mark a keyword as FAILED and add to failed_niches blacklist.
    Failed keywords are skipped in future hunts.
    """
    path = path or _DEFAULT_PATH
    with _LOCK:
        data = _load(path)
        kw = keyword.lower().strip()
        if kw in data.get("niches", {}):
            data["niches"][kw]["status"] = "FAILED"
            data["niches"][kw]["notes"]  = reason or data["niches"][kw].get("notes", "")
            data["niches"][kw]["last_updated"] = _now_iso()
        failed = data.setdefault("failed_niches", [])
        if kw not in failed:
            failed.append(kw)
        _save(data, path)


def add_seasonal_flag(keyword: str, season: str, path: Path | None = None) -> None:
    """
    Tag a keyword with a seasonal spike marker.
    season: e.g. "christmas", "summer", "back-to-school", "valentines"
    """
    path = path or _DEFAULT_PATH
    season = season.lower().strip()
    with _LOCK:
        data = _load(path)
        kw = keyword.lower().strip()
        # Update niche entry if it exists
        if kw in data.get("niches", {}):
            flags = data["niches"][kw].setdefault("seasonal_flags", [])
            if season not in flags:
                flags.append(season)
        # Also update seasonal_spikes index
        spikes = data.setdefault("seasonal_spikes", {})
        spikes.setdefault(season, [])
        if kw not in spikes[season]:
            spikes[season].append(kw)
        _save(data, path)


def get_niche(keyword: str, path: Path | None = None) -> dict | None:
    """Retrieve a stored niche by keyword (case-insensitive). None if not found."""
    path = path or _DEFAULT_PATH
    data = _load(path)
    return data.get("niches", {}).get(keyword.lower().strip())


def get_winners(path: Path | None = None) -> list[dict]:
    """Return all niches with status WINNER, sorted by peak_score desc."""
    path = path or _DEFAULT_PATH
    data = _load(path)
    winners = [v for v in data.get("niches", {}).values() if v.get("status") == "WINNER"]
    return sorted(winners, key=lambda x: -x.get("peak_score", 0))


def get_failed_niches(path: Path | None = None) -> list[str]:
    """Return list of failed keyword strings."""
    path = path or _DEFAULT_PATH
    return _load(path).get("failed_niches", [])


def get_seasonal_keywords(season: str, path: Path | None = None) -> list[str]:
    """Return keywords flagged for a given season."""
    path = path or _DEFAULT_PATH
    return _load(path).get("seasonal_spikes", {}).get(season.lower(), [])


def all_niches(path: Path | None = None) -> list[dict]:
    """Return all tracked niches sorted by last_updated (newest first)."""
    path = path or _DEFAULT_PATH
    data = _load(path)
    niches = list(data.get("niches", {}).values())
    return sorted(niches, key=lambda x: x.get("last_updated", ""), reverse=True)


def summary_stats(path: Path | None = None) -> dict[str, Any]:
    """Return summary statistics about stored trends."""
    path = path or _DEFAULT_PATH
    data = _load(path)
    niches = data.get("niches", {})
    by_status: dict[str, int] = {}
    for n in niches.values():
        s = n.get("status", "WATCHING")
        by_status[s] = by_status.get(s, 0) + 1

    return {
        "total_tracked": len(niches),
        "by_status":     by_status,
        "failed_count":  len(data.get("failed_niches", [])),
        "seasonal_tags": list(data.get("seasonal_spikes", {}).keys()),
        "updated_at":    data.get("meta", {}).get("updated_at", ""),
    }

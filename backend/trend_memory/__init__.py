"""
trend_memory/ — Persistent trend memory store.

Modules:
  store  — Record winners/failures, seasonal spikes, score history
"""
from .store import (
    add_seasonal_flag,
    all_niches,
    get_failed_niches,
    get_niche,
    get_seasonal_keywords,
    get_winners,
    mark_failed,
    mark_winner,
    record_trend,
    record_winner,
    summary_stats,
)

__all__ = [
    "record_trend", "record_winner", "mark_winner", "mark_failed", "add_seasonal_flag",
    "get_niche", "get_winners", "get_failed_niches", "get_seasonal_keywords",
    "all_niches", "summary_stats",
]

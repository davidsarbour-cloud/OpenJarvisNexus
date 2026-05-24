"""
trend_memory/ — Persistent trend memory store.

Modules:
  store  — Record winners/failures, seasonal spikes, score history
"""
from .store import (
    record_trend, mark_winner, mark_failed, add_seasonal_flag,
    get_niche, get_winners, get_failed_niches, get_seasonal_keywords,
    all_niches, summary_stats,
)

__all__ = [
    "record_trend", "mark_winner", "mark_failed", "add_seasonal_flag",
    "get_niche", "get_winners", "get_failed_niches", "get_seasonal_keywords",
    "all_niches", "summary_stats",
]

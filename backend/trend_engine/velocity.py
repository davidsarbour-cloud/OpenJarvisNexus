"""
trend_engine/velocity.py
Centralized velocity calculations across all platforms.
Single source of truth — no duplication with scrapers.

All normalize_* functions map raw platform metrics → 0.0–1.0.
"""
from __future__ import annotations

import math
from typing import Sequence

# ── Platform caps (raw value that maps to 1.0) ────────────────────────────────

_REDDIT_CAP   = 1_000.0    # upvotes/hour
_ETSY_CAP     = 5_000.0    # listing count (inverted: low count = high signal)
_TIKTOK_CAP   = 500_000.0  # views/hour
_GOOGLE_CAP   = 2.0        # ratio 7d/30d (2× breakout = max score)
_GENERIC_CAP  = 100.0      # generic score 0–100


# ── Normalization helpers ─────────────────────────────────────────────────────

def normalize_linear(value: float, cap: float) -> float:
    """Linear normalization: value/cap, capped at 1.0. Returns 0.0 for cap<=0."""
    if cap <= 0:
        return 0.0
    return min(value / cap, 1.0)


def normalize_log(value: float, cap: float) -> float:
    """
    Logarithmic normalization — more sensitive at the low end.
    Useful for values with a long tail (e.g. Reddit upvotes).
    Returns 0.0 for value<=0.
    """
    if value <= 0 or cap <= 0:
        return 0.0
    return min(math.log1p(value) / math.log1p(cap), 1.0)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(value, hi))


# ── Platform-specific normalizations ─────────────────────────────────────────

def normalize_reddit_velocity(upvotes_per_hour: float) -> float:
    """
    Reddit upvote velocity → 0.0–1.0.
    Cap: 1000 upvotes/hour = viral post.
    Uses log scale for sensitivity at low-engagement posts.
    """
    return round(normalize_log(upvotes_per_hour, _REDDIT_CAP), 4)


def normalize_tiktok_velocity(views_per_hour: float) -> float:
    """TikTok view velocity → 0.0–1.0. Cap: 500k views/hour."""
    return round(normalize_linear(views_per_hour, _TIKTOK_CAP), 4)


def normalize_google_breakout(ratio_7d_30d: float) -> float:
    """
    Google Trends breakout ratio (7d avg / 30d avg) → 0.0–1.0.
    1.0 = stable, 2.0 = doubling = full score.
    ratio < 1.0 (declining) → 0.0.
    """
    if ratio_7d_30d <= 0:
        return 0.0
    return round(clamp((ratio_7d_30d - 1.0) / (_GOOGLE_CAP - 1.0)), 4)


def normalize_etsy_listing_count(count: int) -> float:
    """
    Etsy listing count → competition score (0.0–1.0).
    Inverted: fewer listings = less competition = higher score.
    0–50 listings → near 1.0 (blue ocean)
    5000+ listings → near 0.0 (saturated)
    """
    if count <= 0:
        return 0.5  # unknown
    # Use log-inverse: ln(cap/count) / ln(cap/1)
    cap = 5000.0
    count_f = float(count)
    if count_f >= cap:
        return 0.0
    return round(math.log(cap / count_f) / math.log(cap), 4)


# ── Cross-platform velocity fusion ────────────────────────────────────────────

def fuse_velocity(
    reddit:  float = 0.0,   # already normalized 0–1
    tiktok:  float = 0.0,   # already normalized 0–1
    google:  float = 0.0,   # already normalized 0–1
    weights: dict[str, float] | None = None,
) -> float:
    """
    Weighted average of cross-platform velocity signals.

    Default weights: reddit 40%, tiktok 35%, google 25%.
    If a signal is missing (0.0), its weight is redistributed proportionally.

    Returns 0.0–1.0.
    """
    if weights is None:
        weights = {"reddit": 0.40, "tiktok": 0.35, "google": 0.25}

    signals = {
        "reddit": reddit,
        "tiktok": tiktok,
        "google": google,
    }

    # Only include signals with non-zero weight keys in weights dict
    total_w = 0.0
    weighted_sum = 0.0
    for k, w in weights.items():
        v = signals.get(k, 0.0)
        if v > 0.0:
            weighted_sum += v * w
            total_w += w

    if total_w <= 0:
        return 0.0
    # Normalize by actual weight used (handles missing platforms)
    return round(clamp(weighted_sum / total_w), 4)


# ── Momentum detection ────────────────────────────────────────────────────────

def detect_momentum(
    current_score: float,
    history: Sequence[float],
    window: int = 7,
) -> str:
    """
    Compare current score to recent history to detect trend momentum.

    Parameters
    ----------
    current_score : latest composite score (0.0–1.0)
    history       : list of past scores (oldest first)
    window        : how many past periods to average

    Returns
    -------
    "RISING"   — current > avg_history by >10%
    "FALLING"  — current < avg_history by >10%
    "STABLE"   — within ±10% of average
    "NEW"      — no history
    """
    if not history:
        return "NEW"
    recent = list(history)[-window:]
    avg = sum(recent) / len(recent)
    if avg == 0:
        return "NEW" if current_score > 0 else "STABLE"
    delta = (current_score - avg) / avg
    if delta > 0.10:
        return "RISING"
    if delta < -0.10:
        return "FALLING"
    return "STABLE"

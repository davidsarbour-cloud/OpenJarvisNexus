"""
trend_engine/scoring.py
Updated scoring formula + alert/stage/action logic.
Weights: intent 25%, velocity 30%, cross-platform 20%, competition_inv 15%, monetization 10%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Weights ───────────────────────────────────────────────────────────────────

WEIGHTS = {
    "velocity":        0.30,  # how fast it's spreading
    "intent":          0.25,  # buyer purchase signals
    "cross_platform":  0.20,  # validated on multiple sources
    "competition_inv": 0.15,  # inverse competition (low comp = high score)
    "monetization":    0.10,  # price point + STL/product viability
}

# W10 FIX: explicit check instead of assert (assert is stripped by python -O)
if abs(sum(WEIGHTS.values()) - 1.0) >= 1e-9:
    raise ValueError(f"WEIGHTS must sum to 1.0, got {sum(WEIGHTS.values())}")


# ── Alert levels ──────────────────────────────────────────────────────────────

ALERT_THRESHOLDS = {
    "HIGH":   70,
    "MEDIUM": 40,
    "WATCH":  20,
    "NOISE":   0,
}

ALERT_EMOJIS = {
    "HIGH":   "🔥",
    "MEDIUM": "⚠️",
    "WATCH":  "👁️",
    "NOISE":  "💤",
}


# ── Stage / action labels ─────────────────────────────────────────────────────

def get_stage(score: float, competition: str) -> str:
    """
    Map score + competition to funnel stage.
    """
    score_int = int(score)
    comp = competition.upper()

    if score_int >= 70:
        if comp in ("LOW", "UNKNOWN"):
            return "BUILD"
        if comp == "MEDIUM":
            return "VALIDATE"
        return "DIFFERENTIATE"  # HIGH/SATURATED but high demand
    if score_int >= 40:
        if comp in ("LOW", "UNKNOWN"):
            return "VALIDATE"
        return "RESEARCH"
    if score_int >= 20:
        return "WATCH"
    return "IGNORE"


def get_action(stage: str) -> str:
    """Human-readable recommended action derived from stage."""
    stage_upper = stage.upper()
    actions = {
        "BUILD":         "Build product — high demand, low competition",
        "VALIDATE":      "Test with small batch — demand confirmed",
        "DIFFERENTIATE": "Enter with unique angle — saturated but proven demand",
        "RESEARCH":      "Deep dive — promising signal, needs validation",
        "WATCH":         "Monitor 7 days — early signal, not confirmed",
        "IGNORE":        "Skip — insufficient signal",
    }
    return actions.get(stage_upper, "Monitor")


def get_alert_level(score: float) -> tuple[str, str]:
    """Returns (level_name, emoji)."""
    score_int = int(score)
    for level, threshold in sorted(ALERT_THRESHOLDS.items(), key=lambda x: -x[1]):
        if score_int >= threshold:
            return level, ALERT_EMOJIS[level]
    return "NOISE", ALERT_EMOJIS["NOISE"]


# ── Monetization signal ───────────────────────────────────────────────────────

_MONETIZATION_KEYWORDS: dict[str, float] = {
    # High-price niches
    "ergonomic": 0.9, "standing desk": 0.9, "gaming": 0.8, "custom":  0.8,
    "personalized": 0.85, "leather": 0.85, "bamboo": 0.75, "minimal": 0.7,
    "organize": 0.7, "organizer": 0.75, "cable":  0.7,  "desk":  0.65,
    "wedding": 0.85, "gift": 0.8, "pet": 0.75, "baby": 0.8, "home": 0.6,
    # STL / 3D print niches
    "stl": 0.8, "3d print": 0.75, "filament": 0.7, "resin": 0.7,
    # Low-price (lower score)
    "generic": 0.3, "basic": 0.3, "simple": 0.4,
}


def monetization_score(keyword: str) -> float:
    """
    Estimate monetization potential from keyword (0.0–1.0).
    Based on known high-margin niche words. Defaults to 0.5 (neutral).
    """
    kw_lower = keyword.lower()
    best = 0.5  # neutral default
    for k, v in _MONETIZATION_KEYWORDS.items():
        if k in kw_lower:
            best = max(best, v)
    return round(best, 4)


# ── Main score function ───────────────────────────────────────────────────────

@dataclass
class TrendScore:
    keyword:         str
    score:           float              # 0.0–100.0
    alert_level:     str                # HIGH / MEDIUM / WATCH / NOISE
    alert_emoji:     str
    stage:           str                # BUILD / VALIDATE / etc.
    action:          str
    components:      dict[str, float]   # sub-scores
    competition:     str                # LOW / MEDIUM / HIGH / SATURATED
    platforms:       list[str] = field(default_factory=list)
    momentum:        str = "STABLE"     # RISING / FALLING / STABLE / NEW


def compute_trend_score(
    keyword:         str,
    velocity:        float,            # normalized 0.0–1.0 (cross-platform avg)
    intent_score:    float,            # normalized 0.0–1.0
    n_platforms:     int,              # number of platforms with signal
    competition:     str = "UNKNOWN",  # LOW / MEDIUM / HIGH / SATURATED / UNKNOWN
    competition_score: float | None = None,  # override (from etsy_signal)
    momentum:        str = "STABLE",
    extra: dict[str, Any] | None = None,
) -> TrendScore:
    """
    Compute composite trend score.

    Parameters
    ----------
    velocity          : fused velocity signal 0.0–1.0
    intent_score      : buyer intent 0.0–1.0
    n_platforms       : 1–4 (reddit, etsy, tiktok, google)
    competition       : string label from Etsy scraper
    competition_score : optional override for competition_inv component
    momentum          : from velocity.detect_momentum
    extra             : dict with optional "monetization" key (0.0–1.0)

    Returns
    -------
    TrendScore dataclass with score 0–100
    """
    extra = extra or {}

    # Cross-platform signal: 1 platform = 0.25, 2 = 0.5, 3 = 0.75, 4 = 1.0
    cross_platform = min(n_platforms / 4.0, 1.0)

    # Competition inverse
    if competition_score is not None:
        comp_inv = competition_score
    else:
        comp_inv = {
            "LOW":       1.0,
            "MEDIUM":    0.6,
            "HIGH":      0.3,
            "SATURATED": 0.1,
            "UNKNOWN":   0.5,
        }.get(competition.upper(), 0.5)

    # Monetization
    mono = extra.get("monetization", monetization_score(keyword))

    # Weighted sum
    raw = (
        WEIGHTS["velocity"]        * velocity
        + WEIGHTS["intent"]          * intent_score
        + WEIGHTS["cross_platform"]  * cross_platform
        + WEIGHTS["competition_inv"] * comp_inv
        + WEIGHTS["monetization"]    * mono
    )

    # Scale to 0–100
    score_100 = round(raw * 100, 1)
    score_100 = max(0.0, min(100.0, score_100))

    alert_level, alert_emoji = get_alert_level(score_100)
    stage  = get_stage(score_100, competition)
    action = get_action(stage)

    components = {
        "velocity":        round(velocity, 4),
        "intent":          round(intent_score, 4),
        "cross_platform":  round(cross_platform, 4),
        "competition_inv": round(comp_inv, 4),
        "monetization":    round(mono, 4),
    }

    return TrendScore(
        keyword=keyword,
        score=score_100,
        alert_level=alert_level,
        alert_emoji=alert_emoji,
        stage=stage,
        action=action,
        components=components,
        competition=competition,
        momentum=momentum,
    )

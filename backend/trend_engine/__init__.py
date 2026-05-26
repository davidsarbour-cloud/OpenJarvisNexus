"""
trend_engine/ — Core scoring and fusion logic.

Modules:
  sentiment  — Buyer intent phrases + scan functions (SINGLE SOURCE OF TRUTH)
  velocity   — Normalized velocity calculations for all platforms
  scoring    — Composite TrendScore computation (weights, alerts, stages)
  fusion     — Cross-platform signal fusion → TrendScore
"""
from .fusion import fuse_signals, signals_summary
from .scoring import (
    ALERT_THRESHOLDS,
    WEIGHTS,
    TrendScore,
    compute_trend_score,
    get_action,
    get_alert_level,
    get_stage,
)
from .sentiment import INTENT_PHRASES, STL_INTENT_PHRASES, VIRAL_HOOKS, scan_intent, score_intent
from .velocity import (
    detect_momentum,
    fuse_velocity,
    normalize_google_breakout,
    normalize_reddit_velocity,
)

__all__ = [
    "INTENT_PHRASES", "VIRAL_HOOKS", "STL_INTENT_PHRASES", "scan_intent", "score_intent",
    "fuse_velocity", "normalize_reddit_velocity", "normalize_google_breakout", "detect_momentum",
    "WEIGHTS", "ALERT_THRESHOLDS", "compute_trend_score", "TrendScore",
    "get_action", "get_alert_level", "get_stage",
    "fuse_signals", "signals_summary",
]

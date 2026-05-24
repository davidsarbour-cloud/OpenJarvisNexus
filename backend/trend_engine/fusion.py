"""
trend_engine/fusion.py
Cross-platform signal fusion.
Takes raw signals from all scrapers and fuses them into a unified TrendScore.
"""
from __future__ import annotations

from typing import Any

from trend_engine.velocity import (
    fuse_velocity, normalize_reddit_velocity,
    normalize_google_breakout, normalize_etsy_listing_count, detect_momentum,
)
from trend_engine.scoring import compute_trend_score, TrendScore


# ── Fusion entry point ────────────────────────────────────────────────────────

def fuse_signals(
    keyword:    str,
    reddit:     dict[str, Any] | None = None,
    etsy:       dict[str, Any] | None = None,
    tiktok:     dict[str, Any] | None = None,
    google:     dict[str, Any] | None = None,
    stl:        dict[str, Any] | None = None,
    history:    list[float] | None = None,
    extra:      dict[str, Any] | None = None,
) -> TrendScore:
    """
    Fuse signals from multiple scrapers into a single TrendScore.

    Parameters (all optional — gracefully handles missing platforms)
    ----------
    reddit  : dict from reddit_scraper.reddit_signal()
    etsy    : dict from etsy_scraper.etsy_signal()
    tiktok  : dict from tiktok_scraper.tiktok_signal()
    google  : dict from trend_hunter._google_trends_signal() or google_signal()
    stl     : dict from STL/local snapshot signal
    history : past composite scores for momentum detection
    extra   : arbitrary overrides (e.g. {"monetization": 0.9})

    Returns
    -------
    TrendScore with fused composite score
    """
    platforms_active: list[str] = []

    # ── Reddit ────────────────────────────────────────────────────────────────
    reddit_vel        = 0.0
    reddit_intent     = 0.0
    reddit_unique_subs = 0

    if reddit and not reddit.get("error") and reddit.get("post_count", 0) > 0:
        platforms_active.append("reddit")
        reddit_vel        = normalize_reddit_velocity(reddit.get("velocity_raw", 0.0))
        reddit_intent     = float(reddit.get("intent_score", 0.0))
        reddit_unique_subs = int(reddit.get("unique_subs", 0))

    # ── Etsy ──────────────────────────────────────────────────────────────────
    etsy_comp_score = 0.5     # neutral default
    etsy_comp_level = "UNKNOWN"
    etsy_jackpot    = False

    if etsy and not etsy.get("error"):
        count        = int(etsy.get("listing_count", 0))
        etsy_jackpot = bool(etsy.get("jackpot", False))
        etsy_comp_level = etsy.get("competition_level", "UNKNOWN")
        # W9 FIX: only count Etsy as active platform when we have real data
        if count > 0 or etsy_jackpot:
            platforms_active.append("etsy")
            etsy_comp_score = (
                normalize_etsy_listing_count(count) if count > 0
                else float(etsy.get("competition_score", 0.5))
            )

    # ── TikTok ────────────────────────────────────────────────────────────────
    tiktok_vel = 0.0
    tiktok_intent = 0.0
    tiktok_viral  = 0

    if tiktok and not tiktok.get("error") and tiktok.get("video_count", 0) > 0:
        platforms_active.append("tiktok")
        tiktok_vel    = float(tiktok.get("velocity_norm", 0.0))
        tiktok_intent = float(tiktok.get("intent_score", 0.0))
        tiktok_viral  = int(tiktok.get("viral_hits", 0))

    # ── Google Trends ─────────────────────────────────────────────────────────
    google_vel = 0.0

    if google and not google.get("error"):
        platforms_active.append("google")
        ratio = float(google.get("ratio", google.get("breakout_ratio", 0.0)))
        google_vel = normalize_google_breakout(ratio)

    # ── STL local ─────────────────────────────────────────────────────────────
    stl_present = False
    if stl and not stl.get("error"):
        stl_present = bool(stl.get("found", False))
        if stl_present:
            platforms_active.append("stl")

    # ── Fuse velocity ─────────────────────────────────────────────────────────
    fused_vel = fuse_velocity(
        reddit=reddit_vel,
        tiktok=tiktok_vel,
        google=google_vel,
    )

    # ── Intent fusion (weighted avg of reddit + tiktok) ──────────────────────
    intent_signals = []
    if reddit and not reddit.get("error") and reddit.get("post_count", 0) > 0:
        intent_signals.append(reddit_intent)
    if tiktok and not tiktok.get("error") and tiktok.get("video_count", 0) > 0:
        intent_signals.append(tiktok_intent)
    fused_intent = sum(intent_signals) / len(intent_signals) if intent_signals else 0.0

    # ── Jackpot bonus ─────────────────────────────────────────────────────────
    # Etsy jackpot = proven demand → boost intent score
    if etsy_jackpot:
        fused_intent = min(fused_intent + 0.15, 1.0)

    # ── Momentum ──────────────────────────────────────────────────────────────
    momentum = detect_momentum(fused_vel, history or [])

    # ── Cross-platform count ──────────────────────────────────────────────────
    n_platforms = len(platforms_active)

    # ── Build extra payload ───────────────────────────────────────────────────
    extra_payload = dict(extra or {})
    extra_payload.update({
        "reddit_unique_subs": reddit_unique_subs,
        "tiktok_viral_hits":  tiktok_viral,
        "stl_present":        stl_present,
        "jackpot":            etsy_jackpot,
        "platforms_active":   platforms_active,
    })

    # ── Compute ───────────────────────────────────────────────────────────────
    ts = compute_trend_score(
        keyword=keyword,
        velocity=fused_vel,
        intent_score=fused_intent,
        n_platforms=n_platforms,
        competition=etsy_comp_level,
        competition_score=etsy_comp_score,
        momentum=momentum,
        extra=extra_payload,
    )
    ts.platforms = platforms_active
    ts.momentum  = momentum
    return ts


def signals_summary(ts: TrendScore) -> dict[str, Any]:
    """
    Flatten TrendScore to a JSON-serializable dict for storage/API.
    """
    return {
        "keyword":        ts.keyword,
        "score":          ts.score,
        "alert_level":    ts.alert_level,
        "alert_emoji":    ts.alert_emoji,
        "stage":          ts.stage,
        "action":         ts.action,
        "competition":    ts.competition,
        "momentum":       ts.momentum,
        "platforms":      ts.platforms,
        "components":     ts.components,
    }

"""
Trend Hunter v2 — Nexus9
Pipeline: SOURCES → SIGNAL EXTRACTION → VELOCITY → INTENT → CROSS-PLATFORM → SCORING → ALERT

Sources:
  ✅ Reddit        — velocity (upvotes/h), buyer intent phrases  [scrapers.reddit_scraper]
  ✅ Google Trends — breakout 7d vs 30d (pytrends)              [google_trends_signal]
  ✅ Etsy          — competition proxy, jackpot detection        [scrapers.etsy_scraper]
  ✅ TikTok        — view velocity, viral hooks                  [scrapers.tiktok_scraper]
  ✅ STL snapshots — données locales research_logs/              [_stl_signal]
  ✅ Yahoo Finance — stocks / crypto (no API key)                [_fetch_yahoo]

Scoring/fusion:    trend_engine.scoring + trend_engine.fusion + trend_engine.velocity
Intent phrases:    trend_engine.sentiment
Memory:            trend_memory.store

Endpoints:
  POST /v1/trends/hunt          — full hunt + snapshot
  GET  /v1/trends/latest        — last snapshot
  GET  /v1/trends/history       — snapshot list
  POST /v1/trends/score/{kw}    — score single keyword on demand
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter
from scrapers.etsy_scraper import etsy_signal

# ── New modular imports (no duplication) ─────────────────────────────────────
from scrapers.reddit_scraper import reddit_signal
from scrapers.tiktok_scraper import tiktok_signal
from trend_engine.fusion import fuse_signals, signals_summary
from trend_engine.scoring import ALERT_THRESHOLDS
from trend_memory.store import record_trend

router = APIRouter(prefix="/v1/trends", tags=["trends"])

BACKEND_DIR = Path(__file__).parent


# ── Config ────────────────────────────────────────────────────────────────────

def _cfg() -> dict:
    f = BACKEND_DIR / "config.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except Exception:
        return {}

def _hunter_cfg() -> dict:
    return _cfg().get("trend_hunter", {})

def _snapshot_dir() -> Path:
    d = BACKEND_DIR / _hunter_cfg().get("snapshot_dir", "trend_snapshots")
    d.mkdir(exist_ok=True)
    return d


# ── Google Trends (kept here: pytrends-specific, not worth a separate file) ──

def _google_trends_sync(keyword: str) -> dict[str, Any]:
    """
    Breakout detection: interest 7d avg vs 30d avg.
    Returns ratio, breakout flag, normalized 0-1 signal.
    Synchronous — call via asyncio.to_thread.
    """
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=300, timeout=(10, 25), retries=2, backoff_factor=0.5)
        pt.build_payload([keyword], cat=0, timeframe="today 1-m", geo="", gprop="")
        df = pt.interest_over_time()

        if df is None or df.empty or keyword not in df.columns:
            return {"keyword": keyword, "error": "no_data", "ratio": 0.0, "breakout": False}

        series  = df[keyword].tolist()
        avg_30d = sum(series) / max(len(series), 1)
        avg_7d  = sum(series[-7:]) / max(min(len(series), 7), 1)
        ratio   = avg_7d / max(avg_30d, 1)
        breakout = ratio >= 1.5

        return {
            "keyword":  keyword,
            "avg_30d":  round(avg_30d, 1),
            "avg_7d":   round(avg_7d, 1),
            "ratio":    round(ratio, 2),
            "breakout": breakout,
            "peak":     max(series),
        }
    except Exception as e:
        return {"keyword": keyword, "error": str(e), "ratio": 0.0, "breakout": False}


async def _google_trends_signal(keyword: str) -> dict[str, Any]:
    """Async wrapper for _google_trends_sync."""
    return await asyncio.to_thread(_google_trends_sync, keyword)


# ── STL local snapshots (kept here: local file lookup) ───────────────────────

def _stl_signal(keyword: str) -> dict[str, Any]:
    """Check if keyword appears in local STL research_logs/ snapshots."""
    research_dir = BACKEND_DIR / "research_logs"
    if not research_dir.exists():
        return {"keyword": keyword, "found": False, "hits": 0}

    snaps    = sorted(research_dir.glob("*.json"), reverse=True)[:3]
    kw_lower = keyword.lower()
    hits     = 0

    for snap in snaps:
        try:
            data = json.loads(snap.read_text(encoding="utf-8"))
            for source_key in ("thingiverse", "cults3d", "etsy"):
                items = data.get(source_key, [])
                if isinstance(items, list):
                    for item in items:
                        if kw_lower in item.get("title", "").lower():
                            hits += 1
        except Exception:
            pass

    return {"keyword": keyword, "found": hits > 0, "hits": hits}


# ── Yahoo Finance (no API key) ────────────────────────────────────────────────

async def _fetch_yahoo(client: httpx.AsyncClient, symbol: str) -> dict[str, Any]:
    """Fetch latest Yahoo Finance quote — no API key required."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
    try:
        r = await client.get(url, timeout=10)
        if r.status_code != 200:
            return {"symbol": symbol, "error": f"HTTP {r.status_code}"}

        result = r.json().get("chart", {}).get("result", [None])[0]
        if not result:
            return {"symbol": symbol, "error": "empty_response"}

        meta       = result.get("meta", {})
        price      = float(meta.get("regularMarketPrice") or 0)
        prev       = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
        change     = price - prev
        change_pct = (change / prev * 100) if prev else 0.0
        closes_raw = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes     = [round(c, 4) for c in closes_raw if c is not None]

        return {
            "symbol":       symbol,
            "name":         meta.get("shortName", symbol),
            "price":        round(price, 4),
            "prev_close":   round(prev, 4),
            "change":       round(change, 4),
            "change_pct":   round(change_pct, 2),
            "currency":     meta.get("currency", "USD"),
            "history_5d":   closes[-5:],
            "market_state": meta.get("marketState", "UNKNOWN"),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# KEYWORD HUNT — uses fusion engine
# ─────────────────────────────────────────────────────────────────────────────

async def _hunt_keyword(
    client:     httpx.AsyncClient,
    keyword:    str,
    subreddits: list[str],
    save_to_memory: bool = True,
) -> dict[str, Any]:
    """
    Full analysis of a keyword across all sources.
    Uses fusion engine for scoring — no duplication of scoring logic here.
    """
    # Run all sources in parallel
    reddit_coro  = reddit_signal(client, keyword, subreddits=None, fetch_comments=False)
    etsy_coro    = etsy_signal(client, keyword)
    tiktok_coro  = tiktok_signal(client, keyword, check_hashtag=False)
    google_coro  = _google_trends_signal(keyword)
    stl_result   = await asyncio.to_thread(_stl_signal, keyword)

    reddit_r, etsy_r, tiktok_r, google_r = await asyncio.gather(
        reddit_coro, etsy_coro, tiktok_coro, google_coro,
        return_exceptions=True,
    )

    # Coerce exceptions to error dicts
    if isinstance(reddit_r, Exception):
        reddit_r = {"error": str(reddit_r), "post_count": 0}
    if isinstance(etsy_r, Exception):
        etsy_r = {"error": str(etsy_r)}
    if isinstance(tiktok_r, Exception):
        tiktok_r = {"error": str(tiktok_r), "video_count": 0}
    if isinstance(google_r, Exception):
        google_r = {"error": str(google_r), "ratio": 0.0}

    # Fuse all signals into a TrendScore
    ts = fuse_signals(
        keyword=keyword,
        reddit=reddit_r,
        etsy=etsy_r,
        tiktok=tiktok_r,
        google=google_r,
        stl=stl_result,
    )

    # Persist to trend memory (non-blocking)
    if save_to_memory:
        try:
            record_trend(ts, status="WATCHING")
        except Exception as e:
            print(f"[trend_hunter] memory record failed: {e}")

    # Build backward-compatible output dict
    summary = signals_summary(ts)
    summary.update({
        "trend":           keyword,
        "alert":           f"{ts.alert_emoji} {ts.alert_level}",
        "buyer_intent":    (
            "HIGH" if ts.components.get("intent", 0) >= 0.6
            else "MED" if ts.components.get("intent", 0) >= 0.3
            else "LOW"
        ),
        "cross_validated": len(ts.platforms) >= 2,
        "n_platforms":     len(ts.platforms),
        "signals": {
            "reddit":        reddit_r,
            "etsy":          etsy_r,
            "tiktok":        tiktok_r,
            "google_trends": google_r,
            "stl":           stl_result,
        },
    })
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# FULL HUNT
# ─────────────────────────────────────────────────────────────────────────────

async def run_trend_hunt() -> dict[str, Any]:
    """
    Full hunt: tickers + dropshipping keywords.
    Persists snapshot JSON and returns result.
    """
    hcfg = _hunter_cfg()
    if not hcfg.get("enabled", True):
        return {"enabled": False, "message": "trend_hunter disabled in config.json"}

    tickers    = hcfg.get("tickers", [])
    crypto     = hcfg.get("crypto", [])
    keywords   = hcfg.get("dropshipping_keywords", [])
    subreddits = hcfg.get("reddit_subreddits", [])

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:

        all_symbols  = tickers + crypto
        ticker_coros = [_fetch_yahoo(client, s) for s in all_symbols]
        kw_coros     = [_hunt_keyword(client, kw, subreddits) for kw in keywords]

        all_results = await asyncio.gather(
            *ticker_coros, *kw_coros,
            return_exceptions=True,
        )

    n_tickers = len(all_symbols)

    tickers_data: dict[str, Any] = {}
    for sym, res in zip(all_symbols, all_results[:n_tickers]):
        tickers_data[sym] = {"symbol": sym, "error": str(res)} if isinstance(res, Exception) else res

    trends_list: list[dict] = []
    for kw, res in zip(keywords, all_results[n_tickers:]):
        if isinstance(res, Exception):
            trends_list.append({"trend": kw, "score": 0, "error": str(res)})
        else:
            trends_list.append(res)

    trends_list.sort(key=lambda x: x.get("score", 0), reverse=True)

    opportunities = [
        {
            "trend":        t["trend"],
            "score":        t["score"],
            "alert":        t.get("alert", "💤 NOISE"),
            "stage":        t.get("stage", "?"),
            "platforms":    t.get("platforms", []),
            "buyer_intent": t.get("buyer_intent", "LOW"),
            "competition":  t.get("competition", "UNKNOWN"),
            "action":       t.get("action", "Monitor"),
        }
        for t in trends_list
        if t.get("score", 0) >= ALERT_THRESHOLDS["WATCH"]
    ]

    snapshot: dict[str, Any] = {
        "timestamp":     datetime.now().isoformat(),
        "tickers":       tickers_data,
        "trends":        trends_list,
        "opportunities": opportunities,
        "_meta": {
            "symbols_fetched": len(all_symbols),
            "keywords_scored": len(keywords),
            "opportunities":   len(opportunities),
        },
    }

    today     = datetime.now().strftime("%Y-%m-%d")
    snap_file = _snapshot_dir() / f"trends-{today}.json"
    snap_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"[trend_hunter] Snapshot -> {snap_file.name} | "
        f"{len(all_symbols)} tickers | {len(keywords)} keywords | "
        f"{len(opportunities)} opportunities"
    )
    return snapshot


# ── On-demand single keyword ──────────────────────────────────────────────────

async def score_single_keyword(keyword: str) -> dict[str, Any]:
    """Score a single keyword with all sources, without saving a snapshot."""
    hcfg       = _hunter_cfg()
    subreddits = hcfg.get("reddit_subreddits", []) or ["entrepreneur", "dropship"]
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        return await _hunt_keyword(client, keyword, subreddits, save_to_memory=False)


async def get_latest_snapshot() -> dict[str, Any]:
    """Return most recent snapshot from disk."""
    snaps = sorted(_snapshot_dir().glob("trends-*.json"), reverse=True)
    if not snaps:
        return {
            "error": "No snapshot available",
            "tip":   "POST /v1/trends/hunt to create one",
        }
    try:
        data = json.loads(snaps[0].read_text(encoding="utf-8"))
        data["_snapshot_file"] = snaps[0].name
        return data
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/hunt")
async def trends_hunt():
    """Full hunt (tickers + keywords) — saves snapshot and returns it."""
    return await run_trend_hunt()


@router.get("/latest")
async def trends_latest():
    """Return last trend snapshot without re-fetching."""
    return await get_latest_snapshot()


@router.get("/history")
async def trends_history():
    """List all available snapshots."""
    snaps = sorted(_snapshot_dir().glob("trends-*.json"), reverse=True)
    return {"count": len(snaps), "snapshots": [s.name for s in snaps]}


@router.post("/score/{keyword:path}")
async def trends_score_keyword(keyword: str):
    """Score a specific keyword on demand (no snapshot saved)."""
    return await score_single_keyword(keyword)

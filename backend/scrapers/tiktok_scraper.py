"""
scrapers/tiktok_scraper.py
TikTok signal: view velocity, viral hook detection, hashtag spread.

Strategy:
  Level 1 — httpx semi-public API   → if blocked/empty
  Level 2 — Playwright headless     → renders search page + scrolls
             (TikTok is heavily JS-rendered, Playwright is PRIMARY)

Human simulation:
  - Random delays between 2–7s
  - Scroll simulation
  - Stealth fingerprint (Brave/Chrome)
"""
from __future__ import annotations

import os
import random
import re
import time
from typing import Any

import httpx

from trend_engine.sentiment import scan_viral, scan_intent, score_intent
from scrapers.browser import get_browser_context, human_delay, slow_scroll


# ── View count parsing ────────────────────────────────────────────────────────

def _parse_view_count(raw: Any) -> int:
    """Parse TikTok view count: int, '1.2M', '500K', '1,234'."""
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    if isinstance(raw, str):
        raw = raw.strip().upper()
        try:
            if raw.endswith("M"):
                return int(float(raw[:-1]) * 1_000_000)
            if raw.endswith("K"):
                return int(float(raw[:-1]) * 1_000)
            return int(raw.replace(",", ""))
        except ValueError:
            pass
    return 0


def _velocity_from_videos(videos: list[dict]) -> float:
    """Average view velocity (views/hour) → normalized 0.0–1.0. Cap 500k/h."""
    now    = time.time()
    cutoff = now - (72 * 3600)
    velocities: list[float] = []
    for v in videos:
        created = v.get("createTime", 0) or v.get("create_time", 0)
        views   = _parse_view_count(
            v.get("stats", {}).get("playCount", 0)
            or v.get("play_count", 0) or 0
        )
        if not created or created < cutoff:
            continue
        age_h = max((now - created) / 3600, 0.1)
        velocities.append(views / age_h)
    if not velocities:
        return 0.0
    raw = sum(velocities) / len(velocities)
    return round(min(raw / 500_000, 1.0), 4)


def _extract_hashtags(videos: list[dict]) -> list[str]:
    tags: set[str] = set()
    for v in videos:
        for ch in v.get("challenges", []):
            t = ch.get("title", "")
            if t:
                tags.add(t.lower())
        desc = v.get("desc", "") or v.get("description", "")
        for tag in re.findall(r'#(\w+)', desc):
            tags.add(tag.lower())
    return sorted(tags)[:20]


# ── Level 1 — httpx semi-public API ──────────────────────────────────────────

def _tiktok_headers() -> dict[str, str]:
    session_id = os.environ.get("TIKTOK_SESSION_ID", "")
    h = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.tiktok.com/",
    }
    if session_id:
        h["Cookie"] = f"sessionid={session_id}"
    return h


async def _tiktok_api(
    client: httpx.AsyncClient,
    keyword: str,
    count: int = 20,
) -> tuple[list[dict], str | None]:
    url = "https://www.tiktok.com/api/search/general/full/"
    params = {"keyword": keyword, "count": count, "type": 1}
    try:
        r = await client.get(url, headers=_tiktok_headers(), params=params, timeout=12)
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", [])
            videos = []
            for item in items:
                v = item.get("item", item.get("video", item))
                if isinstance(v, dict):
                    videos.append(v)
            return videos, None
        return [], f"HTTP {r.status_code}"
    except Exception as e:
        return [], str(e)


# ── Level 2 — Playwright ──────────────────────────────────────────────────────

async def _tiktok_playwright(keyword: str) -> tuple[list[dict], str | None]:
    """
    Playwright scraper for TikTok search.
    Navigates to tiktok.com/search, scrolls to load videos,
    extracts video metadata from the rendered DOM.
    """
    url = f"https://www.tiktok.com/search?q={keyword.replace(' ', '%20')}"

    try:
        async with get_browser_context(
            extra_headers={"Referer": "https://www.tiktok.com/"}
        ) as ctx:
            page = await ctx.new_page()

            # Intercept: block heavy media but keep JSON API calls
            await page.route(
                "**/*.{mp4,webm,m3u8}",
                lambda r: r.abort(),
            )

            # Navigate to search
            await page.goto(url, wait_until="networkidle", timeout=25_000)
            await human_delay(2.0, 4.0)

            # Scroll to trigger lazy loading of video cards
            await slow_scroll(page, steps=random.randint(3, 6))
            await human_delay(1.5, 3.0)

            # Extract video cards from the DOM
            videos = await page.evaluate("""
                () => {
                    const cards = document.querySelectorAll(
                        '[data-e2e="search_video-item"], ' +
                        '.tiktok-x6y88p-DivItemContainerV2, ' +
                        '[class*="DivItemContainer"]'
                    );
                    const results = [];
                    cards.forEach(card => {
                        try {
                            const descEl = card.querySelector(
                                '[data-e2e="search-card-desc"], ' +
                                '.tiktok-j2a19z-SpanText, ' +
                                'span[class*="SpanText"]'
                            );
                            const viewEl = card.querySelector(
                                '[data-e2e="video-views"], ' +
                                'strong[class*="StrongVideoCount"]'
                            );
                            const likeEl = card.querySelector(
                                '[data-e2e="like-count"], ' +
                                'strong[class*="StrongLikeCount"]'
                            );
                            const timeEl = card.querySelector('time');
                            const desc  = descEl ? descEl.innerText : '';
                            const views = viewEl ? viewEl.innerText : '0';
                            const likes = likeEl ? likeEl.innerText : '0';
                            if (desc) {
                                results.push({
                                    desc:         desc,
                                    play_count:   views,
                                    like_count:   likes,
                                    createTime:   timeEl ? (Date.parse(timeEl.dateTime)/1000 || 0) : 0,
                                });
                            }
                        } catch(e) {}
                    });
                    return results;
                }
            """)

            await page.close()
            return videos or [], None

    except Exception as e:
        return [], f"playwright: {e}"


# ── Main signal function ──────────────────────────────────────────────────────

async def tiktok_signal(
    client: httpx.AsyncClient,
    keyword: str,
    check_hashtag: bool = True,
    force_playwright: bool = False,
) -> dict[str, Any]:
    """
    TikTok signal for a keyword.

    Level 1: httpx API (fast)
    Level 2: Playwright (if API blocked — TikTok's primary path)

    Returns view velocity, viral hook count, intent score.
    """
    videos: list[dict] = []
    api_error: str | None = None

    # Level 1 — httpx API
    if not force_playwright:
        videos, api_error = await _tiktok_api(client, keyword)

    # Level 2 — Playwright fallback (or primary if API blocked)
    if not videos:
        pw_videos, pw_error = await _tiktok_playwright(keyword)
        if pw_videos:
            videos = pw_videos
            api_error = None  # Playwright succeeded
        elif not api_error:
            api_error = pw_error

    if not videos:
        return _empty_result(keyword, error=api_error)

    # Extract descriptions for intent scanning
    texts: list[str] = []
    for v in videos:
        desc = v.get("desc", "") or v.get("description", "")
        if desc:
            texts.append(desc)

    viral_hits,  _ = scan_viral(texts)
    intent_hits, _ = scan_intent(texts)
    intent_score   = score_intent(intent_hits, len(texts)) if texts else 0.0

    velocity_norm = _velocity_from_videos(videos)
    hashtags      = _extract_hashtags(videos)

    view_counts = sorted(
        [_parse_view_count(
            v.get("stats", {}).get("playCount", 0)
            or v.get("play_count", 0) or 0
        ) for v in videos],
        reverse=True,
    )

    return {
        "keyword":       keyword,
        "video_count":   len(videos),
        "velocity_norm": velocity_norm,
        "viral_hits":    viral_hits,
        "intent_hits":   intent_hits,
        "intent_score":  round(intent_score, 4),
        "hashtags":      hashtags[:10],
        "top_views":     view_counts[:5],
        "error":         api_error,
    }


def _empty_result(keyword: str, error: str | None = None) -> dict[str, Any]:
    return {
        "keyword":       keyword,
        "video_count":   0,
        "velocity_norm": 0.0,
        "viral_hits":    0,
        "intent_hits":   0,
        "intent_score":  0.0,
        "hashtags":      [],
        "top_views":     [],
        "error":         error,
    }

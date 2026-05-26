"""
scrapers/reddit_scraper.py
Reddit signal: posts + top comments, velocity (upvotes/hour), intent detection.
No PRAW dependency — pure httpx against reddit JSON API.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Any

import httpx
from trend_engine.sentiment import scan_intent, score_intent
from trend_engine.velocity import normalize_reddit_velocity as _norm_vel

_REDDIT_HEADERS = {
    "User-Agent":      "nexus9-trend-hunter/2.0 (contact: d3dprintix@outlook.com)",
    "Accept":          "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

# Level 2 — Randomization: polite inter-request delay
async def _polite_delay(min_s: float = 1.5, max_s: float = 4.0) -> None:
    """Random sleep between Reddit API calls to avoid rate-limit."""
    await asyncio.sleep(random.uniform(min_s, max_s))

_DEFAULT_LIMIT   = 25     # posts per fetch
_COMMENT_LIMIT   = 10     # top-level comments per post
_MAX_COMMENT_AGE = 72     # hours — ignore very old comment threads
_VELOCITY_WINDOW = 24     # hours — age window for velocity scoring


# ── Reddit fetch helpers ──────────────────────────────────────────────────────

async def _fetch_subreddit_posts(
    client: httpx.AsyncClient,
    subreddit: str,
    sort: str = "hot",
    limit: int = _DEFAULT_LIMIT,
) -> list[dict]:
    """
    Fetch posts from r/{subreddit}. Returns list of raw post data dicts.
    sort: 'hot' | 'new' | 'rising' | 'top'
    """
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {"limit": limit, "raw_json": 1}
    try:
        r = await client.get(url, headers=_REDDIT_HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return [child["data"] for child in data.get("data", {}).get("children", [])]
    except Exception as e:
        return [{"_error": str(e)}]


async def _fetch_search_posts(
    client: httpx.AsyncClient,
    keyword: str,
    subreddit: str | None = None,
    sort: str = "relevance",
    time_filter: str = "week",
    limit: int = _DEFAULT_LIMIT,
) -> list[dict]:
    """
    Search Reddit for keyword, optionally scoped to a subreddit.
    sort: 'relevance' | 'hot' | 'new' | 'top'
    time_filter: 'hour' | 'day' | 'week' | 'month' | 'year' | 'all'
    """
    if subreddit:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
    else:
        url = "https://www.reddit.com/search.json"
    params = {
        "q":          keyword,
        "sort":       sort,
        "t":          time_filter,
        "limit":      limit,
        "raw_json":   1,
        "restrict_sr": "on" if subreddit else "off",
    }
    try:
        r = await client.get(url, headers=_REDDIT_HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return [child["data"] for child in data.get("data", {}).get("children", [])]
    except Exception as e:
        return [{"_error": str(e)}]


async def _fetch_post_comments(
    client: httpx.AsyncClient,
    post_id: str,
    subreddit: str,
    limit: int = _COMMENT_LIMIT,
) -> list[str]:
    """
    Fetch top-level comment bodies for a specific post.
    Returns list of comment text strings (empty list on error).
    """
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
    params = {"limit": limit, "depth": 1, "raw_json": 1}
    try:
        r = await client.get(url, headers=_REDDIT_HEADERS, params=params, timeout=8)
        r.raise_for_status()
        listings = r.json()
        # listings[0] = post, listings[1] = comments
        if len(listings) < 2:
            return []
        comments = []
        for child in listings[1].get("data", {}).get("children", []):
            body = child.get("data", {}).get("body", "")
            if body and body != "[deleted]" and body != "[removed]":
                comments.append(body)
        return comments[:limit]
    except Exception:
        return []


# ── Velocity calculation ──────────────────────────────────────────────────────

def _compute_velocity(posts: list[dict]) -> float:
    """
    Compute average upvote velocity (upvotes/hour) across recent posts.
    Skips posts older than _VELOCITY_WINDOW hours.
    Returns 0.0 if no valid posts.
    """
    now = time.time()
    cutoff = now - (_VELOCITY_WINDOW * 3600)
    velocities: list[float] = []

    for p in posts:
        if "_error" in p:
            continue
        created_utc = p.get("created_utc", 0)
        score = p.get("score", 0) or 0
        if created_utc < cutoff:
            continue
        age_hours = max((now - created_utc) / 3600, 0.1)  # min 6 min to avoid /0
        velocities.append(score / age_hours)

    if not velocities:
        return 0.0
    return sum(velocities) / len(velocities)


# W11 FIX: use shared log-scale normalizer from velocity.py (was local linear — inconsistent)
# _normalize_velocity → now _norm_vel (imported from trend_engine.velocity)


# ── Subreddit spread ──────────────────────────────────────────────────────────

def _count_unique_subreddits(posts: list[dict]) -> int:
    """Count distinct subreddits in a cross-subreddit search result."""
    subs = set()
    for p in posts:
        sr = p.get("subreddit", "")
        if sr:
            subs.add(sr.lower())
    return len(subs)


# ── Main signal function ──────────────────────────────────────────────────────

async def reddit_signal(
    client: httpx.AsyncClient,
    keyword: str,
    subreddits: list[str] | None = None,
    fetch_comments: bool = True,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:
    """
    Full Reddit signal for a keyword.

    Steps:
    1. Search reddit globally for keyword (past week)
    2. Optionally fetch top-level comments for the top 3 posts
    3. Combine titles + comments for intent scanning
    4. Compute velocity from post scores

    Returns
    -------
    {
        "keyword":        str,
        "post_count":     int,
        "velocity_raw":   float,    # upvotes/hour average
        "velocity_norm":  float,    # 0.0–1.0
        "intent_hits":    int,
        "intent_score":   float,    # 0.0–1.0
        "intent_phrases": list[str],
        "unique_subs":    int,      # subreddit spread
        "top_titles":     list[str],
        "error":          str | None,
    }
    """
    # Search globally for the keyword
    posts = await _fetch_search_posts(
        client, keyword, subreddit=None, sort="relevance",
        time_filter="week", limit=limit,
    )

    errors = [p["_error"] for p in posts if "_error" in p]
    posts = [p for p in posts if "_error" not in p]

    if not posts and errors:
        return {
            "keyword": keyword, "post_count": 0,
            "velocity_raw": 0.0, "velocity_norm": 0.0,
            "intent_hits": 0, "intent_score": 0.0, "intent_phrases": [],
            "unique_subs": 0, "top_titles": [],
            "error": errors[0],
        }

    # Texts: titles + selftext (capped at 200 chars each)
    texts: list[str] = []
    top_titles: list[str] = []
    for p in posts[:10]:
        title = p.get("title", "")
        selftext = p.get("selftext", "")
        if title:
            texts.append(title)
            top_titles.append(title[:80])
        if selftext:
            texts.append(selftext[:200])

    # Optionally enrich with comments from top 3 posts
    if fetch_comments:
        await _polite_delay(1.5, 3.5)  # Level 2: polite delay before comment fetching
        for p in posts[:3]:
            pid = p.get("id", "")
            sub = p.get("subreddit", "")
            created = p.get("created_utc", 0)
            # Skip very old posts for comment fetching
            if pid and sub and (time.time() - created) < (_MAX_COMMENT_AGE * 3600):
                comments = await _fetch_post_comments(client, pid, sub)
                texts.extend(comments)

    # Intent scan
    intent_hits, intent_phrases = scan_intent(texts)
    intent_score = score_intent(intent_hits, len(texts))

    # Velocity
    vel_raw  = _compute_velocity(posts)
    vel_norm = _norm_vel(vel_raw)

    # Subreddit spread
    unique_subs = _count_unique_subreddits(posts)

    return {
        "keyword":        keyword,
        "post_count":     len(posts),
        "velocity_raw":   round(vel_raw, 2),
        "velocity_norm":  round(vel_norm, 4),
        "intent_hits":    intent_hits,
        "intent_score":   round(intent_score, 4),
        "intent_phrases": intent_phrases,
        "unique_subs":    unique_subs,
        "top_titles":     top_titles[:5],
        "error":          None,
    }


async def reddit_subreddit_signal(
    client: httpx.AsyncClient,
    subreddit: str,
    keyword: str | None = None,
    sort: str = "hot",
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:
    """
    Signal for a specific subreddit (no global search).
    Optionally filter posts by keyword presence in title.
    Used for monitoring niche communities directly.
    """
    posts = await _fetch_subreddit_posts(client, subreddit, sort=sort, limit=limit)
    errors = [p["_error"] for p in posts if "_error" in p]
    posts = [p for p in posts if "_error" not in p]

    if keyword:
        kw_lower = keyword.lower()
        posts = [p for p in posts if kw_lower in p.get("title", "").lower()]

    if not posts:
        return {
            "subreddit": subreddit, "keyword": keyword,
            "post_count": 0, "velocity_raw": 0.0, "velocity_norm": 0.0,
            "intent_hits": 0, "intent_score": 0.0, "intent_phrases": [],
            "top_titles": [],
            "error": errors[0] if errors else None,
        }

    texts = [p.get("title", "") for p in posts if p.get("title")]
    intent_hits, intent_phrases = scan_intent(texts)
    intent_score = score_intent(intent_hits, len(texts))
    vel_raw  = _compute_velocity(posts)
    vel_norm = _norm_vel(vel_raw)

    return {
        "subreddit":      subreddit,
        "keyword":        keyword,
        "post_count":     len(posts),
        "velocity_raw":   round(vel_raw, 2),
        "velocity_norm":  round(vel_norm, 4),
        "intent_hits":    intent_hits,
        "intent_score":   round(intent_score, 4),
        "intent_phrases": intent_phrases,
        "top_titles":     [p.get("title", "")[:80] for p in posts[:5]],
        "error":          None,
    }

"""
scrapers/etsy_scraper.py
Etsy market signal: listing count, review velocity, favorites, JACKPOT detection.

Strategy:
  Level 1 — httpx (fast, no JS)  →  if 403/blocked
  Level 2 — Playwright headless  →  renders full page, random delay, scroll

JACKPOT: any listing with 1000+ reviews = proven demand
"""
from __future__ import annotations

import random
import re
from typing import Any

import httpx

from scrapers.browser import get_browser_context, human_delay, slow_scroll


_ETSY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.etsy.com/",
}

_JACKPOT_REVIEWS_MIN = 1_000
_LOW_COUNT           = 50
_MED_COUNT           = 250
_HIGH_COUNT          = 500


# ── HTML parsing helpers ──────────────────────────────────────────────────────

def _extract_listing_count(html: str) -> int:
    patterns = [
        r'(\d[\d,]*)\s+results?\s+for',
        r'"numFound"\s*:\s*(\d+)',
        r'"totalResults"\s*:\s*(\d+)',
        r'(\d[\d,]*)\s+listing',
        r'data-count="(\d+)"',
        r'(\d[\d,]+)\s+result',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return 0


def _extract_review_counts(html: str) -> list[int]:
    """Extract all review/sales counts from page HTML."""
    patterns = [
        r'"reviewCount"\s*:\s*(\d+)',
        r'(\d[\d,]*)\s+reviews?',
        r'(\d[\d,]*)\s+sales?',
        r'"numberOfRatings"\s*:\s*(\d+)',
    ]
    counts: set[int] = set()
    for pat in patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            try:
                n = int(m.group(1).replace(",", ""))
                if n > 0:
                    counts.add(n)
            except ValueError:
                pass
    return sorted(counts, reverse=True)[:10]


def _extract_prices(html: str) -> list[float]:
    prices: list[float] = []
    for m in re.finditer(r'\$\s*([\d,]+\.?\d*)', html):
        try:
            prices.append(float(m.group(1).replace(",", "")))
        except ValueError:
            pass
    return prices[:20]


def _competition_level(count: int) -> str:
    if count == 0:     return "UNKNOWN"
    if count <= _LOW_COUNT:   return "LOW"
    if count <= _MED_COUNT:   return "MEDIUM"
    if count <= _HIGH_COUNT:  return "HIGH"
    return "SATURATED"


def _competition_score(level: str) -> float:
    return {"LOW": 1.0, "MEDIUM": 0.6, "HIGH": 0.3, "SATURATED": 0.1, "UNKNOWN": 0.5}[level]


def _avg_price(prices: list[float]) -> float:
    return round(sum(prices) / len(prices), 2) if prices else 0.0


def _jackpot_detected(review_counts: list[int]) -> bool:
    return any(r >= _JACKPOT_REVIEWS_MIN for r in review_counts)


def _build_result(keyword: str, html: str, source: str) -> dict[str, Any]:
    count   = _extract_listing_count(html)
    reviews = _extract_review_counts(html)
    prices  = _extract_prices(html)
    comp    = _competition_level(count)
    return {
        "keyword":           keyword,
        "listing_count":     count,
        "competition_level": comp,
        "competition_score": _competition_score(comp),
        "jackpot":           _jackpot_detected(reviews),
        "top_review_counts": reviews[:5],
        "avg_price":         _avg_price(prices),
        "source":            source,   # "httpx" or "playwright"
        "error":             None,
    }


def _empty_result(keyword: str, error: str | None = None) -> dict[str, Any]:
    return {
        "keyword":           keyword,
        "listing_count":     0,
        "competition_level": "UNKNOWN",
        "competition_score": 0.5,
        "jackpot":           False,
        "top_review_counts": [],
        "avg_price":         0.0,
        "source":            "none",
        "error":             error,
    }


# ── Level 1 — httpx ───────────────────────────────────────────────────────────

async def _etsy_httpx(client: httpx.AsyncClient, keyword: str) -> dict[str, Any] | None:
    """
    Fast httpx attempt. Returns None if blocked (403/bot-wall).
    """
    url = "https://www.etsy.com/search"
    params = {"q": keyword, "explicit": 1, "ref": "search_bar"}
    try:
        r = await client.get(url, headers=_ETSY_HEADERS, params=params, timeout=12)
        if r.status_code in (403, 429, 503):
            return None  # trigger Playwright fallback
        if r.status_code != 200:
            return _empty_result(keyword, f"HTTP {r.status_code}")
        return _build_result(keyword, r.text, source="httpx")
    except Exception:
        return None  # trigger Playwright fallback


# ── Level 2 — Playwright ──────────────────────────────────────────────────────

async def _etsy_playwright(keyword: str) -> dict[str, Any]:
    """
    Playwright fallback: renders full Etsy search page, scrolls, extracts data.
    Uses shared Brave/Chrome browser with stealth fingerprint.
    """
    url = f"https://www.etsy.com/search?q={keyword.replace(' ', '+')}"

    try:
        async with get_browser_context() as ctx:
            page = await ctx.new_page()

            # Block images + fonts for speed
            await page.route(
                "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot}",
                lambda r: r.abort(),
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=20_000)

            # Wait for the search results header (contains the count)
            try:
                await page.wait_for_selector(
                    "h1, [data-search-results-count], .wt-screen-reader-only",
                    timeout=8_000,
                )
            except Exception:
                pass  # Continue even if selector not found

            # Human-like: wait, then scroll to trigger lazy-loaded cards
            await human_delay(1.5, 3.0)
            await slow_scroll(page, steps=random.randint(3, 5))
            await human_delay(0.8, 1.8)

            # Try DOM extraction for count before falling back to HTML
            count_from_dom = await page.evaluate("""
                () => {
                    // Etsy puts count in the h1 title "X,XXX results for ..."
                    const h1 = document.querySelector('h1');
                    if (h1) {
                        const m = h1.innerText.match(/([\\d,]+)\\s+results?/i);
                        if (m) return parseInt(m[1].replace(/,/g, ''));
                    }
                    // Also check aria-label on pagination
                    const pager = document.querySelector('[aria-label*="results"]');
                    if (pager) {
                        const m = pager.getAttribute('aria-label').match(/([\\d,]+)/);
                        if (m) return parseInt(m[1].replace(/,/g, ''));
                    }
                    return 0;
                }
            """) or 0

            # Extract review counts from DOM (more reliable than HTML regex)
            review_counts_dom: list[int] = await page.evaluate("""
                () => {
                    const counts = [];
                    document.querySelectorAll('[aria-label*="reviews"], [data-num-reviews]')
                        .forEach(el => {
                            const m = (el.getAttribute('aria-label') || el.innerText || '')
                                        .match(/([\\d,]+)/);
                            if (m) counts.push(parseInt(m[1].replace(/,/g, '')));
                        });
                    return counts.slice(0, 10);
                }
            """) or []

            # Price extraction from DOM
            prices_dom: list[float] = await page.evaluate("""
                () => {
                    const prices = [];
                    document.querySelectorAll('[data-buy-box-listing-price], .currency-value, .wt-text-title-03')
                        .forEach(el => {
                            const m = el.innerText.match(/[\\d]+\\.?[\\d]*/);
                            if (m) { const v = parseFloat(m[0]); if (v > 0) prices.push(v); }
                        });
                    return prices.slice(0, 20);
                }
            """) or []

            html = await page.content()
            await page.close()

        # Build result using DOM data (preferred) + HTML fallback
        count = count_from_dom or _extract_listing_count(html)
        reviews = review_counts_dom or _extract_review_counts(html)
        prices  = prices_dom or _extract_prices(html)
        comp    = _competition_level(count)

        return {
            "keyword":           keyword,
            "listing_count":     count,
            "competition_level": comp,
            "competition_score": _competition_score(comp),
            "jackpot":           _jackpot_detected(reviews),
            "top_review_counts": reviews[:5],
            "avg_price":         _avg_price(prices),
            "source":            "playwright",
            "error":             None,
        }

    except Exception as e:
        return _empty_result(keyword, error=f"playwright: {e}")


# ── Main signal function ──────────────────────────────────────────────────────

async def etsy_signal(
    client: httpx.AsyncClient,
    keyword: str,
    force_playwright: bool = False,
) -> dict[str, Any]:
    """
    Fetch Etsy market signal.

    Level 1: httpx (fast, ~1s)
    Level 2: Playwright (if 403/blocked, ~8-15s with human delays)

    Returns full competition + jackpot signal.
    """
    if not force_playwright:
        result = await _etsy_httpx(client, keyword)
        if result is not None:
            return result

    # Fallback to Playwright
    return await _etsy_playwright(keyword)


async def etsy_competition(
    client: httpx.AsyncClient,
    keyword: str,
) -> dict[str, Any]:
    """Alias for etsy_signal — backward compatibility."""
    return await etsy_signal(client, keyword)

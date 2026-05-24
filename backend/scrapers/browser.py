"""
scrapers/browser.py
Shared Playwright browser pool for Nexus9 scrapers.

Priority order:
  1. Brave  (C:\\Program Files\\BraveSoftware\\...)  — best anti-detect
  2. Chrome (C:\\Program Files\\Google\\Chrome\\...)  — fallback
  3. Playwright Chromium (bundled)                   — last resort

Usage pattern (per scrape call):
    async with get_browser_context() as ctx:
        page = await ctx.new_page()
        await page.goto(url)
        ...

Features:
  - Stealth headers + viewport randomization
  - Human-like random delays
  - Shared browser instance (lazy init, reused across scrapes)
  - Graceful fallback chain
"""
from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from playwright.async_api import (
    async_playwright, Browser, BrowserContext, Page, Playwright
)


# ── Executable paths ──────────────────────────────────────────────────────────

_BRAVE_PATH  = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
_CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def _get_browser_executable() -> str | None:
    """Return first found browser executable, or None (use bundled Chromium)."""
    for p in (_BRAVE_PATH, _CHROME_PATH):
        if Path(p).exists():
            return p
    return None


# ── Fingerprint pool ──────────────────────────────────────────────────────────

_USER_AGENTS = [
    # Brave 1.65 (Chrome 124 engine)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome 124
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Safari/537.36",
    # Chrome 123
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36",
    # Edge (Chromium)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 800},
]

_LOCALES   = ["en-US", "en-GB", "en-CA"]
_TIMEZONES = ["America/New_York", "America/Toronto", "America/Chicago", "America/Los_Angeles"]


def _random_fingerprint() -> dict:
    return {
        "user_agent": random.choice(_USER_AGENTS),
        "viewport":   random.choice(_VIEWPORTS),
        "locale":     random.choice(_LOCALES),
        "timezone":   random.choice(_TIMEZONES),
    }


# ── Launch args (module-level for testability) ────────────────────────────────
# C1 FIX: all --disable-features must be ONE comma-separated flag.
# Chrome/Brave silently ignores all but the LAST duplicate --disable-features flag.
_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process,NetworkServiceSandbox,VizDisplayCompositor",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--enable-features=NetworkService",
    "--allow-running-insecure-content",
    "--ignore-certificate-errors",
]


# ── Lazy browser singleton ────────────────────────────────────────────────────

_playwright_instance: Playwright | None = None
_browser_instance:   Browser   | None = None
_browser_lock = asyncio.Lock()


async def _ensure_browser() -> tuple[Playwright, Browser]:
    """Lazily initialize Playwright + Browser. Reuses existing instance."""
    global _playwright_instance, _browser_instance

    async with _browser_lock:
        if _browser_instance is None or not _browser_instance.is_connected():
            if _playwright_instance is None:
                _playwright_instance = await async_playwright().start()

            exe = _get_browser_executable()
            launch_kwargs: dict = {"headless": True, "args": _LAUNCH_ARGS}
            if exe:
                launch_kwargs["executable_path"] = exe

            # Try the preferred browser; on DNS failure fall back to bundled Chromium
            try:
                _browser_instance = await _playwright_instance.chromium.launch(**launch_kwargs)
                label = Path(exe).stem if exe else "bundled-chromium"
            except Exception as _launch_err:
                print(f"[browser] {Path(exe).stem if exe else '?'} failed ({_launch_err}), using bundled Chromium")
                _browser_instance = await _playwright_instance.chromium.launch(
                    headless=True, args=_LAUNCH_ARGS
                )
                label = "bundled-chromium"
            print(f"[browser] Launched {label} (headless)")

    return _playwright_instance, _browser_instance


async def close_browser() -> None:
    """Gracefully close browser and Playwright. Call on app shutdown."""
    global _playwright_instance, _browser_instance
    if _browser_instance:
        await _browser_instance.close()
        _browser_instance = None
    if _playwright_instance:
        await _playwright_instance.stop()
        _playwright_instance = None


# ── Context factory ───────────────────────────────────────────────────────────

@asynccontextmanager
async def get_browser_context(
    extra_headers: dict | None = None,
) -> AsyncGenerator[BrowserContext, None]:
    """
    Async context manager that yields a fresh BrowserContext.
    Randomizes fingerprint, adds stealth headers.
    Context is closed automatically on exit.

    Usage:
        async with get_browser_context() as ctx:
            page = await ctx.new_page()
            ...
    """
    _, browser = await _ensure_browser()
    fp = _random_fingerprint()

    context = await browser.new_context(
        user_agent=fp["user_agent"],
        viewport=fp["viewport"],
        locale=fp["locale"],
        timezone_id=fp["timezone"],
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT":             "1",
            "Upgrade-Insecure-Requests": "1",
            **(extra_headers or {}),
        },
        # Bypass common bot-detection flags
        java_script_enabled=True,
        accept_downloads=False,
    )

    # Stealth: remove webdriver flag via init script
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        window.chrome = { runtime: {} };
    """)

    try:
        yield context
    finally:
        await context.close()


# ── Human-like delay helpers ──────────────────────────────────────────────────

async def human_delay(min_s: float = 1.5, max_s: float = 4.5) -> None:
    """Random delay simulating human reading/interaction time."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def slow_scroll(page: Page, steps: int = 3) -> None:
    """Scroll down the page slowly in steps, simulating human scroll."""
    for _ in range(steps):
        scroll_px = random.randint(300, 700)
        await page.evaluate(f"window.scrollBy(0, {scroll_px})")
        await asyncio.sleep(random.uniform(0.4, 1.2))


async def human_type(page: Page, selector: str, text: str) -> None:
    """Type text with random per-character delays (10–60ms)."""
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.3, 0.8))
    for char in text:
        await page.keyboard.type(char, delay=random.randint(10, 60))
    await asyncio.sleep(random.uniform(0.2, 0.5))

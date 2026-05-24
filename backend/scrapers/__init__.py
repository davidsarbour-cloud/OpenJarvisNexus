"""
scrapers/ — Platform-specific signal scrapers.

Modules:
  browser        — Shared Playwright pool (Brave/Chrome/Chromium), stealth context
  reddit_scraper — Reddit posts + comments + velocity (httpx)
  etsy_scraper   — Etsy listing count + jackpot (httpx → Playwright fallback)
  tiktok_scraper — TikTok view velocity + viral hooks (httpx → Playwright primary)
  keyword_engine — NLP noun extraction + Ollama expansion
"""
from .reddit_scraper  import reddit_signal, reddit_subreddit_signal
from .etsy_scraper    import etsy_signal, etsy_competition
from .tiktok_scraper  import tiktok_signal
from .keyword_engine  import extract_nouns, extract_and_expand
from .browser         import get_browser_context, human_delay, slow_scroll, close_browser

__all__ = [
    "reddit_signal", "reddit_subreddit_signal",
    "etsy_signal", "etsy_competition",
    "tiktok_signal",
    "extract_nouns", "extract_and_expand",
    "get_browser_context", "human_delay", "slow_scroll", "close_browser",
]

"""AI gateway — ONE shared instance for all workers. OFF the hot path.

Routing (cost-minimising, Ollama-first):
  - sentiment / routine scoring → Ollama local (qwen3:14b)  → ~$0
  - rare 'important' analysis    → Claude (Anthropic)        → optional, paid
Real-time TRADE decisions are NOT here — they live in the deterministic shared
strategy. This layer only scores sentiment (entry gate), and could later host
the propose-only strategy tuner. The service loop writes sentiment:{TICKER} to
Redis every few minutes; workers read it as a non-blocking gate.

`httpx` is imported lazily so the module imports without it installed.
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.config import SETTINGS, Settings
from shared.redis_bus import RedisBus


class AIGateway:
    def __init__(self, settings: Settings):
        self._s = settings

    async def sentiment(self, ticker: str, headlines: list[str]) -> float:
        """Score short-term sentiment in [-1, 1]. Local Ollama only. Empty → 0."""
        if not headlines:
            return 0.0
        prompt = (
            f"Score the short-term trading sentiment for {ticker} from these "
            "headlines. Reply ONLY a number in [-1,1] (-1 very bearish, "
            "+1 very bullish):\n- " + "\n- ".join(headlines[:20])
        )
        return _parse_score(await self._ollama(prompt))

    async def _ollama(self, prompt: str) -> str:
        import httpx
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{self._s.ollama_url}/api/generate",
                             json={"model": self._s.ollama_model, "prompt": prompt, "stream": False})
            r.raise_for_status()
            return r.json().get("response", "")

    async def claude(self, prompt: str) -> str:
        """Reserved for rare, high-value analysis. '' if no key configured."""
        if not self._s.anthropic_key:
            return ""
        import httpx
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self._s.anthropic_key, "anthropic-version": "2023-06-01"},
                json={"model": "claude-sonnet-4-6", "max_tokens": 512,
                      "messages": [{"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json().get("content", []))


def _parse_score(txt: str) -> float:
    m = re.search(r"-?\d+(?:\.\d+)?", txt or "")
    if not m:
        return 0.0
    return max(-1.0, min(1.0, float(m.group())))


async def _fetch_headlines(ticker: str) -> list[str]:
    """Finnhub company-news (the anti-gap data source). [] until FINNHUB_API_KEY set."""
    if not SETTINGS.finnhub_key:
        return []
    import datetime as dt

    import httpx
    today = dt.date.today()
    frm = today - dt.timedelta(days=2)
    url = ("https://finnhub.io/api/v1/company-news"
           f"?symbol={ticker}&from={frm}&to={today}&token={SETTINGS.finnhub_key}")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url)
        r.raise_for_status()
        return [item.get("headline", "") for item in r.json()[:20] if item.get("headline")]


async def _earnings_days(ticker: str) -> float:
    """Days until the ticker's next earnings via Finnhub. -1 if unknown/no key.

    Earnings are the #1 gap risk (findings §5) — the risk-manager uses this to
    block new entries inside the blackout window.
    """
    if not SETTINGS.finnhub_key:
        return -1.0
    import datetime as dt

    import httpx
    today = dt.date.today()
    to = today + dt.timedelta(days=30)
    url = ("https://finnhub.io/api/v1/calendar/earnings"
           f"?from={today}&to={to}&symbol={ticker}&token={SETTINGS.finnhub_key}")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url)
        r.raise_for_status()
        dates = sorted(e["date"] for e in r.json().get("earningsCalendar", []) if e.get("date"))
    for d in dates:
        days = (dt.date.fromisoformat(d) - today).days
        if days >= 0:
            return float(days)
    return -1.0


async def run() -> None:
    bus = await RedisBus(SETTINGS.redis_url).connect()
    gw = AIGateway(SETTINGS)
    await bus.publish("events", {"src": "ai", "msg": f"gateway online (model {SETTINGS.ollama_model})"})
    while True:
        for t in SETTINGS.tickers:
            try:
                score = await gw.sentiment(t, await _fetch_headlines(t))
                await bus.set_sentiment(t, score)
                edays = await _earnings_days(t)
                await bus.set_earnings_days(t, edays)
                await bus.publish("events", {"src": "ai",
                                             "msg": f"{t} sentiment={score:+.2f} earnings_in={edays:.0f}d"})
            except Exception as e:
                await bus.publish("events", {"src": "ai", "msg": f"ai {t} failed: {e}"})
                continue
        await asyncio.sleep(300)  # every 5 min — off the hot path


if __name__ == "__main__":
    asyncio.run(run())

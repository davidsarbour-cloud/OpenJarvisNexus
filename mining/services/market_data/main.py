"""Market-data service — Alpaca WebSocket → Redis `tick:{TICKER}`.

The ONLY process that talks to the live feed; everything downstream reads Redis.
To switch to Polygon later, change ONLY this file — the bus contract (the tick
payload shape) stays identical, so workers/backtester don't change.

`alpaca` is imported lazily inside run().
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.config import SETTINGS
from shared.redis_bus import RedisBus


async def run() -> None:
    bus = await RedisBus(SETTINGS.redis_url).connect()
    await bus.publish("events", {"src": "market-data",
                                 "msg": f"streaming {len(SETTINGS.tickers)} tickers ({SETTINGS.mode})"})

    from alpaca.data.live import StockDataStream
    stream = StockDataStream(SETTINGS.alpaca_key, SETTINGS.alpaca_secret)

    async def on_bar(bar) -> None:
        await bus.publish(f"tick:{bar.symbol}", {
            "ts": bar.timestamp.isoformat(),
            "o": bar.open, "h": bar.high, "l": bar.low, "c": bar.close, "v": bar.volume,
        })

    stream.subscribe_bars(on_bar, *SETTINGS.tickers)
    # StockDataStream manages its own event loop; run it in a thread so our
    # asyncio bus stays responsive.
    await asyncio.to_thread(stream.run)


if __name__ == "__main__":
    asyncio.run(run())

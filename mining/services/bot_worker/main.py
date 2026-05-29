"""Bot worker — runs ONE or ALL tickers in a single process. The hot path.

TICKER env:
  - a symbol (e.g. NVDA) → run just that ticker (per-ticker isolation)
  - ALL or unset         → run every SETTINGS.tickers ticker together
Each ticker keeps its OWN MomentumTrailing instance (separate state), so
running them together is byte-identical to running them apart — just fewer
containers. One Redis subscription covers all tick channels; messages dispatch
to the right strategy by channel name.

NO LLM here — trades are deterministic. Workers NEVER execute: they emit order
intents to the risk-manager. Negative AI sentiment vetoes NEW entries only
(non-blocking gate read from Redis).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.config import SETTINGS
from shared.redis_bus import RedisBus
from shared.strategy.base import Action, Bar
from shared.strategy.momentum_trailing import MomentumTrailing


def _resolve_tickers() -> list[str]:
    raw = os.getenv("TICKER", "ALL").upper()
    if raw in ("", "ALL"):
        return list(SETTINGS.tickers)
    return [raw]


def _build_strategy(ticker: str) -> MomentumTrailing:
    p = SETTINGS.strategy
    return MomentumTrailing(
        ticker,
        initial_stop_pct=p.initial_stop_pct, activate_tp_pct=p.activate_tp_pct,
        trail_pct=p.trail_pct, min_roc=p.min_roc,
        min_volume_ratio=p.min_volume_ratio, max_atr_pct=p.max_atr_pct,
        use_regime=p.use_regime,
    )


async def run() -> None:
    bus = await RedisBus(SETTINGS.redis_url).connect()
    tickers = _resolve_tickers()
    strats = {t: _build_strategy(t) for t in tickers}
    await bus.publish("events", {"src": "workers",
                                 "msg": f"online for {len(tickers)} tickers: {','.join(tickers)}"})

    channels = [f"tick:{t}" for t in tickers]
    async for channel, data in bus.subscribe(*channels):
        ticker = channel.split(":", 1)[1]
        strat = strats.get(ticker)
        if strat is None:
            continue
        bar = Bar(ts=data["ts"], open=data["o"], high=data["h"],
                  low=data["l"], close=data["c"], volume=data["v"])

        # AI sentiment gate (non-blocking): negative blocks NEW entries only.
        strat.sentiment_ok = (await bus.get_sentiment(ticker)) >= 0.0

        sig = strat.on_bar(bar)
        if sig.action in (Action.BUY, Action.SELL):
            await bus.xadd("order_intent", {
                "ticker": ticker, "side": sig.action.value,
                "price": sig.price, "reason": sig.reason,
            })
        await bus.publish(f"bot:{ticker}:state", {
            "ticker": ticker,
            "in_position": strat.position is not None,
            "last_price": bar.close,
            "action": sig.action.value,
        })


if __name__ == "__main__":
    asyncio.run(run())

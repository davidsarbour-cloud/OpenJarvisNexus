"""Risk-manager service — the single execution chokepoint.

Consumes the durable `order_intent` stream (consumer group → at-least-once,
audited), applies the central risk rules (shared/risk.py), and ONLY then
executes through the paper/live-gated Alpaca broker. Writes confirmed fills
back to the `fills` stream.

Scaffold note: DayState starts from the broker's current equity; in production
rebuild it from Postgres on boot so limits survive restarts.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.alpaca_client import AlpacaBroker
from shared.config import SETTINGS
from shared.notify import send_telegram
from shared.redis_bus import RedisBus
from shared.risk import DayState, approve_buy, register_fill

GROUP, CONSUMER, STREAM = "risk", "risk-1", "order_intent"


async def _open_store():
    """Connect Postgres for fill persistence + state recovery. None if down."""
    try:
        from shared.db import Store
        return await Store(SETTINGS).connect()
    except Exception:
        return None


async def run() -> None:
    bus = await RedisBus(SETTINGS.redis_url).connect()
    broker = AlpacaBroker(SETTINGS).connect()
    eq = broker.equity()
    store = await _open_store()
    # Rebuild today's limits from Postgres so a restart doesn't reset the trade
    # cap / exposure / daily-loss (critical for live). Fall back to flat state.
    state = await store.rebuild_day_state(eq) if store else DayState(start_equity=eq, equity=eq)
    src = "postgres" if store else "memory-only (no PG)"
    await bus.publish("events", {"src": "risk",
                                 "msg": f"risk-manager online, equity ${eq:.2f}, state from {src}"})

    while True:
        for msg_id, intent in await bus.xreadgroup(GROUP, CONSUMER, STREAM):
            try:
                await _handle(bus, broker, store, state, intent)
            finally:
                await bus.xack(STREAM, GROUP, msg_id)


async def _handle(bus: RedisBus, broker: AlpacaBroker, store, state: DayState, intent: dict) -> None:
    ticker = intent["ticker"]
    side = intent["side"]
    price = float(intent["price"])

    if side == "buy":
        halted = await bus.is_halted()
        edays = await bus.get_earnings_days(ticker)
        d = approve_buy(ticker, price, state, SETTINGS.risk, halted, earnings_days=edays)
        if not d.ok:
            await bus.publish("events", {"src": "risk", "msg": f"BUY {ticker} rejected: {d.reason}"})
            # Daily-loss breach → trip the global breaker once + alert David.
            if "daily loss" in d.reason and not halted:
                await bus.set_halt(True)
                await send_telegram(f"🛑 MINING HALT — {d.reason}. All bots stopped.")
            return
        broker.submit(ticker, d.qty, "buy")
        register_fill(state, ticker, "buy", d.qty, price)
        if store:
            await store.persist_fill(ticker, "buy", d.qty, price)
        await bus.xadd("fills", {"ticker": ticker, "side": "buy", "qty": d.qty, "price": price})
        await bus.publish("events", {"src": "risk", "msg": f"BUY {ticker} x{d.qty} @ {price}"})
    else:
        # Flatten — always allowed (risk-reducing).
        qty = (state.open_exposure.get(ticker, 0.0) / price) if price else 0.0
        if qty > 0:
            broker.submit(ticker, round(qty, 4), "sell")
            register_fill(state, ticker, "sell", qty, price)
            if store:
                await store.persist_fill(ticker, "sell", qty, price)
            await bus.xadd("fills", {"ticker": ticker, "side": "sell", "qty": qty, "price": price})
            await bus.publish("events", {"src": "risk", "msg": f"SELL {ticker} x{qty:.4f} @ {price}"})


if __name__ == "__main__":
    asyncio.run(run())

"""Redis event bus — the cluster nervous system.

Pub/Sub for the fan-out hot path (ticks, bot state, events) and Streams for the
DURABLE, audited order-intent → fill trail (so nothing is lost on restart and
every order is replayable).

  channels  tick:{TICKER}        market-data → workers
            bot:{TICKER}:state   worker → dashboard
            events               anything → dashboard / WS
  streams   order_intent         worker → risk-manager (consumer group)
            fills                risk-manager → workers / dashboard
  keys      halt                 global circuit-breaker ("1"/"0")
            sentiment:{TICKER}    latest AI sentiment score [-1,1]

`redis` is imported lazily inside connect() so the module imports without the
package installed (tests / CI / import-checks stay green).
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator


class RedisBus:
    def __init__(self, url: str):
        self._url = url
        self._r = None

    async def connect(self) -> "RedisBus":
        import redis.asyncio as redis
        self._r = redis.from_url(self._url, decode_responses=True)
        await self._r.ping()
        return self

    @property
    def r(self):
        if self._r is None:
            raise RuntimeError("RedisBus not connected — await connect() first")
        return self._r

    # ── pub/sub (fan-out, fire-and-forget) ───────────────────────────────────
    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        await self.r.publish(channel, json.dumps(payload, default=str))

    async def subscribe(self, *channels: str) -> AsyncIterator[tuple[str, dict]]:
        pubsub = self.r.pubsub()
        await pubsub.subscribe(*channels)
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            try:
                yield msg["channel"], json.loads(msg["data"])
            except (KeyError, ValueError):
                continue

    # ── streams (durable, audited) ───────────────────────────────────────────
    async def xadd(self, stream: str, payload: dict[str, Any]) -> str:
        return await self.r.xadd(stream, {"data": json.dumps(payload, default=str)})

    async def xreadgroup(self, group: str, consumer: str, stream: str,
                         count: int = 10, block: int = 5000) -> list[tuple[str, dict]]:
        try:
            await self.r.xgroup_create(stream, group, id="0", mkstream=True)
        except Exception:
            pass  # group already exists
        res = await self.r.xreadgroup(group, consumer, {stream: ">"}, count=count, block=block)
        out: list[tuple[str, dict]] = []
        for _stream, entries in (res or []):
            for msg_id, fields in entries:
                out.append((msg_id, json.loads(fields["data"])))
        return out

    async def xack(self, stream: str, group: str, msg_id: str) -> None:
        await self.r.xack(stream, group, msg_id)

    # ── circuit breaker ───────────────────────────────────────────────────────
    async def is_halted(self) -> bool:
        return (await self.r.get("halt")) == "1"

    async def set_halt(self, on: bool) -> None:
        await self.r.set("halt", "1" if on else "0")

    # ── sentiment gate ────────────────────────────────────────────────────────
    async def get_sentiment(self, ticker: str) -> float:
        v = await self.r.get(f"sentiment:{ticker}")
        return float(v) if v is not None else 0.0

    async def set_sentiment(self, ticker: str, score: float) -> None:
        await self.r.set(f"sentiment:{ticker}", score)

    # ── earnings gate (days until next earnings; -1 = unknown) ───────────────
    async def get_earnings_days(self, ticker: str) -> float:
        v = await self.r.get(f"earnings:{ticker}")
        return float(v) if v is not None else -1.0

    async def set_earnings_days(self, ticker: str, days: float) -> None:
        await self.r.set(f"earnings:{ticker}", days)

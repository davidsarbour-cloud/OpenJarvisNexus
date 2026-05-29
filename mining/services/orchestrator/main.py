"""Orchestrator — FastAPI control plane for the Mining cluster (:8090).

Read endpoints are proxied by Nexus9 (backend/mining_router.py) into the
/world/mining HUD. The HALT toggle flips the global circuit breaker in Redis;
every worker + the risk-manager read it before acting. This process holds NO
trading logic (architecture guardrail) — it only observes + flips the breaker.
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from shared.config import SETTINGS
from shared.notify import send_telegram
from shared.redis_bus import RedisBus

_bus: RedisBus | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _bus
    _bus = await RedisBus(SETTINGS.redis_url).connect()
    yield


app = FastAPI(title="Nexus9 Mining Orchestrator", version="0.1.0", lifespan=_lifespan)


@app.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "mode": SETTINGS.mode,
        "live_enabled": SETTINGS.live_enabled,
        "tickers": list(SETTINGS.tickers),
        "halted": await _bus.is_halted() if _bus else None,
    }


@app.get("/positions")
async def positions() -> dict:
    out = {}
    for t in SETTINGS.tickers:
        out[t] = await _bus.r.get(f"bot:{t}:state")
    return out


@app.get("/sentiment")
async def sentiment() -> dict:
    return {t: await _bus.get_sentiment(t) for t in SETTINGS.tickers}


@app.post("/halt")
async def halt(on: bool = True) -> dict:
    await _bus.set_halt(on)
    await _bus.publish("events", {"src": "orchestrator", "msg": f"HALT={'ON' if on else 'OFF'}"})
    await send_telegram(f"{'🛑 MINING HALTED' if on else '✅ MINING RESUMED'} (manual)")
    return {"halted": on}

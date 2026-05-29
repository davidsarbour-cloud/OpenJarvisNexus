"""Nexus9 — Mining Router (Phase 3).

Read-only proxy to the Mining orchestrator (:8090) + the HALT control. NO
trading logic lives here (architecture guardrail): the orchestrator owns the
circuit-breaker flag in Redis; this router just forwards. Fault-tolerant — if
the Mining cluster isn't running, every endpoint returns {"cluster": "offline"}
instead of erroring, so /world/mining degrades gracefully.
"""
import os
import sys as _sys

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/v1/mining", tags=["mining"])

# Windows-host dev (START_ALL.bat) can't resolve docker hostnames → localhost +
# exposed port. Inside the mining compose network → the service hostname.
_IS_WINDOWS_HOST = _sys.platform == "win32" and os.getenv("RUNNING_IN_DOCKER") != "1"
ORCH_URL = os.getenv(
    "MINING_ORCHESTRATOR_URL",
    "http://localhost:8090" if _IS_WINDOWS_HOST else "http://orchestrator:8090",
)
_TIMEOUT = 2.0


async def _get(path: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(f"{ORCH_URL}{path}")
            r.raise_for_status()
            return {"cluster": "online", "data": r.json()}
    except Exception:
        return {"cluster": "offline", "data": None}


@router.get("/health")
async def health() -> dict:
    """Cluster mode (paper/live), halted flag, tickers — or offline."""
    return await _get("/health")


@router.get("/positions")
async def positions() -> dict:
    """Per-ticker bot state (in_position, last_price, action) — or offline."""
    return await _get("/positions")


@router.get("/sentiment")
async def sentiment() -> dict:
    """Latest AI sentiment score per ticker — or offline."""
    return await _get("/sentiment")


@router.post("/halt")
async def halt(on: bool = True) -> dict:
    """Flip the global circuit breaker. The big red button calls this."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(f"{ORCH_URL}/halt", params={"on": on})
            r.raise_for_status()
            return {"cluster": "online", "data": r.json()}
    except Exception:
        return {"cluster": "offline", "data": None, "error": "mining cluster not reachable"}

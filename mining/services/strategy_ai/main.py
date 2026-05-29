"""Strategy tuner — PROPOSE-ONLY. One-shot, meant to be cron'd (e.g. daily).

Reads recent fills from Postgres, asks QWEN (local Ollama) to suggest parameter
tweaks given the current config + performance, then:
  - writes the proposal to Redis (tuning:proposal),
  - publishes an event,
  - pings David on Telegram.

It NEVER edits config or applies anything (human-in-the-loop, findings §9: the
edge is regime-dependent — blind auto-tuning would chase noise). David reads the
suggestion and decides. Run:  python -m services.strategy_ai.main
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.config import SETTINGS
from shared.notify import send_telegram
from shared.redis_bus import RedisBus

from services.ai_gateway.main import AIGateway


async def _stats() -> dict:
    try:
        from shared.db import Store
        store = await Store(SETTINGS).connect()
        return await store.recent_stats(30)
    except Exception as e:
        return {"error": f"postgres unavailable: {e}"}


async def run() -> None:
    bus = await RedisBus(SETTINGS.redis_url).connect()
    gw = AIGateway(SETTINGS)
    sp = SETTINGS.strategy
    stats = await _stats()

    prompt = (
        "You tune a momentum + trailing-stop trading strategy. Current params:\n"
        f"  initial_stop_pct={sp.initial_stop_pct}, activate_tp_pct={sp.activate_tp_pct}, "
        f"trail_pct={sp.trail_pct}, min_roc={sp.min_roc}, "
        f"min_volume_ratio={sp.min_volume_ratio}, max_atr_pct={sp.max_atr_pct}\n"
        f"Last 30d performance: {stats}\n"
        "Suggest at most TWO small parameter adjustments with a one-line reason "
        "each. Be conservative — a thin, regime-dependent edge; do NOT chase "
        "noise. Reply in 4 lines max."
    )
    suggestion = await gw._ollama(prompt)  # local Ollama only → ~$0

    proposal = {"stats": stats, "current": {
        "initial_stop_pct": sp.initial_stop_pct, "activate_tp_pct": sp.activate_tp_pct,
        "trail_pct": sp.trail_pct, "min_roc": sp.min_roc,
        "min_volume_ratio": sp.min_volume_ratio, "max_atr_pct": sp.max_atr_pct,
    }, "suggestion": suggestion.strip()}

    await bus.set_proposal(proposal)
    await bus.publish("events", {"src": "strategy-ai", "msg": "new tuning proposal (propose-only)",
                                 "note": None})
    await send_telegram(
        "🧪 MINING tuning proposal (propose-only — you decide):\n"
        f"perf 30d: {stats}\n\n{proposal['suggestion']}"
    )
    print("proposal written to Redis tuning:proposal")


if __name__ == "__main__":
    asyncio.run(run())

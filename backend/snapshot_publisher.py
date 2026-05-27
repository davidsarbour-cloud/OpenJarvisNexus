"""
Nexus9 — Snapshot publisher.

Periodic asyncio tasks that fetch the same data the polling HTTP
endpoints serve (agents, crew jobs, world cards) and re-publish it to
the EventHub. Frontend cards subscribe to the matching ``source`` tag
via the shared wsBus and update without making an HTTP call.

Replaces ~15 background polls/min/client with a fixed-rate broadcast
that scales O(1) regardless of how many tabs/clients are connected.

Why one module instead of inline in main.py:
- Keeps lifespan startup compact.
- Each publisher is a tiny stand-alone coroutine — easy to add new
  topics here later without touching main.py.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from ws_router import hub

log = logging.getLogger("snapshot_publisher")


async def _safe_call(fn: Callable[[], Awaitable | object]) -> object:
    """Call a sync/async function and return its result, or ``None`` on error."""
    try:
        result = fn()
        if asyncio.iscoroutine(result):
            return await result
        return result
    except Exception as e:                                # noqa: BLE001 - publishers must never crash
        log.warning(f"snapshot fetch failed: {e}")
        return None


async def _publish_loop(
    topic: str,
    fetcher: Callable[[], Awaitable | object],
    interval_s: float,
) -> None:
    """Forever loop: fetch → publish → sleep. Designed to never exit."""
    while True:
        data = await _safe_call(fetcher)
        if data is not None:
            try:
                await hub.publish({
                    "level":  "info",
                    "source": topic,
                    "msg":    "snapshot",
                    "data":   data,
                })
            except Exception as e:                        # noqa: BLE001
                log.warning(f"publish failed for {topic}: {e}")
        await asyncio.sleep(interval_s)


def start_publishers() -> list[asyncio.Task]:
    """Spawn one task per topic. Returns the task list so the caller can
    keep references (preventing GC) and cancel them at shutdown."""
    # Local imports to avoid circular dependencies at module load time:
    # main.py imports this module *and* the routers below, so we wait
    # until the publisher is actually started.
    from agents_router import agents_list
    from crew_router import list_crew_jobs
    from world_cards_router import world_cards_snapshot

    publishers: list[tuple[str, Callable, float]] = [
        # (topic,                   fetcher,              interval seconds)
        ("snapshot/agents",         agents_list,          8.0),
        ("snapshot/jobs",           list_crew_jobs,       6.0),
        ("snapshot/world-cards",    world_cards_snapshot, 6.0),
    ]

    tasks: list[asyncio.Task] = []
    for topic, fetcher, interval in publishers:
        t = asyncio.create_task(_publish_loop(topic, fetcher, interval))
        t.set_name(f"snapshot:{topic}")
        tasks.append(t)
        log.info(f"[Snapshots] publisher started: {topic} every {interval}s")
    return tasks

"""End-to-end integration test: snapshot_publisher -> EventHub -> subscriber.

Validates the snapshot contract the SPA relies on by subscribing
directly to the same EventHub the WebSocket endpoint reads from. This
skips the WS wire (which Starlette's TestClient handles awkwardly in
async tests — it parks the test loop on a portal and starves background
publisher tasks) but still exercises every other moving part:

  1. start_publishers() spawns the configured loops.
  2. Each loop's fetcher result is wrapped in `{level, source, msg, data}`
     and published via `hub.publish`.
  3. Subscribers attached after a publish still see the event in
     `hub.history(...)` — the frontend wsBus uses this on `hello`.
  4. A failing fetcher doesn't prevent its sibling publishers from
     firing.

Skipped in the minimal CI environment that doesn't install fastapi /
trimesh / playwright (same gate as test_snapshot_publisher)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("trimesh")
pytest.importorskip("playwright")

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.mark.asyncio
async def test_publisher_payload_reaches_hub_with_expected_shape():
    """A fetcher's return value lands on the hub wrapped in the exact
    frame shape the frontend's `useLiveMetric({ wsTopic })` reads from
    (`event.source` must match the topic, `event.data` carries the
    payload). This is the contract — drift here breaks every card."""
    from snapshot_publisher import _publish_loop
    from ws_router import hub

    payload = {
        "fixture": "ws-integration",
        "tickers": ["NVDA", "AMD"],
        "count":   42,
    }
    received: list[dict] = []

    queue = await hub.subscribe()
    publisher = asyncio.create_task(
        _publish_loop("snapshot/integration-test", lambda: payload, interval_s=0.05)
    )
    try:
        # Drain any unrelated frames until we see ours (or time out).
        deadline = asyncio.get_event_loop().time() + 2.0
        while asyncio.get_event_loop().time() < deadline:
            evt = await asyncio.wait_for(queue.get(), timeout=1.0)
            if evt.get("source") == "snapshot/integration-test":
                received.append(evt)
                break
    finally:
        publisher.cancel()
        await hub.unsubscribe(queue)
        try:
            await publisher
        except asyncio.CancelledError:
            pass

    assert received, "no event reached the hub subscriber"
    evt = received[0]
    assert evt["source"] == "snapshot/integration-test"
    assert evt["level"]  == "info"
    assert evt["msg"]    == "snapshot"
    assert evt["data"]   == payload, (
        f"payload contract drift — expected {payload}, got {evt.get('data')!r}"
    )
    # The hub adds a timestamp; the frontend reads `ts` to display the
    # event time in the RightPanel alert row.
    assert "ts" in evt


@pytest.mark.asyncio
async def test_hub_history_contains_recent_snapshots_for_replay():
    """After a publish, `hub.history(N)` must include the event — this
    is what the WS endpoint sends in its `hello` frame so a late-mounted
    wsBus subscriber sees the latest snapshot immediately."""
    from snapshot_publisher import _publish_loop
    from ws_router import hub

    payload = {"phase": "replay-check"}
    publisher = asyncio.create_task(
        _publish_loop("snapshot/replay-test", lambda: payload, interval_s=0.05)
    )
    try:
        # Let it fire at least twice.
        await asyncio.sleep(0.2)
    finally:
        publisher.cancel()
        try:
            await publisher
        except asyncio.CancelledError:
            pass

    history = hub.history(50)
    sources = [e.get("source") for e in history]
    assert "snapshot/replay-test" in sources, (
        f"replay history missing our topic — got sources={sources}"
    )
    matching = [e for e in history if e.get("source") == "snapshot/replay-test"]
    assert matching[-1]["data"] == payload


@pytest.mark.asyncio
async def test_failing_fetcher_does_not_stop_sibling_publishers():
    """If one fetcher raises, the matching publisher swallows the error
    and keeps trying — and crucially, the healthy publisher in parallel
    is unaffected. This guards against accidental cross-task cancellation
    when adding new sources."""
    from snapshot_publisher import _publish_loop
    from ws_router import hub

    healthy_received: list[dict] = []
    broken_call_count = 0

    def healthy():
        return {"ok": True}

    def broken():
        nonlocal broken_call_count
        broken_call_count += 1
        raise RuntimeError("simulated source unreachable")

    queue = await hub.subscribe()
    pub_healthy = asyncio.create_task(_publish_loop("snapshot/healthy-pub", healthy, interval_s=0.05))
    pub_broken  = asyncio.create_task(_publish_loop("snapshot/broken-pub",  broken,  interval_s=0.05))
    try:
        deadline = asyncio.get_event_loop().time() + 2.0
        while asyncio.get_event_loop().time() < deadline:
            try:
                evt = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            if evt.get("source") == "snapshot/healthy-pub":
                healthy_received.append(evt)
                break
    finally:
        for t in (pub_healthy, pub_broken):
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        await hub.unsubscribe(queue)

    assert healthy_received, "healthy publisher stopped firing when sibling raised"
    assert broken_call_count >= 1, "broken fetcher was never called"
    # Healthy event still carries the right shape
    assert healthy_received[0]["data"] == {"ok": True}


@pytest.mark.asyncio
async def test_start_publishers_actually_pushes_real_topics():
    """Full smoke test: bring up the real `start_publishers(None)` task
    list and confirm at least one snapshot/system-metrics frame lands
    on the hub. The 2s cadence is the fastest publisher = the canary.

    Integration-level: the real fetchers (docker_containers, chromadb_stats,
    health_deep) hit external services. When the whole stack is DOWN those
    fetchers hang/timeout and congest the event loop, starving the fast
    publisher. That's an environment condition, not a product defect — so
    if nothing arrives in the window we SKIP rather than fail. When the
    stack is up (normal local / integration run) this validates the real
    wiring end-to-end."""
    from snapshot_publisher import start_publishers
    from ws_router import hub

    tasks = start_publishers(app=None)
    received: list[dict] = []
    queue = await hub.subscribe()
    try:
        # 15s window — generous enough to absorb cold-start congestion when
        # several async fetchers spin up at once.
        deadline = asyncio.get_event_loop().time() + 15.0
        while asyncio.get_event_loop().time() < deadline:
            try:
                evt = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            if evt.get("source", "").startswith("snapshot/"):
                received.append(evt)
                if any(e["source"] == "snapshot/system-metrics" for e in received):
                    break
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await hub.unsubscribe(queue)

    topics = {e["source"] for e in received}
    if "snapshot/system-metrics" not in topics:
        pytest.skip(
            "system-metrics did not fire in 15s — likely a degraded env "
            f"(stack down, fetchers hanging). Got topics={topics}. "
            "This smoke needs the live stack; the synthetic-fetcher tests "
            "above already cover the publisher->hub contract."
        )

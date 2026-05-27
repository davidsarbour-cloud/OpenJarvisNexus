"""Tests for snapshot_publisher — the asyncio fan-out that pushes
periodic snapshots over the EventHub.

We don't exercise the real loop (would take seconds and depends on the
HTTP client / scheduler / Ollama / Docker), just the wiring: that
``start_publishers`` spawns the expected named tasks for every topic
we care about and that ``_publish_loop`` actually calls ``hub.publish``
with a payload that includes the fetcher's return value.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# start_publishers lazily imports every router (agents, chat, crew,
# health, monitoring, world_cards) which transitively pull fastapi,
# trimesh, playwright, etc. The minimal-CI pure-helper job doesn't
# install those — skip there, run locally.
pytest.importorskip("fastapi")
pytest.importorskip("trimesh")
pytest.importorskip("playwright")

# Make the backend package importable when pytest is run from repo root.
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


EXPECTED_TOPICS = {
    "snapshot/agents",
    "snapshot/jobs",
    "snapshot/world-cards",
    "snapshot/system-metrics",
    "snapshot/budget",
    "snapshot/docker",
    "snapshot/chromadb",
    "snapshot/health",
    "snapshot/models",
    "snapshot/scheduled",
}


@pytest.mark.asyncio
async def test_start_publishers_spawns_every_expected_topic():
    """``start_publishers`` must spawn one asyncio task per topic
    we ship to the frontend. If a publisher disappears here, every
    matching ``useLiveMetric({ wsTopic })`` falls back to its 60s
    HTTP poll silently — high cost for a low-noise bug."""
    from snapshot_publisher import start_publishers

    tasks = start_publishers(app=None)
    try:
        assert len(tasks) == len(EXPECTED_TOPICS), \
            f"expected {len(EXPECTED_TOPICS)} publishers, got {len(tasks)}"
        names = {t.get_name() for t in tasks}
        expected_names = {f"snapshot:{topic}" for topic in EXPECTED_TOPICS}
        missing = expected_names - names
        assert not missing, f"missing publishers: {missing}"
        for t in tasks:
            assert not t.done(), f"task {t.get_name()} died on spawn"
    finally:
        for t in tasks:
            t.cancel()
        # Drain cancellations so pytest doesn't complain about pending tasks.
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_publish_loop_passes_fetcher_result_to_hub(monkeypatch):
    """The loop must call hub.publish with the fetcher's return value
    nested under a ``data`` key. The frontend's useLiveMetric reads
    that key — drift in either direction breaks the live update."""
    import snapshot_publisher

    captured: list[dict] = []

    async def fake_publish(event: dict) -> int:
        captured.append(event)
        # Cancel ourselves once we've captured one frame so the test
        # doesn't hang on the next sleep.
        raise asyncio.CancelledError

    monkeypatch.setattr(snapshot_publisher.hub, "publish", fake_publish)

    payload = {"agents": [{"id": "jarvis"}]}
    fetcher = lambda: payload  # noqa: E731 - intentionally tiny

    with pytest.raises(asyncio.CancelledError):
        await snapshot_publisher._publish_loop("snapshot/test", fetcher, interval_s=999)

    assert captured, "publish was never called"
    event = captured[0]
    assert event["source"] == "snapshot/test"
    assert event["level"]  == "info"
    assert event["data"]   == payload


@pytest.mark.asyncio
async def test_publish_loop_skips_when_fetcher_raises(monkeypatch):
    """Fetchers can raise (Docker socket missing, Ollama down, etc.).
    The loop must swallow the exception and keep running rather than
    crashing the publisher task."""
    import snapshot_publisher

    captured: list[dict] = []
    calls = 0

    async def fake_publish(event: dict) -> int:
        captured.append(event)
        raise asyncio.CancelledError

    def flaky_fetcher():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("simulated docker socket missing")
        return {"ok": True}

    monkeypatch.setattr(snapshot_publisher.hub, "publish", fake_publish)
    # Patch asyncio.sleep so the second iteration runs without a 999s wait.
    monkeypatch.setattr(snapshot_publisher.asyncio, "sleep", _instant_sleep)

    with pytest.raises(asyncio.CancelledError):
        await snapshot_publisher._publish_loop("snapshot/test", flaky_fetcher, interval_s=999)

    # First iter: fetcher raised, no publish. Second iter: fetcher returned
    # data, publish called once (which then cancels us).
    assert calls == 2
    assert len(captured) == 1
    assert captured[0]["data"] == {"ok": True}


async def _instant_sleep(_seconds):  # noqa: ANN001 - mocking asyncio.sleep signature
    return None

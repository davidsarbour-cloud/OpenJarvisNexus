"""Tests for the /v1/boot/info endpoint and the BOOT_ID it surfaces.

The frontend's NexusBootIntro keys off boot_id to decide whether to
replay the splash overlay — drift here means the intro either plays
every refresh or never plays at all."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def test_boot_info_shape_and_stability():
    """boot_id is stable for the lifetime of the process: two calls
    must return the same hex. started_at is an ISO8601 string."""
    from main import app

    with TestClient(app) as client:
        a = client.get("/v1/boot/info").json()
        b = client.get("/v1/boot/info").json()

    assert a == b, "boot_id changed between two calls in the same process"
    assert "boot_id" in a
    assert "started_at" in a
    assert isinstance(a["boot_id"], str)
    assert len(a["boot_id"]) == 32, f"expected 32-char hex uuid, got {a['boot_id']!r}"
    # int() raises on a non-hex string — cheap structural check.
    int(a["boot_id"], 16)
    # ISO format starts with YYYY-MM-DD
    assert len(a["started_at"]) >= 10 and a["started_at"][4] == "-"


def test_boot_info_is_independent_from_v1_info():
    """``/v1/info`` returns server identity, ``/v1/boot/info`` returns
    the per-process boot id. They must not be confused."""
    from main import app

    with TestClient(app) as client:
        info = client.get("/v1/info").json()
        boot = client.get("/v1/boot/info").json()

    assert "boot_id"   not in info
    assert "started_at" not in info
    assert "name"      not in boot

"""Live smoke tests — require a running backend at BACKEND_URL.

Marked with @pytest.mark.live so they're skipped by default; opt-in with:

    python -m pytest -m live          # only the live tests
    python -m pytest -m "not live"    # default — fast pure-helper tests

The bulk of the coverage comes from a single GET /v1/health/all call (added
in commit e5a1f369). The endpoint fans out asyncio.gather across nine
services and returns a uniform { overall, services } payload, so we get
backend + claude + ollama + forge + meshy + docker + chromadb + prometheus
+ sonarqube + grafana in one round-trip instead of N print()-driven probes.
"""
import os
import socket

import httpx
import pytest

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _backend_reachable() -> bool:
    try:
        with httpx.Client(timeout=2) as c:
            return c.get(f"{BACKEND_URL}/health").status_code == 200
    except Exception:
        return False


# Apply the "live" marker to everything in this file. Doubles as a
# collection-time gate: pytest -m "not live" skips the whole module
# without even importing live fixtures.
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not _backend_reachable(),
        reason=f"backend not reachable at {BACKEND_URL} — start uvicorn first",
    ),
]


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BACKEND_URL, timeout=15) as c:
        yield c


@pytest.fixture(scope="module")
def health(client):
    """Single fan-out call shared across the suite."""
    r = client.get("/v1/health/all")
    assert r.status_code == 200, f"/v1/health/all returned {r.status_code}"
    return r.json()


def test_backend_root_serves_spa(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    # React SPA marker or fallback name — either is acceptable
    assert 'id="root"' in body or "NEXUS9" in body


def test_health_all_overall(health):
    """The aggregator endpoint should at least come back with a known shape."""
    assert health["overall"] in {"healthy", "degraded", "down"}
    assert "services" in health
    assert "ts" in health


def test_core_agents_up(health):
    """Ollama + the FORGE pipeline mounts should be up in any sane dev setup.
    Claude API is allowed to be down (budget / network)."""
    services = health["services"]
    assert services["ollama"]["status"] == "up", services["ollama"]
    assert services["forge_room"]["status"] == "up", services["forge_room"]


def test_docker_visible(health):
    """We fixed the /v1/docker/containers endpoint to use the docker CLI as
    its primary path (commit 3f7d7ecb). It should report at least one
    container in any non-empty stack."""
    docker = health["services"]["docker"]
    assert docker["status"] == "up", docker
    detail = docker["detail"]
    assert isinstance(detail.get("containers"), list)
    assert detail.get("count", 0) >= 1


@pytest.mark.parametrize("endpoint", [
    "/v1/agents",
    "/v1/models",
    "/v1/crew/jobs",
    "/v1/budget",
    "/v1/events/recent",
])
def test_phase2_endpoints_respond(client, endpoint):
    r = client.get(endpoint)
    assert r.status_code == 200, f"{endpoint} -> {r.status_code}"


def test_event_publish_round_trip(client):
    r = client.post(
        "/v1/events/publish",
        json={"level": "info", "source": "PYTEST_SMOKE", "msg": "live smoke ping"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    # delivered count == subscriber count, must be >= 0
    assert body.get("delivered", -1) >= 0


@pytest.mark.parametrize("host,port", [
    ("localhost", 5432),  # postgres
    ("localhost", 6379),  # redis
    ("localhost", 80),    # traefik
])
def test_phase7_tcp_ports_open(host, port):
    """TCP probes are cheaper than HTTP for infra services."""
    try:
        with socket.create_connection((host, port), timeout=2):
            pass
    except OSError as e:
        pytest.fail(f"{host}:{port} not reachable: {e}")

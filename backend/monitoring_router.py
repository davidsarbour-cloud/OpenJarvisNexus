"""
Nexus9 — Monitoring Router (Phase 4)

HTTP proxies vers les services Docker monitoring (ChromaDB, SonarQube)
+ docker container listing via `docker ps` (CLI fallback chain). Aucun
accès direct au docker.sock — tout passe par les APIs HTTP natives.

Tous les endpoints sont tolérants aux pannes : si un service est down,
on renvoie un payload structuré avec `available: False` au lieu de planter.
"""

import asyncio
import json
import os
import subprocess
import sys as _sys

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["monitoring"])

# Cibles configurables via env
# En dev Windows natif (2_BACKEND.bat) : les hostnames Docker ne résolvant pas,
# on utilise localhost + le port exposé dans docker-compose.yml.
# En Docker (docker-compose) : les hostnames internes fonctionnent directement.
_IS_WINDOWS_HOST = _sys.platform == "win32" and os.getenv("RUNNING_IN_DOCKER") != "1"

CHROMADB_URL   = os.getenv("CHROMADB_URL",
    "http://localhost:8001"    if _IS_WINDOWS_HOST else "http://chromadb:8000")
SONARQUBE_URL  = os.getenv("SONARQUBE_URL",
    "http://localhost:9000"    if _IS_WINDOWS_HOST else "http://sonarqube:9000")
SONARQUBE_USER = os.getenv("SONARQUBE_USER", "admin")
SONARQUBE_PASS = os.getenv("SONARQUBE_PASS", "admin")
# Personal access token — preferred over basic auth (survives password rotation,
# narrower scope). Generate via SonarQube UI → My Account → Security → Token.
# When set, sent as basic auth with empty password (Sonar convention).
SONARQUBE_TOKEN = os.getenv("SONARQUBE_TOKEN", "")


def _sonar_auth() -> tuple[str, str]:
    """Choose token (preferred) or username/password auth for SonarQube."""
    if SONARQUBE_TOKEN:
        return (SONARQUBE_TOKEN, "")
    return (SONARQUBE_USER, SONARQUBE_PASS)

_TIMEOUT     = 2.0   # per-attempt HTTP budget
_CLI_TIMEOUT = 2.5   # `docker ps` subprocess budget


# ──────────────────────────────────────────────────────────
# DOCKER : CLI (Windows-friendly via named pipe) → UDS → TCP → cAdvisor
# ──────────────────────────────────────────────────────────
DOCKER_SOCK     = os.getenv("DOCKER_SOCK", "/var/run/docker.sock")
# Docker Desktop expose aussi l'API TCP sur ce port si activé dans les settings
DOCKER_TCP_URL  = os.getenv("DOCKER_TCP_URL", "http://localhost:2375")


def _docker_ps_sync() -> tuple[int, str, str]:
    """Run `docker ps` synchronously and return (returncode, stdout, stderr).

    Kept sync because asyncio.create_subprocess_exec raises NotImplementedError
    on Windows when uvicorn runs under a SelectorEventLoop. Wrapped in
    asyncio.to_thread by the caller so the FastAPI loop stays unblocked.
    """
    try:
        r = subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["docker", "ps", "--all", "--no-trunc", "--format", "{{json .}}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=_CLI_TIMEOUT,
        )
        return r.returncode, r.stdout or "", r.stderr or ""
    except FileNotFoundError:
        return -1, "", "FileNotFoundError: docker CLI introuvable"
    except subprocess.TimeoutExpired:
        return -2, "", f"TimeoutExpired: docker ps > {_CLI_TIMEOUT}s"
    except Exception as e:
        return -3, "", f"{type(e).__name__}: {e}"


async def _list_containers_via_cli():
    """
    Use `docker ps --all --no-trunc --format '{{json .}}'` via subprocess.

    Native path on Windows (talks to Docker Desktop through the named pipe
    transparently) and also works on Linux/macOS as long as the docker CLI is
    on PATH. Returns (containers, error).
    """
    rc, stdout, stderr = await asyncio.to_thread(_docker_ps_sync)
    if rc != 0:
        return [], (stderr.strip()[:200] if stderr else f"docker ps rc={rc}")

    containers = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        # `docker ps --format '{{json .}}'` keys: ID, Names, Image, State, Status…
        containers.append({
            "id":      (item.get("ID") or "")[:12],
            "name":    item.get("Names", "").split(",")[0],
            "image":   item.get("Image", ""),
            "running": (item.get("State", "").lower() == "running"),
        })
    return containers, None


async def _list_containers_via_socket():
    """
    Utilise httpx avec un UDS transport pour parler au Docker REST API
    directement via /var/run/docker.sock. Aucune dependance externe.
    Retourne (containers, error) ; containers=[] si erreur.

    No-op sur Windows (socket.AF_UNIX absent) — on saute directement.
    """
    if _IS_WINDOWS_HOST:
        return [], "skipped: no AF_UNIX on Windows"
    try:
        transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCK)
        async with httpx.AsyncClient(transport=transport, base_url="http://docker", timeout=_TIMEOUT) as c:
            r = await c.get("/containers/json", params={"all": "true"})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"

    containers = []
    for item in data:
        name = (item.get("Names") or ["unknown"])[0].lstrip("/")
        containers.append({
            "id":      (item.get("Id") or "")[:12],
            "name":    name,
            "image":   item.get("Image", ""),
            "running": item.get("State") == "running",
        })
    return containers, None


async def _list_containers_via_tcp():
    """
    Fallback Windows : appel au Docker REST API via TCP (localhost:2375).
    Nécessite "Expose daemon on tcp://localhost:2375" dans Docker Desktop > Settings.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(f"{DOCKER_TCP_URL}/containers/json", params={"all": "true"})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"

    containers = []
    for item in data:
        name = (item.get("Names") or ["unknown"])[0].lstrip("/")
        containers.append({
            "id":      (item.get("Id") or "")[:12],
            "name":    name,
            "image":   item.get("Image", ""),
            "running": item.get("State") == "running",
        })
    return containers, None


@router.get("/docker/containers")
async def docker_containers():
    """
    Liste les containers Docker. Stratégie à 3 niveaux :
      1. CLI         `docker ps`               (Windows-friendly via npipe, Linux/mac aussi)
      2. Socket Unix /var/run/docker.sock      (Linux / Docker container — no-op Windows)
      3. Docker TCP  localhost:2375            (si "Expose daemon on tcp..." activé)
    """
    # 1. CLI (works on Windows via Docker Desktop named pipe)
    containers, err_cli = await _list_containers_via_cli()
    if containers:
        return {
            "available": True,
            "source":    "docker.cli",
            "count":     len(containers),
            "containers": containers,
        }

    # 2. socket Unix
    containers, err = await _list_containers_via_socket()
    if containers:
        return {
            "available": True,
            "source":    "docker.sock",
            "count":     len(containers),
            "containers": containers,
        }

    # 3. TCP Windows (Docker Desktop — "Expose daemon on tcp://localhost:2375")
    containers, err_tcp = await _list_containers_via_tcp()
    if containers:
        return {
            "available": True,
            "source":    "docker.tcp",
            "count":     len(containers),
            "containers": containers,
        }

    # Tout a échoué — payload structuré pour le front (évite un crash 500)
    return {
        "available": False,
        "source":    "none",
        "error":     f"cli={err_cli} | sock={err} | tcp={err_tcp}",
        "containers": [],
    }


# ──────────────────────────────────────────────────────────
# CHROMADB
# ──────────────────────────────────────────────────────────
@router.get("/chromadb/stats")
async def chromadb_stats():
    """Heartbeat + nombre de collections."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            # Heartbeat (v1 ou v2 selon image)
            try:
                hb = await c.get(f"{CHROMADB_URL}/api/v2/heartbeat")
                if hb.status_code == 404:
                    hb = await c.get(f"{CHROMADB_URL}/api/v1/heartbeat")
            except Exception:
                hb = await c.get(f"{CHROMADB_URL}/api/v1/heartbeat")
            hb.raise_for_status()
            heartbeat = hb.json()

            # Liste des collections — v2 préféré, fallback v1
            try:
                cols = await c.get(f"{CHROMADB_URL}/api/v2/collections", params={"tenant": "default_tenant", "database": "default_database"})
                if cols.status_code in (404, 422):
                    cols = await c.get(f"{CHROMADB_URL}/api/v1/collections")
                cols.raise_for_status()
                collections_count = len(cols.json())
            except Exception:
                collections_count = None

        return {
            "available":   True,
            "heartbeat":   heartbeat,
            "collections": collections_count,
        }
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}", "collections": 0}


# ──────────────────────────────────────────────────────────
# SONARQUBE
# ──────────────────────────────────────────────────────────
@router.get("/sonarqube/issues")
async def sonarqube_issues():
    """Synthèse des issues SonarQube. Auth: SONARQUBE_TOKEN si défini, sinon admin/admin."""
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            auth=_sonar_auth(),
        ) as c:
            r = await c.get(f"{SONARQUBE_URL}/api/issues/search", params={"ps": 1})
            r.raise_for_status()
            payload = r.json()
            facets = {}
            # On compte par sévérité avec un second appel léger
            try:
                r2 = await c.get(
                    f"{SONARQUBE_URL}/api/issues/search",
                    params={"ps": 1, "facets": "severities"},
                )
                if r2.status_code == 200:
                    for f in r2.json().get("facets", []):
                        if f.get("property") == "severities":
                            facets = {v["val"]: v["count"] for v in f.get("values", [])}
            except Exception:
                pass

            return {
                "available": True,
                "total":     payload.get("total", 0),
                "facets":    facets,
            }
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}", "total": 0, "facets": {}}


@router.get("/sonarqube/health")
async def sonarqube_health():
    """État de santé SonarQube (peut prendre 2-3 min à boot)."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(f"{SONARQUBE_URL}/api/system/status")
            r.raise_for_status()
            return {"available": True, **r.json()}
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}"}


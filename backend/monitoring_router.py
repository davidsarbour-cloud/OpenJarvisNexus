"""
Nexus9 — Monitoring Router (Phase 4)

HTTP proxies vers les services Docker monitoring (cAdvisor, Prometheus,
ChromaDB, SonarQube). Aucun accès direct au docker.sock — tout passe
par les APIs HTTP natives de chaque service.

Tous les endpoints sont tolérants aux pannes : si un service est down,
on renvoie un payload structuré avec `available: False` au lieu de planter.
"""

import os
import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["monitoring"])

# Cibles configurables via env
# En dev Windows natif (2_BACKEND.bat) : les hostnames Docker ne résolvant pas,
# on utilise localhost + le port exposé dans docker-compose.yml.
# En Docker (docker-compose) : les hostnames internes fonctionnent directement.
import sys as _sys
_IS_WINDOWS_HOST = _sys.platform == "win32" and os.getenv("RUNNING_IN_DOCKER") != "1"

CADVISOR_URL   = os.getenv("CADVISOR_URL",
    "http://localhost:8888"    if _IS_WINDOWS_HOST else "http://cadvisor:8080")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL",
    "http://localhost:9090"    if _IS_WINDOWS_HOST else "http://prometheus:9090")
CHROMADB_URL   = os.getenv("CHROMADB_URL",
    "http://localhost:8001"    if _IS_WINDOWS_HOST else "http://chromadb:8000")
SONARQUBE_URL  = os.getenv("SONARQUBE_URL",
    "http://localhost:9000"    if _IS_WINDOWS_HOST else "http://sonarqube:9000")
GRAFANA_URL    = os.getenv("GRAFANA_URL",
    "http://localhost:3001"    if _IS_WINDOWS_HOST else "http://grafana:3000")
SONARQUBE_USER = os.getenv("SONARQUBE_USER", "admin")
SONARQUBE_PASS = os.getenv("SONARQUBE_PASS", "admin")

_TIMEOUT = 4.0


# ──────────────────────────────────────────────────────────
# DOCKER : socket Unix d'abord, TCP Windows en fallback, puis cAdvisor
# ──────────────────────────────────────────────────────────
DOCKER_SOCK     = os.getenv("DOCKER_SOCK", "/var/run/docker.sock")
# Docker Desktop expose aussi l'API TCP sur ce port si activé dans les settings
DOCKER_TCP_URL  = os.getenv("DOCKER_TCP_URL", "http://localhost:2375")

async def _list_containers_via_socket():
    """
    Utilise httpx avec un UDS transport pour parler au Docker REST API
    directement via /var/run/docker.sock. Aucune dependance externe.
    Retourne (containers, error) ; containers=[] si erreur.
    """
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


async def _list_containers_via_cadvisor():
    """Fallback : recupere la liste minimal des containers via cAdvisor v2.1."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(f"{CADVISOR_URL}/api/v2.1/stats/docker/?type=docker&recursive=true")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"

    containers = []
    for cid, samples in data.items():
        if not samples:
            continue
        last = samples[-1]
        spec = last.get("spec", {}) if isinstance(last, dict) else {}
        labels = spec.get("labels", {}) if isinstance(spec, dict) else {}
        name = (
            labels.get("io.kubernetes.container.name")
            or labels.get("com.docker.compose.service")
            or cid[:12]
        )
        containers.append({
            "id":      cid[:12],
            "name":    name,
            "image":   labels.get("io.docker.compose.image") or labels.get("org.opencontainers.image.title", ""),
            "running": True,
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
      1. Socket Unix /var/run/docker.sock  (Linux / Docker container)
      2. Docker TCP  localhost:2375        (Windows Docker Desktop, si activé)
      3. cAdvisor    fallback si les 2 précédents échouent
    """
    # 1. socket Unix
    containers, err = await _list_containers_via_socket()
    if containers:
        return {
            "available": True,
            "source":    "docker.sock",
            "count":     len(containers),
            "containers": containers,
        }

    # 2. TCP Windows (Docker Desktop — "Expose daemon on tcp://localhost:2375")
    containers, err_tcp = await _list_containers_via_tcp()
    if containers:
        return {
            "available": True,
            "source":    "docker.tcp",
            "count":     len(containers),
            "containers": containers,
        }

    # 3. cAdvisor
    containers, err2 = await _list_containers_via_cadvisor()
    if containers:
        return {
            "available": True,
            "source":    "cadvisor",
            "count":     len(containers),
            "containers": containers,
        }

    # Tout a échoué — payload structuré pour le front (évite un crash 500)
    return {
        "available": False,
        "source":    "none",
        "error":     f"sock={err} | tcp={err_tcp} | cadvisor={err2}",
        "containers": [],
    }


# ──────────────────────────────────────────────────────────
# PROMETHEUS
# ──────────────────────────────────────────────────────────
@router.get("/prometheus/query")
async def prometheus_query(q: str = "up"):
    """Proxy léger vers /api/v1/query — utile pour les widgets HUD."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": q})
            r.raise_for_status()
            return {"available": True, **r.json()}
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}"}


@router.get("/prometheus/targets")
async def prometheus_targets():
    """État des scrape jobs (UP / DOWN par target)."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(f"{PROMETHEUS_URL}/api/v1/targets")
            r.raise_for_status()
            payload = r.json()
            active = payload.get("data", {}).get("activeTargets", [])
            up   = sum(1 for t in active if t.get("health") == "up")
            down = sum(1 for t in active if t.get("health") != "up")
            return {
                "available": True,
                "total": len(active),
                "up":    up,
                "down":  down,
                "targets": [
                    {"job": t.get("labels", {}).get("job"), "health": t.get("health")}
                    for t in active
                ],
            }
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}", "total": 0, "up": 0, "down": 0, "targets": []}


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
    """Synthèse des issues SonarQube. SonarQube auth basique admin/admin par défaut."""
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            auth=(SONARQUBE_USER, SONARQUBE_PASS),
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


# ──────────────────────────────────────────────────────────
# GRAFANA
# ──────────────────────────────────────────────────────────
@router.get("/grafana/health")
async def grafana_health():
    """État de santé Grafana — heartbeat + nombre de dashboards."""
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            # Basic auth Grafana admin/admin par défaut (configurable via env)
            auth=(
                os.getenv("GRAFANA_USER", "admin"),
                os.getenv("GRAFANA_PASS", "admin"),
            ),
        ) as c:
            # Heartbeat officiel Grafana
            hb = await c.get(f"{GRAFANA_URL}/api/health")
            if hb.status_code != 200:
                return {
                    "available": False,
                    "error": f"HTTP {hb.status_code}",
                    "dashboards": 0,
                }
            health_data = hb.json()

            # Compte des dashboards (optionnel — ne bloque pas si ça échoue)
            dashboards = 0
            try:
                r2 = await c.get(f"{GRAFANA_URL}/api/search", params={"type": "dash-db", "limit": 1})
                if r2.status_code == 200:
                    dashboards = int(r2.headers.get("X-Total-Count", len(r2.json())))
            except Exception:
                pass

        return {
            "available":  True,
            "version":    health_data.get("version", "?"),
            "database":   health_data.get("database", "?"),
            "dashboards": dashboards,
        }
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}", "dashboards": 0}

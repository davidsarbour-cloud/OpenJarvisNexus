"""Docker control endpoints — container status, stats, logs, actions, compose.

Extracted from main.py. Fully self-contained: each handler imports from
tools.docker_tools and returns its result; no shared app state.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/v1/docker", tags=["docker"])


@router.get("/status")
def docker_status_endpoint():
    """Liste tous les containers Docker avec état, ports, santé."""
    from tools.docker_tools import docker_status
    return docker_status()


@router.get("/stats")
def docker_stats_endpoint(name: str = None):
    """CPU / RAM de tous les containers (ou d'un seul si name fourni)."""
    from tools.docker_tools import docker_stats
    return docker_stats(name)


@router.get("/logs/{name}")
def docker_logs_endpoint(name: str, lines: int = 40):
    """Dernières N lignes de logs d'un container."""
    from tools.docker_tools import docker_logs
    return docker_logs(name, lines)


@router.post("/action")
def docker_action_endpoint(body: dict):
    """start | stop | restart un container. Body: {name, action}."""
    from tools.docker_tools import docker_container_action
    return docker_container_action(
        name=body.get("name", ""),
        action=body.get("action", ""),
    )


@router.post("/compose")
def docker_compose_endpoint(body: dict):
    """docker compose up | down | ps | restart. Body: {action}."""
    from tools.docker_tools import docker_compose_action
    return docker_compose_action(action=body.get("action", "ps"))

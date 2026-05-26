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


@router.post("/pipeline")
async def docker_pipeline_endpoint(voice: bool = False):
    """
    Full Docker pipeline : check daemon → launch Docker Desktop if down →
    kill native port conflicts → docker compose up -d → poll container status.
    Returns {ok, containers, count, up, killed, error?}.
    """
    from pipeline_runner import run_docker
    return await run_docker(voice=voice)


@router.post("/restart")
async def docker_restart_endpoint():
    """
    `docker compose restart` — restart every container of the Nexus9 stack
    in place. Faster than a full up cycle: keeps volumes/networks, just
    cycles the processes. Returns {ok, output, count, up, error?}.
    """
    import asyncio
    import subprocess
    from pathlib import Path

    compose_dir = Path(__file__).parent.parent  # racine (docker-compose.yml)

    # Services we never restart from the UI: the user runs these natively
    # in dev mode (uvicorn + Vite), so restarting their containers would
    # collide with the host processes on ports 8000 / 5173.
    EXCLUDE = {"backend", "frontend"}

    def _run_sync() -> tuple[int, str]:
        # Sync subprocess.run captures stdout/stderr reliably on Windows
        # (Docker CLI sometimes doesn't flush async pipes properly).
        try:
            # 1. List all services from the compose file
            cfg = subprocess.run(
                ["docker", "compose", "config", "--services"],
                cwd=str(compose_dir),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=15,
            )
            if cfg.returncode != 0:
                return cfg.returncode, (cfg.stderr or "compose config failed").strip()
            services = [s for s in cfg.stdout.strip().splitlines() if s and s not in EXCLUDE]
            if not services:
                return 0, "no services to restart (all excluded)"

            # 2. Restart only the filtered services
            r = subprocess.run(
                ["docker", "compose", "restart", "--timeout", "10", *services],
                cwd=str(compose_dir),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=180,
            )
            combined = ((r.stdout or "") + (r.stderr or "")).strip()
            if combined:
                combined = f"Restarted {len(services)} services (excluded: {', '.join(sorted(EXCLUDE))})\n{combined}"
            return r.returncode, combined
        except FileNotFoundError:
            return -1, "docker CLI introuvable (Docker Desktop installé ?)"
        except subprocess.TimeoutExpired:
            return -2, "docker compose restart > 180s"
        except Exception as e:
            return -3, str(e)

    try:
        returncode, output = await asyncio.to_thread(_run_sync)
    except Exception as e:
        return {"ok": False, "error": str(e), "output": "", "count": 0, "up": 0}

    ok = returncode == 0

    # Poll container status after restart
    count = 0
    up = 0
    try:
        from tools.docker_tools import docker_status
        st = docker_status()
        containers = st.get("containers", [])
        count = len(containers)
        up = sum(1 for c in containers if c.get("running"))
    except Exception:
        pass

    return {
        "ok": ok,
        "output": output[:2000],
        "count": count,
        "up": up,
        "error": None if ok else output[:500],
        "returncode": returncode,
    }

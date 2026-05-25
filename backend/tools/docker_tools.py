"""
Docker Tools — operations Docker exposees a JARVIS via Claude tool_use.

Strategie d'acces (pas de CLI docker dans le conteneur backend) :
  1. Socket Unix /var/run/docker.sock  via httpx.HTTPTransport(uds=...)
  2. Docker TCP localhost:2375          Docker Desktop "Expose daemon on tcp"
  3. Erreur structuree               (jamais de plantage)

Tout texte retourne est sans emoji — JARVIS ne doit pas en produire.
"""
from __future__ import annotations
import json
import os
import httpx
from typing import Any

DOCKER_SOCK    = os.getenv("DOCKER_SOCK",    "/var/run/docker.sock")
DOCKER_TCP_URL = os.getenv("DOCKER_TCP_URL", "http://localhost:2375")
_TIMEOUT       = 5.0


# ── Client Docker (sync) ────────────────────────────────────────────────────

def _call_docker(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """
    Essaie socket Unix d'abord, puis TCP.
    Leve httpx.RequestError si les deux echouent.
    """
    errors = []

    # 1. Socket Unix
    try:
        transport = httpx.HTTPTransport(uds=DOCKER_SOCK)
        with httpx.Client(transport=transport, base_url="http://docker", timeout=_TIMEOUT) as c:
            resp = c.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp
    except Exception as e:
        errors.append(f"sock: {e}")

    # 2. TCP Docker Desktop
    try:
        with httpx.Client(base_url=DOCKER_TCP_URL, timeout=_TIMEOUT) as c:
            resp = c.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp
    except Exception as e:
        errors.append(f"tcp: {e}")

    raise ConnectionError(" | ".join(errors))


# ── Fonctions outils ────────────────────────────────────────────────────────

def docker_status() -> dict:
    """Liste tous les containers avec statut, image, ports."""
    try:
        r = _call_docker("GET", "/containers/json", params={"all": "true"})
        data = r.json()
    except Exception as e:
        return {"ok": False, "error": str(e), "containers": [], "up": 0, "down": 0, "total": 0}

    containers = []
    for item in data:
        name    = (item.get("Names") or ["?"])[0].lstrip("/")
        state   = item.get("State", "?")
        status  = item.get("Status", "?")
        image   = item.get("Image", "?")
        ports   = ", ".join(
            f"{p.get('PublicPort', '')}:{p.get('PrivatePort', '')}"
            for p in (item.get("Ports") or [])
            if p.get("PublicPort")
        ) or ""
        containers.append({
            "name":    name,
            "image":   image,
            "state":   state,
            "status":  status,
            "ports":   ports,
            "running": state == "running",
        })

    up   = sum(1 for c in containers if c["running"])
    down = len(containers) - up
    return {"ok": True, "containers": containers, "up": up, "down": down, "total": len(containers)}


def docker_container_action(name: str, action: str) -> dict:
    """
    Start, stop ou restart un container via l'API REST Docker.
    action : 'start' | 'stop' | 'restart'
    """
    if action not in ("start", "stop", "restart"):
        return {"ok": False, "error": f"Action inconnue : {action}"}
    try:
        _call_docker("POST", f"/containers/{name}/{action}")
        return {"ok": True, "container": name, "action": action, "output": f"{action} OK"}
    except httpx.HTTPStatusError as e:
        return {"ok": False, "container": name, "action": action, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"ok": False, "container": name, "action": action, "error": str(e)}


def docker_logs(name: str, lines: int = 40) -> dict:
    """Recupere les N dernieres lignes de logs via l'API REST Docker."""
    try:
        r = _call_docker(
            "GET",
            f"/containers/{name}/logs",
            params={"tail": str(lines), "stdout": "true", "stderr": "true"},
        )
        # Docker logs stream peut contenir un header binaire de 8 octets par frame
        raw = r.content
        log_lines = []
        i = 0
        while i < len(raw):
            if i + 8 <= len(raw):
                # Header: [stream_type(1), 0,0,0, size(4 big-endian)]
                size = int.from_bytes(raw[i + 4 : i + 8], "big")
                chunk = raw[i + 8 : i + 8 + size]
                log_lines.append(chunk.decode("utf-8", errors="replace"))
                i += 8 + size
            else:
                log_lines.append(raw[i:].decode("utf-8", errors="replace"))
                break
        log_text = "".join(log_lines).strip()
        if not log_text:
            log_text = r.text.strip()
        return {"ok": True, "container": name, "lines": lines, "logs": log_text}
    except Exception as e:
        return {"ok": False, "container": name, "lines": lines, "logs": "", "error": str(e)}


def docker_compose_action(action: str) -> dict:
    """
    Pour 'ps' : utilise l'API REST (liste containers avec label compose).
    Pour 'up'/'down'/'restart' : retourne une instruction claire (pas de CLI).
    """
    if action == "ps":
        result = docker_status()
        return {
            "ok":         result["ok"],
            "action":     "ps",
            "containers": result.get("containers", []),
            "up":         result.get("up", 0),
            "total":      result.get("total", 0),
        }
    return {
        "ok":     False,
        "action": action,
        "error":  f"Action '{action}' non disponible sans CLI docker dans le conteneur. Utilisez docker_container_action pour agir sur un container specifique.",
    }


def docker_stats(name: str | None = None) -> dict:
    """CPU et memoire via /containers/{id}/stats?stream=false."""
    # On recupere d'abord la liste pour avoir les IDs
    status = docker_status()
    if not status["ok"]:
        return {"ok": False, "error": status.get("error", "?"), "stats": []}

    targets = status["containers"]
    if name:
        targets = [c for c in targets if name in c["name"]]

    stats = []
    for c in targets[:8]:  # max 8 pour eviter timeout
        try:
            r = _call_docker(
                "GET",
                f"/containers/{c['name']}/stats",
                params={"stream": "false"},
            )
            s = r.json()
            # Calcul CPU %
            cpu_delta    = s["cpu_stats"]["cpu_usage"]["total_usage"] - s["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = s["cpu_stats"]["system_cpu_usage"] - s["precpu_stats"].get("system_cpu_usage", 0)
            num_cpus     = s["cpu_stats"].get("online_cpus") or len(s["cpu_stats"]["cpu_usage"].get("percpu_usage", [1]))
            cpu_pct      = round((cpu_delta / system_delta) * num_cpus * 100.0, 1) if system_delta > 0 else 0.0
            # Memoire
            mem_usage = s["memory_stats"].get("usage", 0)
            mem_limit = s["memory_stats"].get("limit", 1)
            mem_pct   = round(mem_usage / mem_limit * 100.0, 1)
            mem_mb    = round(mem_usage / 1024 / 1024, 1)
            stats.append({
                "name":    c["name"],
                "cpu":     f"{cpu_pct}%",
                "mem_mb":  f"{mem_mb} MB",
                "mem_pct": f"{mem_pct}%",
            })
        except Exception:
            stats.append({"name": c["name"], "cpu": "?", "mem_mb": "?", "mem_pct": "?"})

    return {"ok": True, "stats": stats}


# ── Résumé texte rapide pour injection Ollama (sans emoji) ─────────────────

def quick_status_text() -> str:
    """
    Resumé texte du statut Docker — injecte dans le prompt Ollama.
    Aucun emoji, texte brut.
    """
    s = docker_status()
    if not s["ok"]:
        return f"Docker inaccessible : {s.get('error', '?')}"

    lines = [f"Docker — {s['up']}/{s['total']} containers UP\n"]
    for c in s["containers"]:
        state = "UP  " if c["running"] else "DOWN"
        name  = c["name"].replace("nexus_", "")
        ports = f"  [{c['ports']}]" if c["ports"] else ""
        lines.append(f"  {state}  {name:<20}{c['status']}{ports}")
    return "\n".join(lines)


# ── Définitions outils pour Claude tool_use ────────────────────────────────

CLAUDE_TOOL_DEFS = [
    {
        "name": "docker_status",
        "description": (
            "Liste tous les containers Docker avec leur etat (running/stopped), "
            "ports exposes, image utilisee. Utilise cet outil quand l'utilisateur "
            "demande l'etat de Docker, des containers, ou de l'infra."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "docker_container_action",
        "description": (
            "Demarre, arrete ou redemarre un container Docker par son nom. "
            "Le nom peut etre partiel (ex: 'backend'). "
            "Utilise docker_status d'abord si tu ne connais pas le nom exact."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name":   {"type": "string", "description": "Nom du container (ex: nexus_backend)"},
                "action": {"type": "string", "enum": ["start", "stop", "restart"]},
            },
            "required": ["name", "action"],
        },
    },
    {
        "name": "docker_logs",
        "description": (
            "Recupere les logs recents d'un container Docker. "
            "Utilise pour diagnostiquer erreurs ou comprendre ce que fait un service."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name":  {"type": "string",  "description": "Nom du container"},
                "lines": {"type": "integer", "description": "Nombre de lignes (defaut 40)", "default": 40},
            },
            "required": ["name"],
        },
    },
    {
        "name": "docker_compose_action",
        "description": "Statut global docker compose (ps). Pour up/down/restart, utilise docker_container_action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["up", "down", "ps", "restart"]},
            },
            "required": ["action"],
        },
    },
    {
        "name": "docker_stats",
        "description": "Consommation CPU et memoire des containers Docker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nom du container (vide = tous)"},
            },
            "required": [],
        },
    },
]


# ── Dispatcher ──────────────────────────────────────────────────────────────

def dispatch(tool_name: str, tool_input: dict) -> str:
    """Reçoit un appel outil Claude et retourne le résultat en JSON string."""
    try:
        if tool_name == "docker_status":
            result = docker_status()
        elif tool_name == "docker_container_action":
            result = docker_container_action(
                name=tool_input.get("name", ""),
                action=tool_input.get("action", ""),
            )
        elif tool_name == "docker_logs":
            result = docker_logs(
                name=tool_input.get("name", ""),
                lines=tool_input.get("lines", 40),
            )
        elif tool_name == "docker_compose_action":
            result = docker_compose_action(action=tool_input.get("action", "ps"))
        elif tool_name == "docker_stats":
            result = docker_stats(name=tool_input.get("name"))
        else:
            result = {"ok": False, "error": f"Outil inconnu : {tool_name}"}
    except Exception as e:
        result = {"ok": False, "error": str(e)}

    return json.dumps(result, ensure_ascii=False, indent=2)

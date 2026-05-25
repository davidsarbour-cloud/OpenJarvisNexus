"""
Docker Tools — operations Docker exposees a JARVIS via Claude tool_use.

Strategie adaptative selon l'environnement :
  Windows natif  : subprocess docker.exe (installe par Docker Desktop)
  Linux/container: API REST via socket Unix ou TCP

Tout texte retourne est sans emoji.
"""
from __future__ import annotations
import json
import os
import sys
import subprocess
import httpx
from typing import Any

DOCKER_SOCK    = os.getenv("DOCKER_SOCK",    "/var/run/docker.sock")
DOCKER_TCP_URL = os.getenv("DOCKER_TCP_URL", "http://localhost:2375")
_TIMEOUT       = 8.0
_IS_WINDOWS    = sys.platform == "win32"


# ══════════════════════════════════════════════════════════════════════════════
# Backend Windows : subprocess docker.exe
# ══════════════════════════════════════════════════════════════════════════════

def _run(cmd: list[str], timeout: int = 15) -> tuple[bool, str]:
    """Exécute docker CLI, retourne (ok, output). Windows uniquement."""
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, f"Timeout apres {timeout}s"
    except FileNotFoundError:
        return False, "docker.exe introuvable — Docker Desktop installe ?"
    except Exception as e:
        return False, str(e)


def _docker_status_windows() -> dict:
    """Liste les containers via docker CLI (Windows natif)."""
    ok, out = _run(["docker", "ps", "-a", "--format", "{{json .}}"])
    if not ok:
        return {"ok": False, "error": out, "containers": [], "up": 0, "down": 0, "total": 0}

    containers = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            c = json.loads(line)
            name   = c.get("Names", "?")
            state  = c.get("State", "?")
            status = c.get("Status", "?")
            image  = c.get("Image", "?")
            ports  = c.get("Ports", "")
            containers.append({
                "name":    name,
                "image":   image,
                "state":   state,
                "status":  status,
                "ports":   ports,
                "running": state == "running",
            })
        except Exception:
            pass

    up   = sum(1 for c in containers if c["running"])
    down = len(containers) - up
    return {"ok": True, "source": "cli", "containers": containers, "up": up, "down": down, "total": len(containers)}


def _docker_action_windows(name: str, action: str) -> dict:
    ok, out = _run(["docker", action, name])
    return {"ok": ok, "container": name, "action": action, "output": out}


def _docker_logs_windows(name: str, lines: int = 40) -> dict:
    ok, out = _run(["docker", "logs", "--tail", str(lines), name], timeout=10)
    return {"ok": ok, "container": name, "lines": lines, "logs": out}


def _docker_stats_windows(name: str | None = None) -> dict:
    cmd = ["docker", "stats", "--no-stream", "--format", "{{json .}}"]
    if name:
        cmd.append(name)
    ok, out = _run(cmd, timeout=10)
    if not ok:
        return {"ok": False, "error": out, "stats": []}
    stats = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            s = json.loads(line)
            stats.append({
                "name":    s.get("Name", "?"),
                "cpu":     s.get("CPUPerc", "?"),
                "mem_mb":  s.get("MemUsage", "?"),
                "mem_pct": s.get("MemPerc", "?"),
            })
        except Exception:
            pass
    return {"ok": ok, "stats": stats}


# ══════════════════════════════════════════════════════════════════════════════
# Backend Linux / container : REST API Docker socket ou TCP
# ══════════════════════════════════════════════════════════════════════════════

def _call_docker(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Socket Unix d'abord, TCP ensuite. Linux uniquement."""
    errors = []

    # Socket Unix
    try:
        transport = httpx.HTTPTransport(uds=DOCKER_SOCK)
        with httpx.Client(transport=transport, base_url="http://docker", timeout=_TIMEOUT) as c:
            resp = c.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp
    except Exception as e:
        errors.append(f"sock: {e}")

    # TCP
    try:
        with httpx.Client(base_url=DOCKER_TCP_URL, timeout=_TIMEOUT) as c:
            resp = c.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp
    except Exception as e:
        errors.append(f"tcp: {e}")

    raise ConnectionError(" | ".join(errors))


def _docker_status_linux() -> dict:
    """Liste les containers via API REST Docker (socket/TCP). Linux/container."""
    try:
        r = _call_docker("GET", "/containers/json", params={"all": "true"})
        data = r.json()
    except Exception as e:
        return {"ok": False, "error": str(e), "containers": [], "up": 0, "down": 0, "total": 0}

    containers = []
    for item in data:
        name   = (item.get("Names") or ["?"])[0].lstrip("/")
        state  = item.get("State", "?")
        status = item.get("Status", "?")
        image  = item.get("Image", "?")
        ports  = ", ".join(
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
    return {"ok": True, "source": "api", "containers": containers, "up": up, "down": down, "total": len(containers)}


# ══════════════════════════════════════════════════════════════════════════════
# API publique — routage automatique Windows / Linux
# ══════════════════════════════════════════════════════════════════════════════

def docker_status() -> dict:
    """Liste tous les containers. Adapte la methode selon l'OS."""
    if _IS_WINDOWS:
        return _docker_status_windows()
    return _docker_status_linux()


def docker_container_action(name: str, action: str) -> dict:
    if action not in ("start", "stop", "restart"):
        return {"ok": False, "error": f"Action inconnue : {action}"}
    if _IS_WINDOWS:
        return _docker_action_windows(name, action)
    try:
        _call_docker("POST", f"/containers/{name}/{action}")
        return {"ok": True, "container": name, "action": action, "output": f"{action} OK"}
    except Exception as e:
        return {"ok": False, "container": name, "action": action, "error": str(e)}


def docker_logs(name: str, lines: int = 40) -> dict:
    if _IS_WINDOWS:
        return _docker_logs_windows(name, lines)
    try:
        r = _call_docker("GET", f"/containers/{name}/logs",
                         params={"tail": str(lines), "stdout": "true", "stderr": "true"})
        raw = r.content
        log_lines = []
        i = 0
        while i < len(raw):
            if i + 8 <= len(raw):
                size = int.from_bytes(raw[i + 4: i + 8], "big")
                chunk = raw[i + 8: i + 8 + size]
                log_lines.append(chunk.decode("utf-8", errors="replace"))
                i += 8 + size
            else:
                log_lines.append(raw[i:].decode("utf-8", errors="replace"))
                break
        log_text = "".join(log_lines).strip() or r.text.strip()
        return {"ok": True, "container": name, "lines": lines, "logs": log_text}
    except Exception as e:
        return {"ok": False, "container": name, "lines": lines, "logs": "", "error": str(e)}


def docker_compose_action(action: str) -> dict:
    if action == "ps":
        result = docker_status()
        return {"ok": result["ok"], "action": "ps",
                "containers": result.get("containers", []),
                "up": result.get("up", 0), "total": result.get("total", 0)}
    return {"ok": False, "action": action,
            "error": f"Action '{action}' : utilisez docker_container_action pour agir sur un container specifique."}


def docker_stats(name: str | None = None) -> dict:
    if _IS_WINDOWS:
        return _docker_stats_windows(name)
    status = docker_status()
    if not status["ok"]:
        return {"ok": False, "error": status.get("error", "?"), "stats": []}
    targets = status["containers"]
    if name:
        targets = [c for c in targets if name in c["name"]]
    stats = []
    for c in targets[:8]:
        try:
            r = _call_docker("GET", f"/containers/{c['name']}/stats", params={"stream": "false"})
            s = r.json()
            cpu_delta    = s["cpu_stats"]["cpu_usage"]["total_usage"] - s["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = s["cpu_stats"]["system_cpu_usage"] - s["precpu_stats"].get("system_cpu_usage", 0)
            num_cpus     = s["cpu_stats"].get("online_cpus") or len(s["cpu_stats"]["cpu_usage"].get("percpu_usage", [1]))
            cpu_pct      = round((cpu_delta / system_delta) * num_cpus * 100.0, 1) if system_delta > 0 else 0.0
            mem_usage    = s["memory_stats"].get("usage", 0)
            mem_limit    = s["memory_stats"].get("limit", 1)
            mem_pct      = round(mem_usage / mem_limit * 100.0, 1)
            mem_mb       = round(mem_usage / 1024 / 1024, 1)
            stats.append({"name": c["name"], "cpu": f"{cpu_pct}%",
                          "mem_mb": f"{mem_mb} MB", "mem_pct": f"{mem_pct}%"})
        except Exception:
            stats.append({"name": c["name"], "cpu": "?", "mem_mb": "?", "mem_pct": "?"})
    return {"ok": True, "stats": stats}


# ── Résumé texte rapide pour injection Ollama (sans emoji) ─────────────────

def _short_ports(ports_str: str) -> str:
    """Extrait seulement les ports hote uniques. '0.0.0.0:8000->8000/tcp, ...' -> '[8000]'"""
    if not ports_str:
        return ""
    seen = []
    for part in ports_str.split(","):
        part = part.strip()
        # Cherche le pattern host_port->container_port
        if "->" in part:
            left = part.split("->")[0]
            host_port = left.split(":")[-1]
            if host_port and host_port not in seen:
                seen.append(host_port)
    return f"  [{', '.join(seen)}]" if seen else ""


def quick_status_text() -> str:
    s = docker_status()
    if not s["ok"]:
        return f"Docker inaccessible : {s.get('error', '?')}"
    lines = [f"Docker -- {s['up']}/{s['total']} containers UP\n"]
    for c in s["containers"]:
        state = "UP  " if c["running"] else "DOWN"
        name  = c["name"].replace("nexus_", "")
        ports = _short_ports(c.get("ports", ""))
        # Status : garde seulement la partie avant les parens (ex: "Up 5 minutes")
        st = c["status"].split("(")[0].strip()
        lines.append(f"  {state}  {name:<20}{st}{ports}")
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
        "description": "Recupere les logs recents d'un container Docker.",
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
        "description": "Statut global docker compose (ps).",
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

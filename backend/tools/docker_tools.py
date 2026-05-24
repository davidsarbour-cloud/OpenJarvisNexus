"""
Docker Tools — opérations Docker exposées à JARVIS via Claude tool_use.

JARVIS peut :
  • Lister les containers et leur statut
  • Démarrer / arrêter / redémarrer un container
  • Lire les logs d'un container
  • Exécuter docker compose up/down/ps
  • Inspecter les ressources (CPU, RAM) d'un container
"""
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path

COMPOSE_DIR = Path(__file__).parent.parent.parent  # racine projet (docker-compose.yml)


def _run(cmd: list[str], timeout: int = 15) -> tuple[bool, str]:
    """Exécute une commande, retourne (ok, output)."""
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
        return False, f"Timeout après {timeout}s"
    except Exception as e:
        return False, str(e)


# ── Outils exposés ──────────────────────────────────────────────────────────

def docker_status() -> dict:
    """Liste tous les containers Docker avec statut, ports et santé."""
    ok, out = _run(["docker", "ps", "-a",
                    "--format", "{{json .}}"])
    if not ok:
        # Daemon peut-être éteint
        return {"ok": False, "error": out, "containers": []}

    containers = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            c = json.loads(line)
            containers.append({
                "name":    c.get("Names", "?"),
                "image":   c.get("Image", "?"),
                "status":  c.get("Status", "?"),
                "state":   c.get("State", "?"),
                "ports":   c.get("Ports", ""),
                "running": c.get("State", "") == "running",
            })
        except Exception:
            pass

    up   = sum(1 for c in containers if c["running"])
    down = len(containers) - up
    return {"ok": True, "containers": containers, "up": up, "down": down, "total": len(containers)}


def docker_container_action(name: str, action: str) -> dict:
    """
    Start, stop ou restart un container.
    action : 'start' | 'stop' | 'restart'
    """
    if action not in ("start", "stop", "restart"):
        return {"ok": False, "error": f"Action inconnue : {action}"}

    ok, out = _run(["docker", action, name])
    return {"ok": ok, "container": name, "action": action, "output": out}


def docker_logs(name: str, lines: int = 40) -> dict:
    """Récupère les N dernières lignes de logs d'un container."""
    ok, out = _run(["docker", "logs", "--tail", str(lines), name], timeout=10)
    return {"ok": ok, "container": name, "lines": lines, "logs": out}


def docker_compose_action(action: str) -> dict:
    """
    Exécute une commande docker compose.
    action : 'up' | 'down' | 'ps' | 'restart'
    """
    if action == "up":
        cmd = ["docker", "compose", "up", "-d"]
    elif action == "down":
        cmd = ["docker", "compose", "down"]
    elif action == "ps":
        cmd = ["docker", "compose", "ps", "--format", "json"]
    elif action == "restart":
        cmd = ["docker", "compose", "restart"]
    else:
        return {"ok": False, "error": f"Action compose inconnue : {action}"}

    ok, out = _run(cmd, cwd=str(COMPOSE_DIR), timeout=60)

    if action == "ps":
        containers = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                containers.append({
                    "name":   c.get("Name", "?"),
                    "status": c.get("Status", "?"),
                    "state":  c.get("State", "?"),
                })
            except Exception:
                pass
        return {"ok": ok, "action": action, "containers": containers}

    return {"ok": ok, "action": action, "output": out}


def docker_stats(name: str | None = None) -> dict:
    """Récupère CPU, RAM d'un ou tous les containers (snapshot, pas streaming)."""
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
                "name":       s.get("Name", "?"),
                "cpu":        s.get("CPUPerc", "?"),
                "mem_usage":  s.get("MemUsage", "?"),
                "mem_pct":    s.get("MemPerc", "?"),
                "net_io":     s.get("NetIO", "?"),
                "block_io":   s.get("BlockIO", "?"),
            })
        except Exception:
            pass
    return {"ok": ok, "stats": stats}


# ── Définitions outils pour Claude tool_use ────────────────────────────────

CLAUDE_TOOL_DEFS = [
    {
        "name": "docker_status",
        "description": (
            "Liste tous les containers Docker avec leur état (running/stopped), "
            "ports exposés, image utilisée. Utilise cet outil quand l'utilisateur "
            "demande l'état de Docker, des containers, ou de l'infra."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "docker_container_action",
        "description": (
            "Démarre, arrête ou redémarre un container Docker par son nom. "
            "Le nom peut être partiel (ex: 'backend' → 'nexus_backend'). "
            "Utilise docker_status d'abord si tu ne connais pas le nom exact."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name":   {"type": "string",  "description": "Nom exact du container (ex: nexus_backend)"},
                "action": {"type": "string",  "enum": ["start", "stop", "restart"],
                           "description": "Action à effectuer"},
            },
            "required": ["name", "action"],
        },
    },
    {
        "name": "docker_logs",
        "description": (
            "Récupère les logs récents d'un container Docker. "
            "Utilise cet outil quand l'utilisateur veut voir des erreurs, "
            "diagnostiquer un problème, ou comprendre ce que fait un service."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name":  {"type": "string",  "description": "Nom du container"},
                "lines": {"type": "integer", "description": "Nombre de lignes (défaut 40)", "default": 40},
            },
            "required": ["name"],
        },
    },
    {
        "name": "docker_compose_action",
        "description": (
            "Exécute une commande docker compose globale : "
            "up (démarre tous les services), down (arrête tout), "
            "ps (statut de tous les services), restart (redémarre tout)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["up", "down", "ps", "restart"],
                           "description": "Commande compose à exécuter"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "docker_stats",
        "description": (
            "Montre la consommation CPU et mémoire des containers Docker. "
            "Utilise cet outil pour diagnostiquer des problèmes de performance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nom du container (laisser vide pour tous)"},
            },
            "required": [],
        },
    },
]


# ── Dispatcher — appelle la bonne fonction depuis un tool_use Claude ────────

def dispatch(tool_name: str, tool_input: dict) -> str:
    """
    Reçoit un appel outil Claude (name + input) et retourne le résultat en JSON string.
    """
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


# ── Helper : résumé texte rapide de docker_status pour injection Ollama ────

def quick_status_text() -> str:
    """
    Retourne un résumé texte du statut Docker.
    Utilisé pour injecter dans le prompt Ollama (pas de tool_use natif).
    """
    s = docker_status()
    if not s["ok"]:
        return f"⚠️ Docker inaccessible : {s.get('error', '?')}"
    lines = [f"🐳 Docker — {s['up']}/{s['total']} containers UP\n"]
    for c in s["containers"]:
        icon = "✅" if c["running"] else "⏸"
        name = c["name"].replace("nexus_", "").replace("/", "")
        lines.append(f"{icon} {name:<18} {c['status']}")
    return "\n".join(lines)

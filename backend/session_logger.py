"""
Nexus9 — session_logger.py

Auto-logging des sessions agent dans session_logs/YYYY-MM-DD.md.
Appelé par memory.add_message() à chaque tour user/assistant.

Format : Markdown append-only avec frontmatter daily.
Le daily sync (sync-brain.js) remontera ces logs dans BRAIN/02_Daily/sessions/.

Garde-fous :
- Jamais bloquant (try/except enveloppant)
- Append-only (pas de réécriture, pas de risque de perte)
- Filtre messages vides
- Compatible Windows (LF line endings)
"""

from __future__ import annotations

import re
import threading
from datetime import datetime
from pathlib import Path

# session_logs/ vit à la racine du repo (frère de backend/)
BASE_DIR = Path(__file__).parent          # backend/
REPO_ROOT = BASE_DIR.parent                # OpenJarvisNexus/
SESSION_LOGS_DIR = REPO_ROOT / "session_logs"

# Lock pour éviter race condition entre threads
_write_lock = threading.Lock()

# Patterns pour détecter quel agent répond (best-effort)
_AGENT_TRIGGERS = [
    (re.compile(r"!ultron\b", re.IGNORECASE),  "ULTRON"),
    (re.compile(r"!cortana\b", re.IGNORECASE), "CORTANA"),
    (re.compile(r"!nova\b", re.IGNORECASE),    "NOVA"),
    (re.compile(r"!qwen\b", re.IGNORECASE),    "QWEN"),
    (re.compile(r"!bruce\b", re.IGNORECASE),   "BRUCE"),
    (re.compile(r"!forge\b|stl|3d print|mesh|dragon", re.IGNORECASE), "FORGE"),
]


def _detect_agent(user_text: str | None) -> str:
    """Détecte l'agent ciblé d'après les triggers du message user."""
    if not user_text:
        return "JARVIS"
    for pattern, name in _AGENT_TRIGGERS:
        if pattern.search(user_text):
            return name
    return "JARVIS"


def _today_path() -> Path:
    """Retourne le chemin du log du jour, crée le dossier si besoin."""
    SESSION_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    return SESSION_LOGS_DIR / f"{today}.md"


def _ensure_day_header(path: Path) -> None:
    """Crée le fichier du jour avec son frontmatter si absent."""
    if path.exists() and path.stat().st_size > 0:
        return
    today_iso = datetime.now().strftime("%Y-%m-%d")
    header = (
        f"---\n"
        f"created: {today_iso}\n"
        f"tags: [daily, session, auto-log]\n"
        f"nexus9_session_log: true\n"
        f"---\n\n"
        f"# 📅 Sessions du {today_iso}\n\n"
        f"Auto-loggées par `backend/session_logger.py`. "
        f"Routées vers `BRAIN/02_Daily/sessions/` au prochain daily sync.\n\n"
        f"## Liens\n\n"
        f"- [[../session-history]]\n"
        f"- [[../../06_Agents/_shared/session-protocol]]\n\n"
        f"---\n\n"
    )
    path.write_text(header, encoding="utf-8")


# Variable pour grouper les tours dans une même section "session"
_last_session_id: dict[str, datetime] = {}
_SESSION_GAP_MIN = 30  # nouveau bloc visuel si > 30 min entre 2 messages


def _need_session_break(session_id: str) -> bool:
    """True si on doit ouvrir un nouveau bloc de session (gap > 30 min)."""
    now = datetime.now()
    last = _last_session_id.get(session_id)
    _last_session_id[session_id] = now
    if last is None:
        return True
    return (now - last).total_seconds() > _SESSION_GAP_MIN * 60


def _format_entry(
    session_id: str,
    role: str,
    content: str,
    agent: str,
    open_session: bool,
) -> str:
    """Formate une entrée markdown pour le log."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    lines: list[str] = []

    if open_session:
        lines.append(f"### 🟢 Session `{session_id[:8]}` — démarrée à {timestamp}\n")

    speaker = "**👤 David**" if role == "user" else f"**🤖 {agent}**"
    lines.append(f"{speaker} · `{timestamp}`\n")

    # Indent le contenu en blockquote pour différencier des notes manuelles
    safe_content = content.strip() or "_(vide)_"
    # Éviter casser les blocs markdown : on indent avec > seulement les lignes non-vides
    quoted = "\n".join(
        f"> {ln}" if ln.strip() else ">"
        for ln in safe_content.split("\n")
    )
    lines.append(quoted)
    lines.append("")  # ligne vide après chaque tour
    return "\n".join(lines)


def log_message(
    session_id: str,
    role: str,
    content: str,
    user_msg_for_routing: str | None = None,
) -> bool:
    """
    Log un message dans le fichier du jour. JAMAIS bloquant.

    Args:
        session_id: ID de session (clé interne Jarvis)
        role: "user" | "assistant" | autre (ignoré)
        content: contenu textuel du message
        user_msg_for_routing: dernier message user (pour deviner l'agent)

    Returns:
        True si écrit, False si skip ou erreur (logged silently).
    """
    if role not in ("user", "assistant"):
        return False
    if not content or not content.strip():
        return False

    try:
        with _write_lock:
            path = _today_path()
            _ensure_day_header(path)

            # Si role=user, c'est lui-même qui détermine l'agent
            # Si role=assistant, on regarde le dernier user_msg passé en param
            routing_hint = content if role == "user" else (user_msg_for_routing or "")
            agent = _detect_agent(routing_hint)

            # Nouveau bloc session seulement avant le tour user (pas l'assistant)
            need_break = (role == "user") and _need_session_break(session_id)

            entry = _format_entry(session_id, role, content, agent, need_break)

            with path.open("a", encoding="utf-8") as f:
                f.write(entry)
        return True
    except Exception as e:
        # Jamais bloquer le flux principal
        print(f"[session_logger] WARN: log failed: {e}")
        return False


def log_path_today() -> Path:
    """Helper externe : retourne le chemin du log du jour."""
    return _today_path()

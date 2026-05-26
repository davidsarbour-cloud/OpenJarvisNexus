"""
Jarvis Memory System v2
- Session : sauvegardé sur disque, survit aux redémarrages
- Facts : JSON persistant, injecté dans chaque prompt
- Résumé : récupère le contexte si la page est rafraîchie
"""

import json
import os
import time
from datetime import date
from pathlib import Path

BASE_DIR      = Path(__file__).parent
MEMORY_FILE   = BASE_DIR / "memory.json"
SESSIONS_FILE = BASE_DIR / "sessions.json"
CONFIG_FILE   = BASE_DIR / "config.json"

# ── Obsidian Vault Memory ────────────────────────────────
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", "/app/BRAIN/BRAIN"))
_VAULT_TTL = 300.0  # relit le vault toutes les 5 minutes

_vault_cache: str = ""
_vault_cache_ts: float = 0.0


def _strip_note(text: str, max_chars: int) -> str:
    """Supprime frontmatter YAML, wikilinks, lignes de tags — garde le contenu utile."""
    import re
    # Retire le bloc frontmatter ---...---
    text = re.sub(r"^---[\s\S]*?---\s*", "", text, count=1).strip()
    # Retire les wikilinks [[...]] → garde le label si présent
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
    # Retire les lignes qui ne contiennent que des hashtags (#core #goals ...)
    text = re.sub(r"^#\w+(\s+#\w+)*\s*$", "", text, flags=re.MULTILINE)
    # Retire les lignes "## Liens" et ce qui suit (pas utile pour JARVIS)
    text = re.sub(r"\n## Liens[\s\S]*", "", text)
    # Nettoie les lignes vides multiples
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…"
    return text


# Notes essentielles injectées à chaque prompt (ordre = priorité)
_CORE_ESSENTIAL = ["core-identité", "core-objectifs-2026", "core-vocabulary"]


def load_vault_memory() -> str:
    """Injecte les 3 notes essentielles du vault + note du jour si non vide.
    Cache 5 min — ~500 tokens max pour rester confortable avec num_ctx=8192."""
    global _vault_cache, _vault_cache_ts
    if _vault_cache and (time.time() - _vault_cache_ts) < _VAULT_TTL:
        return _vault_cache

    if not VAULT_PATH.exists():
        return ""

    sections: list[str] = []

    # ── 1. Notes essentielles (whitelist) ───────────────
    core_dir = VAULT_PATH / "00_Core"
    for stem in _CORE_ESSENTIAL:
        note = core_dir / f"{stem}.md"
        if not note.exists():
            continue
        try:
            raw = note.read_text(encoding="utf-8").strip()
            if not raw:
                continue
            content = _strip_note(raw, max_chars=600)
            sections.append(f"[{stem}]\n{content}")
        except Exception:
            continue

    # ── 2. Note du jour (si non vide) ───────────────────
    today_file = VAULT_PATH / f"{date.today().isoformat()}.md"
    if not today_file.exists():
        candidates = sorted(VAULT_PATH.glob("20??-??-??.md"), reverse=True)
        today_file = candidates[0] if candidates else None

    if today_file and today_file.exists():
        try:
            raw = today_file.read_text(encoding="utf-8").strip()
            if raw:
                content = _strip_note(raw, max_chars=500)
                sections.append(f"[note du jour: {today_file.stem}]\n{content}")
        except Exception:
            pass

    if not sections:
        return ""

    result = (
        "\n\n━━━ CONTEXTE DAVID ━━━\n"
        + "\n\n".join(sections)
        + "\n━━━ FIN CONTEXTE ━━━"
    )
    _vault_cache    = result
    _vault_cache_ts = time.time()
    return result

MAX_HISTORY = 40
SESSION_TTL = 86400  # 24 heures


# ── Config — TTL cache 30 s (évite lecture disque à chaque message) ─────────
_config_cache: dict = {}
_config_cache_ts: float = 0.0
_CONFIG_TTL = 30.0

def load_config() -> dict:
    global _config_cache, _config_cache_ts
    if _config_cache and (time.time() - _config_cache_ts) < _CONFIG_TTL:
        return _config_cache
    if CONFIG_FILE.exists():
        try:
            _config_cache    = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            _config_cache_ts = time.time()
            return _config_cache
        except Exception:
            pass
    return {}


# ── Sessions (RAM + disque) ─────────────────────────────
_sessions: dict[str, dict] = {}


def _load_sessions() -> None:
    global _sessions
    if SESSIONS_FILE.exists():
        try:
            data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
            now  = time.time()
            _sessions = {
                sid: s for sid, s in data.items()
                if now - s.get("last_active", 0) < SESSION_TTL
            }
        except Exception:
            _sessions = {}


def _save_sessions() -> None:
    try:
        SESSIONS_FILE.write_text(
            json.dumps(_sessions, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"[memory] erreur sauvegarde session: {e}")


_load_sessions()


def get_history(session_id: str) -> list[dict]:
    if session_id not in _sessions:
        _sessions[session_id] = {"messages": [], "last_active": time.time()}
    _sessions[session_id]["last_active"] = time.time()
    msgs = _sessions[session_id]["messages"]
    return msgs[-MAX_HISTORY:] if len(msgs) > MAX_HISTORY else msgs


def add_message(session_id: str, role: str, content: str) -> None:
    if session_id not in _sessions:
        _sessions[session_id] = {"messages": [], "last_active": time.time()}
    _sessions[session_id]["messages"].append({
        "role": role, "content": content
    })
    _sessions[session_id]["last_active"] = time.time()
    _save_sessions()

    # ── Auto-log vers session_logs/YYYY-MM-DD.md ──────────────
    # Non-bloquant : si le logger échoue, on continue normalement.
    try:
        from session_logger import log_message as _log_session
        # Pour deviner l'agent on regarde le dernier message user de la session
        last_user_msg = None
        if role == "assistant":
            for m in reversed(_sessions[session_id]["messages"]):
                if m["role"] == "user":
                    last_user_msg = m["content"]
                    break
        _log_session(session_id, role, content, user_msg_for_routing=last_user_msg)
    except Exception:
        # Silencieux : pas de crash sur erreur de logging
        pass


def clear_session(session_id: str) -> None:
    if session_id in _sessions:
        _sessions[session_id]["messages"] = []
        _save_sessions()


def list_sessions() -> list[dict]:
    return [
        {
            "id":          sid,
            "messages":    len(s.get("messages", [])),
            "last_active": s.get("last_active", 0)
        }
        for sid, s in _sessions.items()
    ]


def get_last_session_summary(session_id: str) -> str:
    """Résume la dernière session pour récupérer le contexte après refresh."""
    cfg = load_config()
    n = cfg.get("session_continuity", {}).get("max_summary_messages", 10)
    msgs = get_history(session_id)
    if not msgs:
        return ""
    lines = []
    for m in msgs[-n:]:
        role = "David" if m["role"] == "user" else "Jarvis"
        lines.append(f"{role}: {m['content'][:120]}...")
    return "Résumé de la conversation précédente:\n" + "\n".join(lines)


def is_new_session(session_id: str) -> bool:
    """
    True si la session a dépassé le gap d'inactivité configuré
    (ou si elle n'a pas encore de messages).
    Doit être appelé AVANT add_message pour être précis.
    """
    cfg = load_config()
    sc_cfg = cfg.get("session_continuity", {})
    if not sc_cfg.get("enabled", True):
        return False
    gap_seconds = sc_cfg.get("gap_minutes", 60) * 60
    sess = _sessions.get(session_id)
    if not sess or not sess.get("messages"):
        return True
    last_active = sess.get("last_active", 0)
    return (time.time() - last_active) > gap_seconds


def compress_session_sync(session_id: str) -> int:
    """
    Compresse les anciens messages de la session via Ollama (synchrone).
    Retourne le nombre de messages compressés (0 si seuil non atteint ou erreur).
    Doit être appelé depuis un endpoint sync (run dans un thread FastAPI).

    Sécurité UX : ne se déclenche que si messages > threshold + 5 (évite de
    bloquer le chat à chaque message au seuil exact) et timeout Ollama limité
    à 10s (pas 45s) pour ne pas bloquer l'utilisateur.
    """
    cfg = load_config()
    mc_cfg = cfg.get("memory_compression", {})
    if not mc_cfg.get("enabled", True):
        return 0

    threshold    = mc_cfg.get("threshold_messages", 30)
    keep_recent  = mc_cfg.get("keep_recent_messages", 10)
    model        = mc_cfg.get("compression_model", "qwen3:14b")
    ollama_url   = mc_cfg.get("ollama_url", "http://localhost:11434")

    if session_id not in _sessions:
        return 0
    msgs = _sessions[session_id].get("messages", [])
    # +5 de marge : évite de bloquer l'utilisateur à chaque message juste au seuil
    if len(msgs) <= threshold + 5:
        return 0

    to_compress = msgs[:-keep_recent]
    to_keep     = msgs[-keep_recent:]

    text = "\n".join(
        f"{'David' if m['role'] == 'user' else 'Jarvis'}: {m['content'][:300]}"
        for m in to_compress
        if m.get("role") in ("user", "assistant")
    )
    if not text.strip():
        return 0

    # Compte seulement les vrais échanges (pas les blocs compressés précédents)
    n_actual = sum(1 for m in to_compress if m.get("role") in ("user", "assistant"))
    prompt = (
        f"Résume ces {n_actual} échanges entre David et Jarvis "
        f"en 5 à 8 points clés.\n"
        f"Préserve: décisions prises, code écrit, problèmes résolus, prochaines étapes.\n"
        f"Format: liste à puces, concis, en français.\n\n{text}"
    )

    import urllib.request as _ur
    payload = json.dumps({
        "model":   model,
        "prompt":  prompt,
        "stream":  False,
        "options": {"temperature": 0.2, "num_predict": 600}
    }).encode()

    try:
        req = _ur.Request(
            f"{ollama_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        # Timeout 10s max — ne pas bloquer l'utilisateur dans le thread chat
        with _ur.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        summary = data.get("response", "").strip()
    except Exception as e:
        print(f"[memory] compress_session_sync: Ollama non disponible ({e})")
        return 0

    if not summary:
        return 0

    n_compressed = len(to_compress)
    compressed_msg = {
        "role":    "system",
        "content": f"[🗜️ MÉMOIRE COMPRESSÉE — {n_compressed} messages]\n{summary}"
    }
    _sessions[session_id]["messages"] = [compressed_msg] + to_keep
    _save_sessions()
    print(f"[memory] Session '{session_id}': {n_compressed} messages compressés via {model}")
    return n_compressed


# ── Facts persistants ───────────────────────────────────
def load_facts() -> dict:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "user_name": "David",
        "projects":    [],
        "preferences": [],
        "notes":       [],
        "updated_at":  None
    }


def save_facts(facts: dict) -> None:
    facts["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    MEMORY_FILE.write_text(
        json.dumps(facts, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ── Construction du prompt système ──────────────────────
def build_system_prompt(base: str, facts: dict) -> str:
    cfg    = load_config()
    jarvis = cfg.get("jarvis", {})

    personality    = jarvis.get("personality", base)
    response_style = jarvis.get("response_style", "")
    expertise      = jarvis.get("expertise", [])
    rules          = jarvis.get("rules", [])
    language       = jarvis.get("language", "Français")

    style_block = (
        f"\n\nRESPONSE STYLE: {response_style}"
        if response_style else ""
    )
    lang_block = f"\n\nLANGUAGE: Always respond in {language}. Understand any input language but reply in {language} only."

    expertise_block = ""
    if expertise:
        expertise_block = (
            "\n\nEXPERTISE:\n"
            + "\n".join(f"  - {e}" for e in expertise)
        )

    rules_block = ""
    if rules:
        rules_block = (
            "\n\nABSOLUTE RULES:\n"
            + "\n".join(f"  - {r}" for r in rules)
        )

    # Memory block
    lines = []
    if facts.get("user_name"):
        lines.append(f"Name: {facts['user_name']}")
    if facts.get("full_name"):
        lines.append(f"Full name: {facts['full_name']}")
    if facts.get("location"):
        lines.append(f"Location: {facts['location']}")
    if facts.get("projects"):
        lines.append("Active projects:")
        for p in facts["projects"]:
            lines.append(f"    • {p}")
    if facts.get("tech_stack"):
        lines.append(
            f"Tech stack: {', '.join(facts['tech_stack'][:8])}"
        )
    if facts.get("preferences"):
        lines.append("Preferences:")
        for p in facts["preferences"]:
            lines.append(f"    • {p}")
    if facts.get("goals"):
        lines.append("David's goals:")
        for g in facts["goals"]:
            lines.append(f"    • {g}")
    if facts.get("session_plan", {}).get("completed"):
        lines.append("Already completed:")
        for c in facts["session_plan"]["completed"]:
            lines.append(f"    ✅ {c}")
    if facts.get("session_plan", {}).get("next_steps"):
        lines.append("Planned next steps:")
        for s in facts["session_plan"]["next_steps"]:
            lines.append(f"    ⏳ {s}")
    if facts.get("notes"):
        lines.append("Important notes:")
        for n in facts["notes"]:
            lines.append(f"    📌 {n}")

    memory_block = ""
    if lines:
        memory_block = (
            "\n\n━━━ PERSISTENT MEMORY ━━━\n"
            + "\n".join(lines)
            + "\n━━━ END MEMORY ━━━\n"
            + "\n⚠️ These facts persist across restarts. "
            "Use them with confidence. "
            "Never tell David you don't remember."
        )

    # Vault Obsidian memory block (00_Core + note du jour)
    vault_block = load_vault_memory()

    # Language rule is prepended first so it's never overridden — driven by config.json
    _lang = language.lower()
    if "english" in _lang or "anglais" in _lang:
        lang_first = "CRITICAL: You ALWAYS respond in English only. David may write or speak in French — understand it fully but ALWAYS reply in English.\n\n"
    else:
        lang_first = f"CRITIQUE : Tu réponds TOUJOURS en {language} uniquement. David peut écrire ou parler en n'importe quelle langue — comprends-le parfaitement mais réponds TOUJOURS en {language}.\n\n"
    return (
        lang_first + personality + lang_block + style_block
        + expertise_block + rules_block + memory_block + vault_block
    )

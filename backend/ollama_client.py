"""
Client Ollama — modèles IA locaux gratuits
Tourne sur ton PC, zéro coût, zéro internet requis.
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv(override=True)

OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://127.0.0.1:11434")  # 127.0.0.1 force IPv4 — évite ::1 sur Windows
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:14b")


def is_ollama_available() -> bool:
    """Vérifie si Ollama tourne sur ce PC."""
    try:
        r = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def list_local_models() -> list[str]:
    """Liste les modèles téléchargés sur ce PC."""
    try:
        r = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def ask_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    """
    Envoie une question à Ollama (modèle local).
    Retourne la réponse ou None si Ollama n'est pas disponible.
    """
    try:
        r = httpx.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model":  model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1024,
                }
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json().get("response", "")
    except httpx.TimeoutException:
        print("[ollama] timeout — bascule sur Claude")
        return None
    except Exception as e:
        print(f"[ollama] erreur: {e} — bascule sur Claude")
        return None


def ask_ollama_chat(messages: list[dict], model: str = OLLAMA_MODEL) -> str:
    """
    Envoie une conversation complète à Ollama (format messages).
    """
    try:
        r = httpx.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model":    model,
                "messages": messages,
                "stream":   False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1024,
                }
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")
    except httpx.TimeoutException:
        print("[ollama] timeout — bascule sur Claude")
        return None
    except Exception as e:
        print(f"[ollama] erreur: {e} — bascule sur Claude")
        return None


# Mots-clés qui déclenchent Claude (questions complexes)
CLAUDE_KEYWORDS = [
    "architecture", "conçois", "planifie", "analyse", "explique pourquoi",
    "stratégie", "compare", "débogue", "refactor", "optimise",
    "multi-agent", "design pattern", "revue de code", "!claude",
]

# Mots-clés pour forcer Ollama
OLLAMA_KEYWORDS = ["!local", "!ollama", "!gratuit"]


def should_use_claude(message: str) -> bool:
    """
    Décide si la question mérite Claude (payant) ou Ollama (gratuit).
    Règle : local-first — Ollama par défaut sauf si complexe.
    """
    msg_lower = message.lower()

    # Force Claude
    if any(k in msg_lower for k in CLAUDE_KEYWORDS):
        return True

    # Force Ollama
    if any(k in msg_lower for k in OLLAMA_KEYWORDS):
        return False

    # Par défaut : Ollama (gratuit)
    return False
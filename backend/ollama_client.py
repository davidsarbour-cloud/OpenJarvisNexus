"""
Client Ollama — modèles IA locaux gratuits
Tourne sur ton PC, zéro coût, zéro internet requis.
"""

import json
import re
import httpx
from typing import Generator

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_NUM_CTX

# ── Think-tag filter (qwen3:14b / deepseek-r1 reasoning blocks) ─────────────
_THINK_RE = re.compile(r'<think>.*?</think>', re.DOTALL)


def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from qwen3/deepseek-r1 output."""
    return _THINK_RE.sub('', text).strip()


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
                    "num_ctx": OLLAMA_NUM_CTX,
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
                    "num_ctx": OLLAMA_NUM_CTX,
                }
            },
            timeout=120,  # qwen3:14b can take up to 2 min on first load
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
    "crée une skill", "installe skill", "utilise le skill", "skill arxiv",
    "skill github", "skill plan", "skill debug",
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


def stream_ollama_chat(
    messages: list[dict],
    model: str = OLLAMA_MODEL,
) -> Generator[str, None, None]:
    """
    Real token-by-token streaming from Ollama.

    Yields visible text fragments as they arrive from the model —
    no full-response wait. Filters out <think>...</think> reasoning
    blocks from qwen3:14b and deepseek-r1 so they never reach the UI.

    Usage::
        for chunk in stream_ollama_chat(msgs, model):
            yield chunk   # already clean text
    """
    buffer   = ""
    in_think = False

    try:
        with httpx.stream(
            "POST",
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model":    model,
                "messages": messages,
                "stream":   True,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1024,
                    "num_ctx":     OLLAMA_NUM_CTX,
                },
            },
            timeout=httpx.Timeout(10.0, read=120.0),
        ) as response:
            response.raise_for_status()

            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                try:
                    chunk = json.loads(raw_line)
                except Exception:
                    continue

                content = chunk.get("message", {}).get("content", "")
                if content:
                    buffer += content

                    # State-machine: strip <think>...</think> blocks spanning chunks
                    while True:
                        if in_think:
                            end = buffer.find("</think>")
                            if end == -1:
                                # Still inside think — keep last 8 chars in case tag spans next chunk
                                buffer = buffer[-8:] if len(buffer) > 8 else buffer
                                break
                            # Found end of think block — discard it
                            buffer   = buffer[end + 8:]
                            in_think = False
                        else:
                            start = buffer.find("<think>")
                            if start == -1:
                                # No think block starting — safe to yield all but last 7 chars
                                safe   = buffer[:-7] if len(buffer) > 7 else ""
                                buffer = buffer[-7:] if len(buffer) > 7 else buffer
                                if safe:
                                    yield safe
                                break
                            # Found start of think block — yield visible text before it
                            if start > 0:
                                yield buffer[:start]
                            buffer   = buffer[start + 7:]
                            in_think = True

                if chunk.get("done"):
                    break

        # Flush remaining visible buffer
        if not in_think and buffer:
            yield buffer

    except httpx.TimeoutException:
        print("[ollama] stream_ollama_chat — timeout après 120s")
    except Exception as exc:
        print(f"[ollama] stream_ollama_chat — erreur: {exc}")
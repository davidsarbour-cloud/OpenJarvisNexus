"""
Bridge vers DeepSeek Coder via Ollama.
Génère : scripts Blender bpy, code OpenSCAD, logique géométrique, scripts de réparation.
"""
from __future__ import annotations
import os
import re
import httpx

OLLAMA_HOST   = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
CODER_MODEL   = os.getenv("OLLAMA_CODER_MODEL", "deepseek-coder:6.7b")
TIMEOUT_S     = 180

_FORGE_SYSTEM = """You are CORTANA, a specialized code generation engine for The Forge Room.
You generate ONLY executable code — no explanations, no prose, no markdown outside code blocks.
Supported outputs: Python (Blender bpy), OpenSCAD, Python (trimesh/numpy geometry).
All geometry must be FDM-printable: manifold, watertight, no overhangs >45°, wall >=1.2mm.
Output ONLY the code block, nothing else."""


def _extract_code(text: str, lang: str = "") -> str:
    """Extrait le premier bloc de code de la réponse."""
    patterns = [
        rf"```{lang}\n?([\s\S]+?)```",
        r"```\n?([\s\S]+?)```",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return text.strip()


async def generate_code_async(
    prompt: str,
    lang: str = "python",
    system: str = _FORGE_SYSTEM,
    temperature: float = 0.2,
    max_tokens: int = 3000,
) -> str | None:
    """Appel asynchrone à DeepSeek Coder via Ollama /api/chat."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ]
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model":    CODER_MODEL,
                    "messages": messages,
                    "stream":   False,
                    "options":  {"temperature": temperature, "num_predict": max_tokens},
                },
                timeout=TIMEOUT_S,
            )
            r.raise_for_status()
            content = r.json().get("message", {}).get("content", "")
            if content:
                return _extract_code(content, lang)
    except httpx.TimeoutException:
        print(f"[deepseek] timeout ({TIMEOUT_S}s)")
    except Exception as e:
        print(f"[deepseek] erreur: {e}")
    return None


def generate_code_sync(
    prompt: str,
    lang: str = "python",
    system: str = _FORGE_SYSTEM,
    temperature: float = 0.2,
    max_tokens: int = 3000,
) -> str | None:
    """Appel synchrone à DeepSeek Coder."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ]
    try:
        r = httpx.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model":    CODER_MODEL,
                "messages": messages,
                "stream":   False,
                "options":  {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=TIMEOUT_S,
        )
        r.raise_for_status()
        content = r.json().get("message", {}).get("content", "")
        return _extract_code(content, lang) if content else None
    except Exception as e:
        print(f"[deepseek] erreur sync: {e}")
        return None


def is_available() -> bool:
    """Vérifie que DeepSeek Coder est disponible dans Ollama."""
    try:
        r = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        return any(CODER_MODEL.split(":")[0] in m for m in models)
    except Exception:
        return False

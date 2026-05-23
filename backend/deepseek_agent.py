"""
NOVA — Agent de raisonnement DeepSeek-R1:7B
Modèle local via Ollama, spécialisé reasoning + code complexe.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

from config import OLLAMA_HOST
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-r1:7b")


def ask_nova(prompt: str, system: str = None, temperature: float = 0.2) -> str:
    """
    Envoie un prompt à NOVA (deepseek-r1:7b) via Ollama.
    R1 génère un bloc <think>...</think> avant la réponse finale.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        r = httpx.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model":    DEEPSEEK_MODEL,
                "messages": messages,
                "stream":   False,
                "options": {
                    "temperature":  temperature,
                    "num_predict":  2048,
                }
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")
    except httpx.TimeoutException:
        return "[NOVA] timeout — tâche trop longue"
    except Exception as e:
        return f"[NOVA] erreur: {e}"


def nova_code(task: str, context: str = "") -> str:
    """Génération de code spécialisée NOVA (reasoning activé)."""
    system = (
        "Tu es NOVA, un expert en code Python, FastAPI, TypeScript et automatisation. "
        "Tu raisonnes étape par étape avant d'écrire du code. "
        "Tu produis toujours du code complet, commenté en français, prêt à l'emploi. "
        "Stack Nexus9 : Python 3.11, FastAPI, React 19, Docker, Ollama."
    )
    full_prompt = f"{task}\n\nContexte additionnel:\n{context}" if context else task
    return ask_nova(full_prompt, system=system, temperature=0.1)


def nova_analyze(code: str, question: str = "Analyse ce code et propose des améliorations.") -> str:
    """Analyse de code par NOVA avec chain-of-thought."""
    system = (
        "Tu es NOVA, expert en revue de code. "
        "Tu identifies les bugs, failles de sécurité, et optimisations possibles. "
        "Tu expliques chaque problème et proposes une correction concrète."
    )
    prompt = f"{question}\n\n```python\n{code}\n```"
    return ask_nova(prompt, system=system, temperature=0.3)


def nova_pipeline(steps: list[str]) -> list[dict]:
    """
    Exécute un pipeline multi-étapes avec NOVA.
    Chaque étape est envoyée séquentiellement, le résultat alimente la suivante.
    """
    results = []
    context = ""
    for i, step in enumerate(steps):
        prompt = f"Étape {i+1}: {step}"
        if context:
            prompt += f"\n\nRésultat étape précédente:\n{context}"
        response = ask_nova(prompt)
        context = response
        results.append({"step": i + 1, "task": step, "result": response})
    return results

# backend/core/claude_client.py — VERSION CORRIGÉE
import os

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

class ClaudeOrchestrator:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or not api_key.startswith("sk-ant-"):
            raise ValueError(
                "❌ ANTHROPIC_API_KEY invalide!\n"
                "→ Obtenez votre clé sur: https://console.anthropic.com/\n"
                "→ Ajoutez-la dans le fichier .env"
            )
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-opus-4-5"
        print(f"✅ Claude connecté: {self.model}")

    async def orchestrate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2048
    ) -> str:
        """Orchestration principale via Claude"""
        system_prompt = """Tu es JARVIS, l'orchestrateur central du système NexusX9.
        Tu coordonnes 5 agents IA spécialisés:
        - Architecte: conception et planification système
        - Laboratoire: expérimentation et recherche
        - Surveillance: monitoring et sécurité
        - AtelierCode: développement et debugging
        - CoffreMémoire: stockage et récupération de connaissances

        Réponds de manière concise, structurée et en français.
        Identifie toujours quel agent est le plus approprié pour chaque tâche."""

        messages = []
        if context:
            messages.append({
                "role": "user",
                "content": f"Contexte précédent:\n{context}"
            })
            messages.append({
                "role": "assistant",
                "content": "Contexte chargé. Prêt pour la prochaine instruction."
            })

        messages.append({"role": "user", "content": prompt})

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text

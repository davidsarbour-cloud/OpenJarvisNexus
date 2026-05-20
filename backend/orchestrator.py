"""
JARVIS Orchestration Engine — classify intent, query Vault, route to agents.
Transforme JARVIS d'un chatbot en système d'orchestration.
"""
from __future__ import annotations
import asyncio
import re
import os
from datetime import datetime
from typing import Any

BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))

# ── Intent Classification ─────────────────────────────────

INTENT_PATTERNS = {
    "fabrication": [
        r"\b(stl|fdm|3d.?print|imprim|figur|dragon|chien|chat|éléphant|low.?poly|meshy|bambu|slicer|mesh|manifold)\b",
        r"\b(crée|génère|fais|make|generate|fabrique)\b.{0,40}\b(3d|stl|model|figur)\b",
    ],
    "coding": [
        r"\b(code|script|programme|fonction|debug|refactor|python|fastapi|api|endpoint|class|module)\b",
        r"\b(écri[st]|génère|crée).{0,30}\b(fonction|script|code|programme)\b",
    ],
    "execution": [
        r"\b(installe|execute|run|lance|déploie|configure|setup|terminal|commande)\b",
        r"\b(bruce|openhands|autonome|filesystem|fichier)\b",
    ],
    "memory": [
        r"\b(souviens|remember|vault|mémoire|historique|précédent|history|recall)\b",
        r"\b(sauvegarde|archive|stocke|mémorise)\b",
    ],
    "reasoning": [
        r"\b(analyse|planifie|stratégie|architecture|design|pense|réfléchi[st]|décide)\b",
        r"\b(ultron|complexe|stratégique|difficile)\b",
    ],
}

AGENT_MAP = {
    "fabrication": {
        "agents": ["FORGE", "CORTANA", "GWEN"],
        "providers": ["Meshy AI", "DeepSeek Coder 6.7b", "Qwen3:14b"],
        "plan": [
            "Vault: chercher missions similaires",
            "CORTANA: préparer pipeline géométrique",
            "FORGE: générer STL via Meshy AI",
            "GWEN: optimiser paramètres FDM",
            "Validation + export Bambu Studio",
        ],
    },
    "coding": {
        "agents": ["CORTANA"],
        "providers": ["DeepSeek Coder 6.7b"],
        "plan": [
            "Vault: charger contexte code existant",
            "CORTANA: générer le code",
            "Validation syntaxique",
            "Save résultat dans Vault",
        ],
    },
    "execution": {
        "agents": ["BRUCE"],
        "providers": ["OpenHands + Qwen3:14b"],
        "plan": [
            "BRUCE: préparer environnement",
            "Exécution autonome",
            "Vérification résultat",
            "Log dans Vault",
        ],
    },
    "memory": {
        "agents": ["GWEN"],
        "providers": ["Qwen3:14b local"],
        "plan": [
            "Vault: recherche sémantique",
            "GWEN: analyse et synthèse",
            "Retour mémoires pertinentes",
        ],
    },
    "reasoning": {
        "agents": ["ULTRON"],
        "providers": ["Claude Sonnet 4.6"],
        "plan": [
            "Vault: charger contexte projet",
            "ULTRON: analyse profonde",
            "Synthèse et recommandations",
            "Save insights dans Vault",
        ],
    },
    "conversation": {
        "agents": ["JARVIS"],
        "providers": ["Claude Haiku 4.5"],
        "plan": [
            "Vault: contexte conversation",
            "JARVIS: réponse orchestrée",
            "Save échange dans Vault",
        ],
    },
}


def classify_intent(text: str) -> dict:
    """Classifie l'intention de l'utilisateur. Retourne intent + confiance."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, text_lower, re.IGNORECASE))
        if score > 0:
            scores[intent] = score
    if not scores:
        return {"intent": "conversation", "confidence": 1.0, "signals": []}
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    signals = [k for k, v in scores.items() if v > 0]
    return {"intent": best, "confidence": round(scores[best] / max(total, 1), 2), "signals": signals}


async def query_vault_for_context(text: str, intent: str) -> list[dict]:
    """Requête Vault pour le contexte pertinent."""
    try:
        from vault.memory_manager import vault_query
        collections = {
            "fabrication": ["forge_reports", "workflows"],
            "coding":      ["agent_memory", "workflows"],
            "execution":   ["orchestration", "workflows"],
            "memory":      None,  # all
            "reasoning":   ["architecture", "workflows"],
            "conversation": ["conversations"],
        }.get(intent)
        memories = await vault_query(text, collections=collections)
        return memories[:4]
    except Exception:
        return []


class OrchestrationResult:
    def __init__(self, text: str):
        self.text      = text
        self.intent    = ""
        self.agents:   list[str] = []
        self.providers: list[str] = []
        self.plan:     list[str] = []
        self.memories: list[dict] = []
        self.result    = ""
        self.execution_id = f"orch_{datetime.now():%Y%m%d%H%M%S}"
        self.duration_ms  = 0
        self.success      = True
        self.error        = None

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "intent":      self.intent,
            "agents":      self.agents,
            "providers":   self.providers,
            "plan":        self.plan,
            "memories":    [{"text": m["text"][:100], "score": m.get("score", 0), "collection": m.get("collection")} for m in self.memories],
            "result":      self.result,
            "success":     self.success,
            "error":       self.error,
            "duration_ms": self.duration_ms,
        }


async def orchestrate(text: str, model: str = "claude-haiku-4-5") -> OrchestrationResult:
    """Pipeline d'orchestration complet pour une requête utilisateur."""
    t0 = datetime.now()
    orch = OrchestrationResult(text)

    # 1. Classification
    classification = classify_intent(text)
    intent = classification["intent"]
    agent_config = AGENT_MAP.get(intent, AGENT_MAP["conversation"])

    orch.intent    = intent
    orch.agents    = agent_config["agents"]
    orch.providers = agent_config["providers"]
    orch.plan      = agent_config["plan"]

    # 2. Vault memory retrieval
    orch.memories = await query_vault_for_context(text, intent)

    # 2b. Jarvis file context — cherche dans les fichiers OneDrive de David
    jarvis_file_context = ""
    try:
        from jarvis_files import search_jarvis_files, read_jarvis_file, list_jarvis_dir
        file_hits = search_jarvis_files(text, max_results=3)
        if file_hits:
            jarvis_file_context = "\n\n[Jarvis Workspace Files]\n" + "\n".join(
                f"• [{h['file']}] {h['excerpt'][:120]}"
                for h in file_hits
            )
            # Ajoute les fichiers trouvés aux mémoires pour l'UI
            for h in file_hits:
                orch.memories.append({
                    "text": h["excerpt"],
                    "score": 0.8,
                    "collection": f"file:{h['file']}",
                })
    except Exception:
        pass

    # 3. Build enriched context
    vault_context = ""
    if orch.memories:
        vault_context = "\n\n[Vault Memory Retrieved]\n" + "\n".join(
            f"• [{m.get('collection','?')}] {m['text'][:120]}"
            for m in orch.memories
        )
    if jarvis_file_context:
        vault_context += jarvis_file_context

    # 4. Log orchestration decision
    try:
        from vault.memory_manager import add_memory
        await add_memory("orchestration",
            f"Intent: {intent} | Agents: {orch.agents} | Query: {text[:100]}",
            metadata={"intent": intent, "agents": str(orch.agents), "execution_id": orch.execution_id}
        )
    except Exception:
        pass

    orch.duration_ms = int((datetime.now() - t0).total_seconds() * 1000)
    return orch

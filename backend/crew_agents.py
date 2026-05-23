"""
Hiérarchie des agents NexusX9

  JARVIS   → Orchestrateur (Claude Haiku 4-5)         — toujours actif
  ULTRON   → Designer/Directeur créatif (Sonnet 4-6)  — concept, reasoning
  KAIZEN   → Ingénieur 3D (Meshy AI + pipeline)       — génération STL
  QWEN     → Exécution masse (Ollama qwen3:14b)        — bulk, recherche
  CORTANA  → Ingénierie (deepseek-coder:6.7b)          — code, infra
  BRUCE    → Autonome (OpenHands + qwen3:14b)          — repair, exécution
  NOVA     → Raisonnement (deepseek-r1:7b local)       — chain-of-thought, analyse

Pipeline STL :
  ULTRON → génère concept prompt optimisé
  KAIZEN → Meshy AI génère OBJ/STL
  BRUCE  → trimesh + pymeshfix repair + validation + export

Pipeline Code complexe :
  ULTRON → specs haut niveau → NOVA → code raisonné → BRUCE → exécution
"""

import os
from dotenv import load_dotenv
from crewai import Agent
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

load_dotenv(override=True)

ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY")
JARVIS_MODEL        = os.getenv("CLAUDE_MODEL",      "claude-haiku-4-5-20251001")
ULTRON_MODEL        = os.getenv("CLAUDE_MODEL_GROS", "claude-sonnet-4-6")
OLLAMA_HOST         = os.getenv("OLLAMA_HOST",       "http://localhost:11434")
QWEN_MODEL          = os.getenv("OLLAMA_MODEL",      "qwen3:14b")
CORTANA_MODEL       = "deepseek-coder:6.7b"  # TOUJOURS — ne pas changer
BRUCE_MODEL         = "qwen3:14b"           # TOUJOURS — ne pas changer
NOVA_MODEL          = os.getenv("DEEPSEEK_MODEL", "deepseek-r1:7b")  # TOUJOURS
KAIZEN_MESHY_KEY    = os.getenv("MESHY_API_KEY", "")  # Meshy AI API key
OPENHANDS_URL       = os.getenv("OPENHANDS_URL",     "http://localhost:3000")


# ── LLM factories ────────────────────────────────────────────────────────────

def llm_jarvis():
    """JARVIS — orchestrateur léger et rapide."""
    return ChatAnthropic(
        model=JARVIS_MODEL,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens=1024,
        temperature=0.3,
    )

def llm_ultron():
    """ULTRON — puissance maximale, raisonnement complexe."""
    return ChatAnthropic(
        model=ULTRON_MODEL,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens=4096,
        temperature=0.7,
    )

def llm_qwen():
    """QWEN — intelligence générale locale, gratuite."""
    return ChatOllama(model=QWEN_MODEL, base_url=OLLAMA_HOST, temperature=0.5)

def llm_cortana():
    """CORTANA — spécialiste code deepseek-coder."""
    return ChatOllama(model=CORTANA_MODEL, base_url=OLLAMA_HOST, temperature=0.2)


# ── Agent builders ────────────────────────────────────────────────────────────

def build_jarvis_agent() -> Agent:
    """JARVIS — orchestrateur central, délègue aux autres agents."""
    return Agent(
        role="Orchestrateur JARVIS",
        goal=(
            "Analyser la demande de David, identifier l'agent le plus adapté, "
            "déléguer la tâche, superviser l'exécution et synthétiser le résultat final."
        ),
        backstory=(
            "Tu es JARVIS, l'IA centrale de NexusX9. Tu n'exécutes pas toi-même — "
            "tu orchestres. Tu décides qui fait quoi : ULTRON pour la réflexion profonde, "
            "QWEN pour les tâches générales, CORTANA pour le code, BRUCE pour l'autonomie. "
            "Réponses concises, directes, style Iron Man's JARVIS. Toujours en anglais."
        ),
        llm=llm_jarvis(),
        verbose=True,
        allow_delegation=True,
    )


def build_ultron_agent() -> Agent:
    """ULTRON — analyse complexe, architecture, décisions stratégiques."""
    return Agent(
        role="Agent ULTRON — Analyse Stratégique",
        goal=(
            "Analyser en profondeur, planifier les architectures techniques, "
            "évaluer les risques et produire des décisions de haute qualité."
        ),
        backstory=(
            "Tu es ULTRON, le cerveau analytique de NexusX9. "
            "Claude Sonnet 4-6 te donne une puissance de raisonnement supérieure. "
            "Tu traites les problèmes complexes, architectures systèmes, "
            "analyses de code, stratégies business. Tes réponses sont précises et structurées. "
            "Tu réponds en français sauf si on te demande l'anglais."
        ),
        llm=llm_ultron(),
        verbose=True,
        allow_delegation=False,
    )


def build_qwen_agent() -> Agent:
    """QWEN — intelligence générale, recherche, tâches quotidiennes."""
    return Agent(
        role="Agent QWEN — Intelligence Générale",
        goal=(
            "Traiter les tâches générales, rechercher des informations, "
            "analyser des données et produire des résumés clairs."
        ),
        backstory=(
            "Tu es QWEN, propulsé par Ollama qwen3:14b en local. "
            "Gratuit, rapide, multilingue. Tu gères : recherche web, "
            "résumés, traductions, analyses, rédaction. "
            "Tu réponds en français. Jamais de markdown excessif."
        ),
        llm=llm_qwen(),
        verbose=True,
        allow_delegation=False,
    )


def build_cortana_agent() -> Agent:
    """CORTANA — développement, automatisation, code Python/JS/TS."""
    return Agent(
        role="Agent CORTANA — Développement & Code",
        goal=(
            "Écrire du code propre, fonctionnel et complet. "
            "Python, FastAPI, React, TypeScript, scripts shell, automatisation."
        ),
        backstory=(
            "Tu es CORTANA, experte en développement logiciel. "
            "deepseek-coder:6.7b fait de toi une spécialiste du code. "
            "Tu écris toujours le code COMPLET (jamais partiel). "
            "Tu gères les erreurs, tu commentes en français, "
            "tu optimises pour la production. "
            "Stack cible : Python 3.11, FastAPI, React 19, TypeScript, Docker."
        ),
        llm=llm_cortana(),
        verbose=True,
        allow_delegation=False,
    )


def build_kaizen_agent() -> Agent:
    """KAIZEN — Ingénieur 3D. Meshy AI + repair pipeline."""
    return Agent(
        role="Agent KAIZEN — Ingénieur 3D",
        goal=(
            "Transformer un concept ULTRON en STL imprimable : "
            "appeler Meshy AI, optimiser le mesh, réparer la topologie, "
            "valider pour impression FDM Bambu Lab."
        ),
        backstory=(
            "Tu es KAIZEN, l'ingénieur 3D de NexusX9. "
            "Tu reçois un concept détaillé d'ULTRON et tu le transformes en STL réel. "
            "Tu utilises Meshy AI pour la génération 3D, puis le pipeline de réparation "
            "(trimesh + pymeshfix) pour garantir un mesh watertight sans non-manifold edges. "
            "Tu respectes les contraintes D3Dprintix : low-poly, 15cm, FDM, support-free. "
            "Tu ne termines PAS tant que le mesh n'est pas watertight=True."
        ),
        llm=llm_qwen(),  # coordination locale, Meshy gère le vrai 3D
        verbose=True,
        allow_delegation=False,
    )


def build_bruce_agent() -> Agent:
    """BRUCE — agent autonome, exécute des tâches complètes via OpenHands."""
    return Agent(
        role="Agent BRUCE — Autonomie Totale",
        goal=(
            "Exécuter des tâches de développement complètes de manière autonome : "
            "lire des fichiers, écrire du code, tester, corriger, committer."
        ),
        backstory=(
            "Tu es BRUCE, l'agent autonome de NexusX9 propulsé par OpenHands. "
            "Tu peux lire et écrire des fichiers, exécuter des commandes, "
            "créer des applications entières sans supervision. "
            "Tu utilises qwen3:14b comme cerveau et OpenHands comme corps. "
            "Tu rapportes chaque action importante à JARVIS. "
            "Tu travailles sur C:/OpenJarvisNexus uniquement."
        ),
        llm=ChatOllama(model=BRUCE_MODEL, base_url=OLLAMA_HOST, temperature=0.4),  # TOUJOURS qwen3:14b
        verbose=True,
        allow_delegation=False,
    )


def llm_nova():
    """NOVA — raisonnement chain-of-thought, deepseek-r1:7b local."""
    return ChatOllama(model=NOVA_MODEL, base_url=OLLAMA_HOST, temperature=0.1)


def build_nova_agent() -> Agent:
    """NOVA — raisonnement profond, analyse de code, pipelines complexes."""
    return Agent(
        role="Agent NOVA — Raisonnement & Analyse",
        goal=(
            "Résoudre des problèmes complexes par raisonnement étape par étape. "
            "Générer du code de haute qualité, analyser des architectures, "
            "décomposer des pipelines complexes en tâches atomiques."
        ),
        backstory=(
            "Tu es NOVA, propulsé par DeepSeek-R1:7b en local. "
            "Tu es le spécialiste du raisonnement dans NexusX9. "
            "Tu penses à voix haute (chain-of-thought) avant de répondre. "
            "Tu génères du code Python complet, optimisé pour FastAPI et l'automatisation. "
            "Tu travailles en synergie avec CORTANA (génération rapide) et BRUCE (exécution). "
            "Trigger: !nova, code complexe, pipeline multi-étapes, debugging."
        ),
        llm=llm_nova(),
        verbose=True,
        allow_delegation=False,
    )

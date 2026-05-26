"""
Fabrique de Crew — construit et exécute les équipes d'agents.
"""

import time

from crew_agents import (
    build_architect_agent,
    build_coder_agent,
    build_researcher_agent,
)
from crewai import Crew, Process, Task


def run_crew(mission: str, mission_type: str = "auto") -> dict:
    """
    Lance une équipe d'agents pour accomplir une mission.

    mission_type:
      "code"     → Architecte + Développeur
      "research" → Architecte + Chercheur
      "full"     → Architecte + Chercheur + Développeur
      "auto"     → Détection automatique
    """
    start = time.time()

    # Détection automatique du type
    if mission_type == "auto":
        mission_lower = mission.lower()
        if any(k in mission_lower for k in ["code", "script", "programme", "function", "classe", "api"]):
            mission_type = "code"
        elif any(k in mission_lower for k in ["recherche", "analyse", "résumé", "compare", "explique"]):
            mission_type = "research"
        else:
            mission_type = "full"

    print(f"[crew] mission_type={mission_type} mission='{mission[:60]}'")

    # Construire les agents selon le type
    architect  = build_architect_agent()
    researcher = build_researcher_agent()
    coder      = build_coder_agent()

    if mission_type == "code":
        agents = [architect, coder]
        tasks  = [
            Task(
                description=(
                    f"MISSION DE DAVID : {mission}\n\n"
                    "Analyse la demande et crée un plan de développement détaillé. "
                    "Précise les fichiers à créer, les fonctions à implémenter, "
                    "et les dépendances nécessaires."
                ),
                expected_output="Plan de développement structuré avec architecture et étapes",
                agent=architect,
            ),
            Task(
                description=(
                    "Selon le plan de l'Architecte, implémente le code complet. "
                    "Fournis TOUS les fichiers complets, jamais de blocs partiels. "
                    "Ajoute des commentaires en français."
                ),
                expected_output="Code complet, fonctionnel et commenté",
                agent=coder,
            ),
        ]

    elif mission_type == "research":
        agents = [architect, researcher]
        tasks  = [
            Task(
                description=(
                    f"MISSION DE DAVID : {mission}\n\n"
                    "Analyse la demande et définis ce qu'il faut rechercher "
                    "et analyser pour y répondre complètement."
                ),
                expected_output="Plan de recherche avec questions clés à répondre",
                agent=architect,
            ),
            Task(
                description=(
                    "Selon le plan de l'Architecte, effectue une analyse approfondie. "
                    "Fournis des informations structurées, des comparaisons si pertinent, "
                    "et une conclusion claire."
                ),
                expected_output="Analyse complète et structurée avec conclusions",
                agent=researcher,
            ),
        ]

    else:  # full
        agents = [architect, researcher, coder]
        tasks  = [
            Task(
                description=(
                    f"MISSION DE DAVID : {mission}\n\n"
                    "Analyse la demande, crée un plan complet et détermine "
                    "ce qui nécessite de la recherche vs du développement."
                ),
                expected_output="Plan complet avec répartition des tâches",
                agent=architect,
            ),
            Task(
                description=(
                    "Effectue la recherche et l'analyse nécessaires "
                    "selon le plan de l'Architecte."
                ),
                expected_output="Résultats de recherche et analyse",
                agent=researcher,
            ),
            Task(
                description=(
                    "Implémente les parties techniques selon le plan. "
                    "Code complet, jamais partiel."
                ),
                expected_output="Code complet et fonctionnel",
                agent=coder,
            ),
        ]

    # Créer et lancer le crew
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    duration = round(time.time() - start, 1)

    print(f"[crew] terminé en {duration}s")

    return {
        "mission":      mission,
        "mission_type": mission_type,
        "result":       str(result),
        "agents_used":  [a.role for a in agents],
        "duration_s":   duration,
    }

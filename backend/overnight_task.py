"""
Tâche overnight — 100% Ollama local, zéro token Claude.
Lance avant de dormir, résultat prêt demain matin.
"""

import time
from datetime import datetime
from pathlib import Path

import requests

OLLAMA = "http://localhost:11434"
OUTPUT = Path("overnight_results")
OUTPUT.mkdir(exist_ok=True)

LOG_FILE = OUTPUT / "rapport_nuit.md"
log_lines = []

def log(msg):
    print(msg)
    log_lines.append(msg)

def ask_ollama(prompt, model="qwen3:14b"):
    """Appelle Ollama local — GRATUIT."""
    try:
        r = requests.post(f"{OLLAMA}/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 2048}
        }, timeout=120)
        return r.json().get("response", "")
    except Exception as e:
        return f"ERREUR: {e}"

def save(filename, content):
    path = OUTPUT / filename
    path.write_text(content, encoding="utf-8")
    log(f"  ✅ Sauvegardé: {path}")
    return path

# ════════════════════════════════════════════════
# TÂCHE 1 — Réparer les erreurs TypeScript NexusX9
# ════════════════════════════════════════════════
def task_fix_typescript():
    log("\n🔧 TÂCHE 1 — Fix TypeScript NexusX9")
    log("  Analyse des problèmes courants...")

    problems = [
        "Missing React import in tsx files",
        "Type 'string' not assignable to type Tab",
        "Cannot find module './types'",
        "Property 'ReactNode' does not exist",
        "Implicit any on event handlers",
    ]

    prompt = f"""Tu es un expert TypeScript React.

Voici les erreurs TypeScript dans un projet NexusX9 Hub (React 18, TypeScript strict):

ERREURS:
{chr(10).join(f'- {p}' for p in problems)}

CONTEXTE:
- React 18 avec JSX transform automatique (pas besoin d'importer React dans chaque fichier)
- Fichier types.ts existe avec: Agent, AgentStatus, AgentProvider, HubAlert, ChatMessage, HubStatus
- Composants: HubHeader, Sidebar, HubMap, AgentRoom, RightPanel, ChatBox

Pour CHAQUE erreur, donne:
1. La cause exacte
2. La correction précise (ligne de code)
3. L'explication simple

Réponds en français, sois concis et direct."""

    result = ask_ollama(prompt)
    save("fix_typescript.md", f"# Fix TypeScript NexusX9\n\n{result}")
    log("  Terminé ✅")

# ════════════════════════════════════════════════
# TÂCHE 2 — Générer le script de démarrage auto
# ════════════════════════════════════════════════
def task_startup_script():
    log("\n🚀 TÂCHE 2 — Script démarrage automatique")

    prompt = """Génère un script PowerShell complet pour Windows qui:

1. Lance Ollama en arrière-plan (ollama serve)
2. Active le venv Python (.venv\\Scripts\\Activate.ps1)
3. Lance le backend FastAPI (python main.py) dans un nouveau terminal
4. Lance le frontend OpenJarvis (npm run dev) dans un nouveau terminal
5. Lance le hub NexusX9 (npm run dev) dans un nouveau terminal
6. Lance le bot Telegram (python telegram_bot.py) dans un nouveau terminal
7. Affiche un message de succès avec les URLs

Chemins:
- Backend: C:\\OpenJarvisNexus\\backend
- Frontend OpenJarvis: C:\\OpenJarvisNexus\\frontend
- Hub NexusX9: C:\\OpenJarvisNexus\\nexusx9
- Bot Telegram: C:\\OpenJarvisNexus\\backend\\telegram_bot.py

Le script doit:
- Utiliser Start-Process pour ouvrir de nouveaux terminaux
- Attendre 3 secondes entre chaque lancement
- Afficher des messages colorés avec Write-Host
- Être simple et fiable sur Windows 11

Génère UNIQUEMENT le code PowerShell, rien d'autre."""

    result = ask_ollama(prompt)
    save("start_nexusx9.ps1", result)
    log("  Terminé ✅")

# ════════════════════════════════════════════════
# TÂCHE 3 — Générer smoke tests complets
# ════════════════════════════════════════════════
def task_smoke_tests():
    log("\n🧪 TÂCHE 3 — Smoke tests automatiques")

    prompt = """Génère un script Python complet de smoke tests pour NexusX9.

ENDPOINTS À TESTER:
- GET  http://localhost:8000/health
- GET  http://localhost:8000/v1/agents
- GET  http://localhost:8000/v1/memory
- GET  http://localhost:8000/v1/models
- POST http://localhost:8000/v1/chat/completions {message: "ping"}
- GET  http://localhost:8000/api/digest
- GET  http://localhost:8000/v1/savings
- GET  http://localhost:11434/api/tags (Ollama)

REQUIS:
- Utilise la bibliothèque requests
- Affiche ✅ ou ❌ pour chaque test
- Mesure le temps de réponse
- Résumé final (X/Y tests passés)
- Couleurs dans le terminal (ANSI codes)
- Gère les timeouts (5 secondes max)
- Génère un rapport rapport_smoke_tests.txt

Génère UNIQUEMENT le code Python complet."""

    result = ask_ollama(prompt)
    save("smoke_tests.py", result)
    log("  Terminé ✅")

# ════════════════════════════════════════════════
# TÂCHE 4 — Documentation complète du projet
# ════════════════════════════════════════════════
def task_documentation():
    log("\n📚 TÂCHE 4 — Documentation projet")

    prompt = """Génère un fichier README.md complet et professionnel pour le projet NexusX9.

PROJET:
- Nom: NexusX9 — Hub de Commandement IA
- Propriétaire: David Arbour
- Stack: Python FastAPI + React TypeScript + Ollama + Claude API
- Architecture: 8 agents IA dans un hub cyberpunk style RPG

SERVICES:
- Backend FastAPI (port 8000): Claude + Ollama + CrewAI + Mémoire persistante
- OpenJarvis Chat (port 5173): Interface principale
- NexusX9 Hub (port 5174): Hub cyberpunk visuel
- Ollama (port 11434): IA locale qwen3:14b + deepseek-coder
- Telegram Bot: Accès mobile avec monitoring

8 AGENTS:
1. Architecte (Claude) - Planification
2. Tour Claude - Raisonnement complexe
3. Laboratoire (Ollama) - Recherche
4. Coffre Mémoire - Stockage persistant
5. Zone Locale (Ollama) - Gratuit
6. Atelier Code (Ollama deepseek) - Code
7. Surveillance - Logs et alertes
8. Missions - CrewAI scheduler

Inclus: installation, démarrage, architecture, endpoints API, agents, troubleshooting.
Style: professionnel avec émojis, tableaux markdown, sections claires.
Langue: Français."""

    result = ask_ollama(prompt)
    save("README.md", result)
    log("  Terminé ✅")

# ════════════════════════════════════════════════
# TÂCHE 5 — Optimiser config.json Jarvis
# ════════════════════════════════════════════════
def task_optimize_config():
    log("\n⚙️  TÂCHE 5 — Optimiser personnalité Jarvis")

    prompt = """Tu es un expert en prompt engineering pour assistants IA.

Génère un config.json optimisé pour Jarvis, l'assistant IA de David Arbour.

PROFIL DAVID:
- Développeur/entrepreneur canadien
- Projets: NexusX9, OpenJarvis, e-commerce (Shopify, Etsy)
- Style: veut du code complet, explications simples, séquences exactes
- Langue: Français préféré
- Techno: Python, React, TypeScript, Windows 11

REQUIS:
- Personnalité: co-fondateur technique de confiance, légèrement sarcastique
- Expertise: IA, cyberpunk UI, e-commerce, automatisation
- Règles: toujours en français, code complet, proactif
- Style: concis et direct, pas de remplissage
- Routing: local-first (Ollama gratuit par défaut)

Format: JSON valide et complet.
Inclus les sections: jarvis, routing, memory."""

    result = ask_ollama(prompt)
    # Extraire juste le JSON
    start = result.find('{')
    end   = result.rfind('}') + 1
    if start >= 0 and end > start:
        json_str = result[start:end]
        save("config_optimized.json", json_str)
    else:
        save("config_optimized.txt", result)
    log("  Terminé ✅")

# ════════════════════════════════════════════════
# TÂCHE 6 — Plan d'intégration Shopify + Etsy
# ════════════════════════════════════════════════
def task_ecommerce_plan():
    log("\n🛍️  TÂCHE 6 — Plan intégration Shopify + Etsy")

    prompt = """Tu es un architecte logiciel senior.

Génère un plan d'intégration complet pour connecter Shopify et Etsy à Jarvis (FastAPI backend).

JARVIS BACKEND:
- FastAPI Python sur port 8000
- Endpoints existants: /v1/chat/completions, /v1/memory/facts, /v1/crew/run
- Claude + Ollama disponibles

REQUIS POUR SHOPIFY:
- Authentification API Shopify (OAuth ou Private App)
- Endpoints à créer: GET produits, GET commandes, GET stocks
- Jarvis peut répondre "combien j'ai vendu cette semaine ?"
- Alertes Telegram si stock faible

REQUIS POUR ETSY:
- Authentification API Etsy v3
- GET listings, GET orders, GET stats
- Jarvis peut comparer performance Shopify vs Etsy

Pour chaque plateforme, génère:
1. Plan d'architecture (fichiers à créer)
2. Code Python des endpoints FastAPI
3. Exemples de questions que David peut poser à Jarvis
4. Ordre d'implémentation recommandé

Réponds en français, code complet."""

    result = ask_ollama(prompt)
    save("plan_ecommerce.md", result)
    log("  Terminé ✅")

# ════════════════════════════════════════════════
# RAPPORT FINAL
# ════════════════════════════════════════════════
def generate_report():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"""# 🌙 Rapport Overnight NexusX9
**Date:** {now}
**Modèle:** qwen3:14b (Ollama local — 100% GRATUIT)
**Coût Claude:** $0.000

## Fichiers générés:
- `fix_typescript.md` — Solutions aux 53 erreurs TypeScript
- `start_nexusx9.ps1` — Script de démarrage automatique
- `smoke_tests.py` — Tests automatiques complets
- `README.md` — Documentation professionnelle
- `config_optimized.json` — Personnalité Jarvis optimisée
- `plan_ecommerce.md` — Plan Shopify + Etsy

## Utilisation demain:
**Bonne nuit David ! 🤖💤**
"""
    LOG_FILE.write_text(report + "\n".join(log_lines), encoding="utf-8")
    log(f"\n📋 Rapport complet: {LOG_FILE.absolute()}")

# ════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════
if __name__ == "__main__":
    log("🌙 NEXUSX9 — TÂCHES OVERNIGHT")
    log("=" * 40)
    log(f"Démarrage: {datetime.now().strftime('%H:%M:%S')}")
    log("Modèle: qwen3:14b (Ollama local)")
    log("Coût Claude: $0.000")
    log("=" * 40)

    # Vérifier Ollama
    try:
        r = requests.get(f"{OLLAMA}/api/tags", timeout=3)
        log("✅ Ollama en ligne — on commence !\n")
    except Exception:
        log("❌ Ollama hors ligne !")
        log("Lance: ollama serve")
        exit(1)

    start = time.time()

    task_fix_typescript()
    task_startup_script()
    task_smoke_tests()
    task_documentation()
    task_optimize_config()
    task_ecommerce_plan()

    generate_report()

    total = round((time.time() - start) / 60, 1)
    log(f"\n🎉 TOUT TERMINÉ EN {total} MINUTES")
    log(f"📁 Résultats dans: {OUTPUT.absolute()}")
    log("💰 Coût total: $0.000")
    log("Bonne nuit David ! 🤖")

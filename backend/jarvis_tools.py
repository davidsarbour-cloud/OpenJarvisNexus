"""
Outils réels de Jarvis — utilisés par les agents CrewAI.
Chaque tool est synchrone (requis par CrewAI).
"""

import os
import json
import time
import httpx
from pathlib import Path
from crewai.tools import tool

PROJECT_ROOT = Path(__file__).parent.parent  # C:\OpenJarvisNexus
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
MEMORY_FILE  = Path(__file__).parent / "memory.json"


# ── Mission STL ──────────────────────────────────────────

@tool("Mission STL 3D")
def stl_mission(prompt: str) -> str:
    """
    Lance une mission de création de modèle 3D STL et attend le résultat.
    prompt doit décrire précisément le modèle voulu (ex: 'low-poly dragon 15cm').
    Retourne le statut final et les derniers logs de la mission.
    """
    try:
        with httpx.Client(timeout=30) as c:
            r = c.post(
                f"http://localhost:{BACKEND_PORT}/v1/stl/mission",
                json={"prompt": prompt},
            )
            r.raise_for_status()
            payload = r.json()
            # stl_agent retourne "mission_id" (pas "id")
            mission_id = payload.get("id") or payload.get("mission_id")
            if not mission_id:
                return f"Erreur: réponse inattendue du serveur STL: {payload}"

        # statuts réels stl_agent: "complete", "partial", "error"
        STATUTS_FINAUX = {"complete", "partial", "error"}
        for _ in range(60):  # max 5 minutes (60 × 5s)
            time.sleep(5)
            with httpx.Client(timeout=10) as c:
                r = c.get(f"http://localhost:{BACKEND_PORT}/v1/stl/mission/{mission_id}")
                data = r.json()
            if data.get("status") in STATUTS_FINAUX:
                derniers_logs = [e["msg"] for e in data.get("logs", [])[-5:]]
                return json.dumps({
                    "id":     mission_id,
                    "status": data["status"],
                    "files":  list(data.get("files", {}).keys()),
                    "logs":   derniers_logs,
                }, ensure_ascii=False)

        return f"Mission {mission_id} toujours en cours après 5 minutes — vérifie le hub mission."
    except Exception as e:
        return f"Erreur mission STL: {e}"


# ── Recherche web ─────────────────────────────────────────

@tool("Recherche Web")
def web_search(query: str) -> str:
    """
    Recherche sur le web via DuckDuckGo (sans API key).
    Retourne un résumé + les 5 premiers résultats pertinents.
    """
    try:
        with httpx.Client(timeout=12, follow_redirects=True) as c:
            r = c.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            )
        data = r.json()

        lignes = []
        if data.get("AbstractText"):
            lignes.append(f"Résumé: {data['AbstractText']}")
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                lignes.append(f"- {topic['Text']}")

        return "\n".join(lignes) if lignes else "Aucun résultat pertinent trouvé."
    except Exception as e:
        return f"Erreur recherche web: {e}"


# ── Fichiers ──────────────────────────────────────────────

@tool("Lire un fichier")
def read_file(path: str) -> str:
    """
    Lit le contenu d'un fichier du projet.
    path peut être relatif à la racine du projet ou absolu.
    Tronqué à 8000 caractères si trop grand.
    """
    try:
        p = Path(path)
        if not p.is_absolute():
            p = PROJECT_ROOT / path
        if not p.exists():
            return f"Fichier introuvable: {p}"
        contenu = p.read_text(encoding="utf-8", errors="replace")
        if len(contenu) > 8000:
            return contenu[:8000] + f"\n\n... [tronqué — {len(contenu)} caractères au total]"
        return contenu
    except Exception as e:
        return f"Erreur lecture fichier: {e}"


@tool("Écrire un fichier")
def write_file(path: str, content: str) -> str:
    """
    Écrit du contenu dans un fichier du projet.
    path = chemin relatif à la racine du projet.
    Écriture refusée si le chemin sort du projet.
    """
    try:
        p = Path(path)
        if not p.is_absolute():
            p = PROJECT_ROOT / path
        # Sécurité : rester dans le projet
        p.resolve().relative_to(PROJECT_ROOT.resolve())
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Fichier écrit: {p} ({len(content)} caractères)"
    except ValueError:
        return "Écriture refusée: le chemin sort du répertoire projet."
    except Exception as e:
        return f"Erreur écriture fichier: {e}"


# ── Mémoire ───────────────────────────────────────────────

@tool("Lire la mémoire Jarvis")
def get_memory() -> str:
    """
    Lit les facts mémorisés de Jarvis (préférences David, contexte projet, état des missions).
    """
    try:
        if not MEMORY_FILE.exists():
            return "Mémoire vide — aucun fact enregistré."
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        facts = data.get("facts", {})
        if not facts:
            return "Aucun fact mémorisé."
        return json.dumps(facts, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Erreur lecture mémoire: {e}"


@tool("Sauvegarder un fait en mémoire")
def save_fact(key: str, value: str) -> str:
    """
    Sauvegarde un fait dans la mémoire persistante de Jarvis.
    key = identifiant court (ex: 'projet_actuel'), value = valeur à mémoriser.
    """
    try:
        data = {}
        if MEMORY_FILE.exists():
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        data.setdefault("facts", {})[key] = value
        MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"Fact '{key}' sauvegardé avec succès."
    except Exception as e:
        return f"Erreur sauvegarde mémoire: {e}"


# ── BRUCE — Agent Autonome OpenHands ─────────────────────

@tool("BRUCE — Exécution Autonome")
def bruce_run(task: str, repo_path: str = "/workspace") -> str:
    """
    Confie une tâche à BRUCE (OpenHands) pour exécution autonome.
    BRUCE peut lire/écrire des fichiers, exécuter du code, corriger des bugs.
    task = description précise de ce que BRUCE doit accomplir.
    Retourne le résultat de l'exécution ou le statut de la conversation.
    """
    openhands_url = os.getenv("OPENHANDS_URL", "http://localhost:3000")
    try:
        with httpx.Client(timeout=10) as c:
            # Démarrer une conversation OpenHands
            r = c.post(
                f"{openhands_url}/api/conversations",
                json={
                    "initial_user_msg": task,
                    "selected_repository": None,
                },
            )
            if r.status_code not in (200, 201):
                return f"BRUCE offline (OpenHands {r.status_code}). Lance-le via : docker compose up bruce"
            conv = r.json()
            conv_id = conv.get("conversation_id") or conv.get("id")
        return (
            f"BRUCE a reçu la mission (conversation {conv_id}).\n"
            f"Suis l'avancement sur http://localhost:3000\n"
            f"Mission : {task[:200]}"
        )
    except httpx.ConnectError:
        return (
            "BRUCE est offline. Lance OpenHands avec :\n"
            "docker compose up bruce\n"
            "ou : docker run -d -p 3000:3000 --name bruce "
            "-e SANDBOX_RUNTIME_CONTAINER_IMAGE=ghcr.io/all-hands-ai/runtime:latest "
            "-v /var/run/docker.sock:/var/run/docker.sock "
            "ghcr.io/all-hands-ai/openhands:latest"
        )
    except Exception as e:
        return f"Erreur BRUCE: {e}"


# ── Telegram ──────────────────────────────────────────────

@tool("Notifier David via Telegram")
def telegram_notify(message: str) -> str:
    """
    Envoie un message à David sur Telegram.
    À utiliser pour signaler une tâche terminée, un résultat important, ou une erreur critique.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    user_id   = os.getenv("TELEGRAM_AUTHORIZED_USER_ID", "")
    if not bot_token or not user_id:
        return "TELEGRAM_BOT_TOKEN ou TELEGRAM_AUTHORIZED_USER_ID manquant dans .env — notification impossible."
    try:
        with httpx.Client(timeout=10) as c:
            r = c.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id":    user_id,
                    "text":       f"🤖 Jarvis: {message}",
                    "parse_mode": "HTML",
                },
            )
        if r.status_code == 200:
            return "Notification Telegram envoyée à David."
        return f"Erreur Telegram {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return f"Erreur envoi Telegram: {e}"

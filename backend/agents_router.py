"""Multi-agent endpoints — agent runners (ULTRON/QWEN/CORTANA/BRUCE/JARVIS),
/task pipeline, budget, agent list & status.

Extracted from main.py. Reads shared client/budget/agent-status from app_state.
"""

import os

import budget_tracker
import httpx
from app_state import (
    BUDGET_MAX_USD,
    CLAUDE_MODEL,
    CLAUDE_MODEL_GROS,
    _agents_status,
    _budget,
    _enregistrer_cout,
    _log_error_500,
    claude,
    get_http,
)
from fastapi import APIRouter
from ollama_client import (
    OLLAMA_MODEL,
    ask_ollama_chat,
    is_ollama_available,
)
from pydantic import BaseModel

router = APIRouter(tags=["agents"])


# ─── moved verbatim from main.py ───
OPENHANDS_URL = os.getenv("OPENHANDS_URL", "http://localhost:3000")

AGENT_SYSTEM_PROMPTS = {
    "ULTRON": (
        "Tu es ULTRON, agent d'analyse stratégique de NexusX9. "
        "Modèle: Claude Sonnet 4-6. "
        "Tu analyses en profondeur, tu planifies, tu structures. "
        "Réponds en français. Sois précis et exhaustif."
    ),
    "QWEN": (
        "Tu es QWEN, agent d'exécution masse de NexusX9. "
        "Modèle: Ollama qwen3:14b local. "
        "Tu génères du contenu en volume, tu traites des données, tu résumes. "
        "Réponds en français. Sois efficace et concis."
    ),
    "CORTANA": (
        "Tu es CORTANA, agent ingénierie de NexusX9. "
        "Modèle: deepseek-coder:6.7b. "
        "Tu écris du code Python/FastAPI/React/TypeScript COMPLET et fonctionnel. "
        "Toujours livrer le code entier, jamais partiel. Commentaires en français."
    ),
    "JARVIS": (
        "Tu es JARVIS, orchestrateur de NexusX9. "
        "Modèle: Claude Haiku 4-5. "
        "Réponds en anglais, style Iron Man JARVIS. Ultra-concis. Commence par ⬡."
    ),
}

async def _run_ultron(task: str) -> dict:
    """ULTRON — Claude Sonnet 4-6."""
    try:
        resp = claude.messages.create(
            model=CLAUDE_MODEL_GROS,
            max_tokens=4096,
            temperature=0.7,
            system=AGENT_SYSTEM_PROMPTS["ULTRON"],
            messages=[{"role": "user", "content": task}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        _enregistrer_cout(
            resp.usage.input_tokens + resp.usage.output_tokens, CLAUDE_MODEL_GROS,
            input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
        )
        return {"ok": True, "agent": "ULTRON", "model": CLAUDE_MODEL_GROS, "result": text}
    except Exception as e:
        return {"ok": False, "agent": "ULTRON", "error": str(e)}

async def _run_qwen(task: str) -> dict:
    """QWEN — Ollama qwen3:14b."""
    try:
        msgs = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPTS["QWEN"]},
            {"role": "user",   "content": task},
        ]
        text = ask_ollama_chat(msgs, OLLAMA_MODEL)
        _budget["appels_ollama"] += 1
        budget_tracker.record_ollama_call()
        if text is None:
            # ask_ollama_chat retourne None sur timeout — message propre
            return {"ok": False, "agent": "QWEN", "error": "Ollama timeout — QWEN ne répond pas (>60s). Vérifie que Ollama tourne: 1_OLLAMA.bat"}
        return {"ok": True, "agent": "QWEN", "model": OLLAMA_MODEL, "result": text or "Pas de réponse Ollama."}
    except httpx.TimeoutException:
        return {"ok": False, "agent": "QWEN", "error": "Ollama timeout — QWEN ne répond pas. Relance Ollama via 1_OLLAMA.bat"}
    except Exception as e:
        return {"ok": False, "agent": "QWEN", "error": str(e)}

async def _run_cortana(task: str) -> dict:
    """CORTANA — deepseek-coder:6.7b."""
    try:
        msgs = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPTS["CORTANA"]},
            {"role": "user",   "content": task},
        ]
        text = ask_ollama_chat(msgs, "deepseek-coder:6.7b")
        _budget["appels_ollama"] += 1
        budget_tracker.record_ollama_call()
        if text is None:
            # ask_ollama_chat retourne None sur timeout — message propre
            return {"ok": False, "agent": "CORTANA", "error": "Ollama timeout — CORTANA ne répond pas (>60s). Vérifie que Ollama tourne: 1_OLLAMA.bat"}
        return {"ok": True, "agent": "CORTANA", "model": "deepseek-coder:6.7b", "result": text or "Pas de réponse CORTANA."}
    except httpx.TimeoutException:
        return {"ok": False, "agent": "CORTANA", "error": "Ollama timeout — CORTANA ne répond pas. Relance Ollama via 1_OLLAMA.bat"}
    except Exception as e:
        return {"ok": False, "agent": "CORTANA", "error": str(e)}

async def _run_bruce(task: str) -> dict:
    """BRUCE — OpenHands autonome — utilise le client HTTP partagé."""
    if get_http() is None:
        return {"ok": False, "agent": "BRUCE", "error": "Client HTTP non initialisé — backend pas encore prêt."}
    try:
        r = await get_http().post(
            f"{OPENHANDS_URL}/api/conversations",
            json={"initial_user_msg": task},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            return {"ok": False, "agent": "BRUCE", "error": f"OpenHands HTTP {r.status_code}. Lance: docker start nexus_bruce"}
        data = r.json()
        conv_id = data.get("conversation_id") or data.get("id") or "?"
        _agents_status["BRUCE"] = "active"
        return {
            "ok":      True,
            "agent":   "BRUCE",
            "model":   "OpenHands + qwen3:14b",
            "conv_id": conv_id,
            "result":  f"⬡ BRUCE mission launched — conversation {conv_id}.\nMonitor: {OPENHANDS_URL}\nTask: {task[:120]}",
        }
    except httpx.ConnectError:
        return {"ok": False, "agent": "BRUCE", "error": "BRUCE offline. Lance: docker start nexus_bruce"}
    except Exception as e:
        return {"ok": False, "agent": "BRUCE", "error": str(e)}

async def _run_jarvis(task: str) -> dict:
    """JARVIS — Claude Haiku, routing par défaut."""
    # Récupère le contexte Vault pertinent
    vault_context = ""
    try:
        from vault.memory_manager import vault_query
        memories = await vault_query(task, collections=["orchestration", "workflows", "conversations"])
        if memories:
            vault_context = "\n\nVault Context (relevant memories):\n" + "\n".join(
                f"- [{m['collection']}] {m['text'][:150]}" for m in memories[:3]
            )
    except Exception:
        pass

    # Ajoute le contexte au message si disponible
    enriched_task = task + vault_context if vault_context else task

    try:
        resp = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            temperature=0.3,
            system=AGENT_SYSTEM_PROMPTS["JARVIS"],
            messages=[{"role": "user", "content": enriched_task}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        _enregistrer_cout(
            resp.usage.input_tokens + resp.usage.output_tokens, CLAUDE_MODEL,
            input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
        )

        # Sauvegarde dans Vault conversations
        try:
            from vault.memory_manager import add_memory
            await add_memory("conversations",
                f"User: {task}\nJARVIS: {text}",
                metadata={"agent": "JARVIS", "model": CLAUDE_MODEL}
            )
        except Exception:
            pass

        return {"ok": True, "agent": "JARVIS", "model": CLAUDE_MODEL, "result": text}
    except Exception as e:
        return {"ok": False, "agent": "JARVIS", "error": str(e)}

class TaskRequest(BaseModel):
    agent: str = "JARVIS"
    task: str

@router.post("/task")
async def run_task(data: TaskRequest):
    """Pipeline multi-agents — route vers JARVIS/ULTRON/QWEN/CORTANA/BRUCE.
    Retourne toujours {"ok": bool, "result": str, "error": str|null} — jamais de 500 brut.
    """
    try:
        agent = data.agent.upper().strip()
        task  = data.task.strip()
        if not task:
            return {"ok": False, "result": "", "error": "task vide"}

        if agent not in _agents_status:
            _agents_status[agent] = "idle"
        _agents_status[agent] = "active"
        result: dict = {}
        try:
            if   agent == "BRUCE":   result = await _run_bruce(task)
            elif agent == "ULTRON":  result = await _run_ultron(task)
            elif agent == "QWEN":    result = await _run_qwen(task)
            elif agent == "CORTANA": result = await _run_cortana(task)
            else:                    result = await _run_jarvis(task)
        finally:
            _agents_status[agent] = "idle" if agent != "BRUCE" else _agents_status.get("BRUCE", "idle")

        # Vault orchestration log
        try:
            from vault.memory_manager import add_memory
            await add_memory("orchestration",
                f"Agent: {agent} | Task: {task[:200]} | Result: {result.get('result','')[:200]}",
                metadata={"agent": agent, "ok": str(result.get("ok", False))}
            )
        except Exception:
            pass

        # Normalise la réponse — toujours {ok, result, error}
        return {
            "ok":     result.get("ok", False),
            "result": result.get("result", ""),
            "error":  result.get("error", None),
            # Champs supplémentaires passés tels quels
            **{k: v for k, v in result.items() if k not in ("ok", "result", "error")},
        }

    except Exception as exc:
        _log_error_500("/task", exc)
        return {"ok": False, "result": "", "error": f"Erreur interne: {type(exc).__name__}: {exc}"}


@router.get("/v1/budget")
def get_budget():
    stats = budget_tracker.get_stats()
    stats["session"] = {
        "cost_usd":     round(_budget["cout_usd"], 6),
        "calls_claude": _budget["appels_claude"],
        "calls_ollama": _budget["appels_ollama"],
    }
    stats["budget_max"] = BUDGET_MAX_USD
    stats["budget_remaining"] = round(BUDGET_MAX_USD - _budget["cout_usd"], 6)
    return stats


@router.get("/v1/agents")
def agents_list():
    ollama_ok = is_ollama_available()
    bruce_url = os.getenv("OPENHANDS_URL", "http://localhost:3000")
    try:
        import httpx
        bruce_ok = httpx.get(f"{bruce_url}/api/options/models", timeout=2).status_code == 200
    except Exception:
        bruce_ok = False

    return {"agents": [
        # ── Hiérarchie principale ──────────────────────────────
        {
            "id":          "jarvis",
            "name":        "JARVIS",
            "provider":    "claude",
            "model":       CLAUDE_MODEL,
            "role":        "Orchestrateur central",
            "description": "Claude Haiku 4-5 — orchestre tous les agents, routing intelligent.",
            "status":      _agents_status.get("JARVIS", "online"),
        },
        {
            "id":          "ultron",
            "name":        "ULTRON",
            "provider":    "claude",
            "model":       CLAUDE_MODEL_GROS,
            "role":        "Analyse complexe & Décisions",
            "description": "Claude Sonnet 4-6 — raisonnement avancé, architecture, stratégie.",
            "status":      _agents_status.get("ULTRON", "idle"),
        },
        {
            "id":          "kaizen",
            "name":        "KAIZEN",
            "provider":    "meshy+local",
            "model":       "Meshy AI + trimesh + pymeshfix",
            "role":        "Ingénieur 3D — Fabrication",
            "description": "Meshy AI génère OBJ/STL. BRUCE (pymeshfix) répare. watertight garanti avant Bambu.",
            "status":      _agents_status.get("KAIZEN", "idle"),
        },
        {
            "id":          "qwen",
            "name":        "QWEN",
            "provider":    "ollama",
            "model":       OLLAMA_MODEL,
            "role":        "Intelligence générale & Recherche",
            "description": "Ollama qwen3:14b — tâches générales, recherche, analyse. Local & gratuit.",
            "status":      _agents_status.get("QWEN", "idle") if ollama_ok else "offline",
        },
        {
            "id":          "cortana",
            "name":        "CORTANA",
            "provider":    "ollama",
            "model":       "deepseek-coder:6.7b",  # TOUJOURS
            "role":        "Développement & Automatisation",
            "description": "deepseek-coder:6.7b — Python, FastAPI, React, scripts. Code complet toujours.",
            "status":      _agents_status.get("CORTANA", "idle") if ollama_ok else "offline",
        },
        {
            "id":          "bruce",
            "name":        "BRUCE",
            "provider":    "openhands",
            "model":       "qwen3:14b",  # TOUJOURS
            "role":        "Agent Autonome OpenHands",
            "description": "OpenHands + qwen3:14b — exécution autonome, lecture/écriture fichiers, git.",
            "status":      "active" if bruce_ok else _agents_status.get("BRUCE", "offline"),
        },
        # ── Agents STL Pipeline ────────────────────────────────
        {
            "id":          "stl_blender",
            "name":        "Blender Agent",
            "provider":    "mixed",
            "model":       OLLAMA_MODEL,
            "role":        "3D Generation & Repair",
            "description": "Meshy AI / Blender — génération STL, repair, simplification, export Bambu.",
            "status":      "idle",
        },
        {
            "id":          "stl_concept",
            "name":        "Concept Agent",
            "provider":    "claude",
            "model":       CLAUDE_MODEL,
            "role":        "Design & 3D Specifications",
            "description": "Brief technique low-poly fantasy, contraintes FDM, dimensions 15cm.",
            "status":      "idle",
        },
        {
            "id":          "stl_optim",
            "name":        "Optimizer",
            "provider":    "ollama",
            "model":       OLLAMA_MODEL,
            "role":        "Print Quality Audit",
            "description": "Scale 15cm, overhang map, printability score.",
            "status":      "idle",
        },
        {
            "id":          "stl_files",
            "name":        "File Manager",
            "provider":    "ollama",
            "model":       OLLAMA_MODEL,
            "role":        "STL Conversion & Validation",
            "description": "trimesh, pymeshfix, validation manifold, handoff Bambu Studio.",
            "status":      "idle",
        },
        {
            "id":          "stl_research",
            "name":        "Researcher",
            "provider":    "ollama",
            "model":       OLLAMA_MODEL,
            "role":        "STL Trends Intelligence",
            "description": "Rapport quotidien 21h — Thingiverse, Cults3D, Etsy top STL.",
            "status":      "idle",
        },
        # ── Business ───────────────────────────────────────────
        {
            "id":          "etsy",
            "name":        "Etsy Agent",
            "provider":    "claude",
            "model":       CLAUDE_MODEL,
            "role":        "Boutique D3Dprintix",
            "description": "Listings, SEO, images, pricing via n8n + Claude.",
            "status":      "idle",
        },
    ]}

@router.post("/v1/agents/{agent_name}/enable")
def enable_agent(agent_name: str):
    _agents_status[agent_name] = "active"
    print(f"[agent] {agent_name} activé")
    return {"ok": True, "agent": agent_name, "status": "active"}

@router.post("/v1/agents/{agent_name}/disable")
def disable_agent(agent_name: str):
    _agents_status[agent_name] = "idle"
    print(f"[agent] ⏸️  {agent_name} désactivé")
    return {"ok": True, "agent": agent_name, "status": "idle"}

@router.get("/v1/agents/{agent_name}/status")
def agent_status(agent_name: str):
    status = _agents_status.get(agent_name, "unknown")
    return {"agent": agent_name, "status": status}

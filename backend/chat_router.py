"""Main chat endpoint (/v1/chat/completions) + model picker.

Extracted from main.py. The big one: routing (Haiku/Sonnet/Ollama), Docker &
Skill shortcuts, tool loop, SSE streaming, session continuity & memory.
Reads shared client/budget from app_state; owns the chat-only detectors.
"""

import json
import re
import threading
import time
import unicodedata
from typing import Optional

import budget_tracker
from anthropic import APIError
from app_state import (
    BUDGET_MAX_USD,
    CLAUDE_MODEL,
    CLAUDE_MODEL_GROS,
    _budget,
    _budget_ok,
    _build_base_system,
    _enregistrer_cout,
    claude,
)
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from ollama_client import (
    OLLAMA_MODEL,
    ask_ollama_chat,
    get_claude_model,
    is_ollama_available,
    list_local_models,
    should_use_claude,
    stream_ollama_chat,
    strip_think_tags,
)
from pydantic import BaseModel
from tools.brain_tools import CLAUDE_TOOL_DEFS as _BRAIN_TOOL_DEFS
from tools.brain_tools import dispatch as _brain_dispatch
from tools.docker_tools import CLAUDE_TOOL_DEFS as _DOCKER_TOOL_DEFS
from tools.docker_tools import dispatch as _docker_dispatch
from tools.docker_tools import quick_status_text as _docker_quick_status
from tools.skill_tools import CLAUDE_TOOL_DEFS as _SKILL_TOOL_DEFS
from tools.skill_tools import dispatch as _skill_dispatch
from tools.skill_tools import skill_catalog_text as _skill_catalog_text
from tools.stl_tools import CLAUDE_TOOL_DEFS as _STL_TOOL_DEFS
from tools.stl_tools import dispatch as _stl_dispatch

from memory import (
    add_message,
    build_system_prompt,
    compress_session_sync,
    get_history,
    get_last_session_summary,
    is_new_session,
    load_config,
    load_facts,
)

router = APIRouter(tags=["chat"])


# ─── moved verbatim from main.py ───
class ChatMessage(BaseModel):
    role:    str
    content: str
    # Optional base64-encoded images attached to THIS message (vision).
    # Each entry may be a raw base64 string OR a data URL (`data:image/png;base64,…`).
    # Only Claude can see them — when ANY message carries images, routing is
    # forced to Claude (qwen3/deepseek are text-only).
    images:  Optional[list[str]] = None

class ChatRequest(BaseModel):
    message:     Optional[str]               = None
    messages:    Optional[list[ChatMessage]] = None
    model:       Optional[str]               = None
    system:      Optional[str]               = None
    max_tokens:  int                         = 1024
    temperature: float                       = 0.7
    stream:      bool                        = False
    session_id:  str                         = "default"
    # Bypass du routing d'intention JARVIS (détection pipeline/skill) pour les
    # appels LLM INTERNES (génération de concept STL, plan ULTRON Forge…). Sans
    # ça, un message interne contenant "meshy"/"stl" déclenche un faux pipeline
    # et renvoie un template à la place de la vraie réponse du modèle.
    skip_pipeline: bool                      = False

# ── Helpers ──────────────────────────────────────────────
# Decorative glyphs JARVIS must never emit: emoji + bullets/arrows/etc. They
# break the Kokoro TTS (read aloud) and clash with the plain-text persona. We
# strip them server-side because no prompt rule is 100% reliable on a small model.
_DECOR_EXTRA = set("→←↔⇒⟶➜➤▶◀◆●○•◦▪▫■★☆✦✧✪⬡⬢▸▹‣·∙")
_VARIATION_SELECTORS = {chr(c) for c in range(0xFE00, 0xFE10)}


def _strip_decorations(text: str) -> str:
    """Remove emoji / decorative symbols while keeping normal prose, punctuation
    (em dash, quotes), and code/math operators intact."""
    if not text:
        return text
    out = []
    for ch in text:
        if ch in _VARIATION_SELECTORS:
            continue
        if ch in _DECOR_EXTRA:
            continue
        # So = "Symbol, other" (emoji, ✅, ⬡…), Sk = modifier, Cf = format (ZWJ…)
        if unicodedata.category(ch) in ("So", "Sk", "Cf"):
            continue
        out.append(ch)
    return "".join(out)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

def _get_session_id(req: ChatRequest, request: Request) -> str:
    if req.session_id and req.session_id != "default":
        return req.session_id
    ip = request.client.host if request.client else "local"
    return f"ip:{ip}"


# ── Vision helpers ──────────────────────────────────────────────────────────
# Claude content can be a string (text-only) OR a list of blocks (multimodal).
# When the frontend attaches images we build the list-of-blocks form; otherwise
# we keep the historical string form so nothing else has to change.

def _text_of(content) -> str:
    """Plain-text view of a Claude content (str OR list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _image_blocks(images: Optional[list[str]]) -> list[dict]:
    """base64 strings or data URLs → Anthropic image content blocks."""
    out: list[dict] = []
    for raw in images or []:
        if not isinstance(raw, str):
            continue
        media_type, data = "image/png", raw
        if raw.startswith("data:"):
            try:
                header, data = raw.split(",", 1)
                media_type = header[5:].split(";")[0] or "image/png"
            except ValueError:
                continue
        if not data:
            continue
        out.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        })
    return out


def _build_chat_msg(m: ChatMessage) -> dict:
    """Build the dict that goes into anthropic_messages. Images → list content."""
    if m.images:
        parts: list[dict] = _image_blocks(m.images)
        if m.content and m.content.strip():
            parts.append({"type": "text", "text": m.content})
        if parts:
            return {"role": m.role, "content": parts}
    return {"role": m.role, "content": m.content}


def _has_images(msgs: list[dict]) -> bool:
    return any(isinstance(m.get("content"), list) for m in msgs)

def _stream_text(text: str, model_used: str, req_id: str, memory: dict | None = None):
    yield _sse({
        "id": req_id, "object": "chat.completion.chunk",
        "model": model_used,
        "choices": [{"index": 0,
                     "delta": {"role": "assistant", "content": ""},
                     "finish_reason": None}]
    })
    for i in range(0, len(text), 12):
        yield _sse({
            "id": req_id, "object": "chat.completion.chunk",
            "model": model_used,
            "choices": [{"index": 0,
                         "delta": {"content": text[i:i+12]},
                         "finish_reason": None}]
        })
        time.sleep(0.01)
    _final = {
        "id": req_id, "object": "chat.completion.chunk",
        "model": model_used,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    if memory:
        _final["memory"] = memory
    yield _sse(_final)
    yield "data: [DONE]\n\n"


def _claude_stream_gen(model_used, system, anthropic_messages, all_tools,
                       max_tokens, temperature, session_id, req_id, memory_meta):
    """Real-time SSE generator for the Claude path.

    Streams tokens live via ``claude.messages.stream()`` and runs the tool loop
    in place (any preamble text of a tool turn is streamed too). Replaces the
    old blocking ``create()`` + ``_stream_text`` replay that forced the user to
    wait for the entire generation before seeing the first word.
    """
    def _chunk(content):
        return _sse({
            "id": req_id, "object": "chat.completion.chunk", "model": model_used,
            "choices": [{"index": 0, "delta": {"content": content},
                         "finish_reason": None}],
        })

    _tool_msgs = list(anthropic_messages)
    _parts: list[str] = []
    _total_in, _total_out = 0, 0

    # initial role chunk
    yield _sse({
        "id": req_id, "object": "chat.completion.chunk", "model": model_used,
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""},
                     "finish_reason": None}],
    })

    try:
        while True:
            _kw = dict(model=model_used, max_tokens=max_tokens,
                       temperature=temperature, system=system, messages=_tool_msgs)
            if all_tools:
                _kw["tools"] = all_tools

            with claude.messages.stream(**_kw) as _st:
                for _delta in _st.text_stream:
                    _delta = _strip_decorations(_delta)
                    if not _delta:
                        continue
                    _parts.append(_delta)
                    yield _chunk(_delta)
                _final = _st.get_final_message()

            _total_in  += _final.usage.input_tokens
            _total_out += _final.usage.output_tokens

            if _final.stop_reason != "tool_use":
                break

            # Execute tool calls, append results, loop for the next turn
            _tool_results = []
            for _blk in _final.content:
                if getattr(_blk, "type", None) == "tool_use":
                    _tname = _blk.name
                    print(f"[tool] calling {_tname} {_blk.input}")
                    if _tname.startswith("skill_"):
                        _res = _skill_dispatch(_tname, _blk.input)
                    elif _tname.startswith("brain_"):
                        _res = _brain_dispatch(_tname, _blk.input)
                    elif _tname.startswith("stl_"):
                        _res = _stl_dispatch(_tname, _blk.input)
                    else:
                        _res = _docker_dispatch(_tname, _blk.input)
                    _tool_results.append({
                        "type": "tool_result", "tool_use_id": _blk.id, "content": _res,
                    })
            _tool_msgs.append({"role": "assistant", "content": _final.content})
            _tool_msgs.append({"role": "user",      "content": _tool_results})

        _enregistrer_cout(_total_in + _total_out, model_used,
                          input_tokens=_total_in, output_tokens=_total_out)

    except APIError as _e:
        # Crédit Anthropic épuisé → fallback Ollama (rejoué en chunks)
        _msg = str(_e)
        if "credit balance" in _msg.lower() or "insufficient" in _msg.lower():
            print("[claude] Crédit épuisé — fallback Ollama (stream)")
            _budget["cout_usd"] = BUDGET_MAX_USD + 1.0
            _fb = ""
            if is_ollama_available():
                _fb = ask_ollama_chat(
                    [{"role": "system", "content": system}] + anthropic_messages,
                    OLLAMA_MODEL,
                )
                if _fb:
                    _fb = strip_think_tags(_fb)
            if not _fb:
                _fb = ("Crédits Anthropic épuisés. Recharge sur "
                       "https://console.anthropic.com/settings/billing")
            for _i in range(0, len(_fb), 12):
                _parts.append(_fb[_i:_i + 12])
                yield _chunk(_fb[_i:_i + 12])
        else:
            _err = f"Erreur API Claude: {_msg[:200]}"
            _parts.append(_err)
            yield _chunk(_err)
    except Exception as _e:
        _err = f"Erreur Claude: {_e}"
        _parts.append(_err)
        yield _chunk(_err)

    _text = "".join(_parts).strip() or "Désolé David, je n'ai pas pu générer de réponse. Réessaie."
    add_message(session_id, "assistant", _text)
    print(f"[chat] modèle={model_used} (stream) '{_text[:50]}...'")

    _fin = {
        "id": req_id, "object": "chat.completion.chunk", "model": model_used,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    if memory_meta:
        _fin["memory"] = memory_meta
    yield _sse(_fin)
    yield "data: [DONE]\n\n"


# ════════════════════════════════════════════════════════
# ROUTES SYSTÈME
# ════════════════════════════════════════════════════════


@router.get("/v1/models")
def models_list():
    # Embedding / non-chat models — never appear in the chat model picker
    _EMBED_SKIP = re.compile(
        r"(embed|embedding|vision-only|clip|rerank|bge-|e5-|nomic-embed|all-minilm)",
        re.I,
    )
    models = [{"id": CLAUDE_MODEL,      "provider": "anthropic", "available": True}]
    # Add Sonnet only if user hasn't run out of credits (budget guard)
    if _budget_ok():
        models.append({"id": CLAUDE_MODEL_GROS, "provider": "anthropic", "available": True})
    if is_ollama_available():
        for m in list_local_models():
            if not _EMBED_SKIP.search(m):   # skip embedding / non-chat models
                models.append({"id": m, "provider": "ollama", "available": True})
    return {"models": models}

@router.get("/v1/managed-agents")
def managed_agents():
    return {"agents": []}



# ════════════════════════════════════════════════════════
# CHAT PRINCIPAL
# ════════════════════════════════════════════════════════

_MEM_MIN_CHARS = 140
_DEBUG_KEYWORDS = (
    "debug", "erreur", "error", "bug", "traceback", "exception",
    "stack trace", "stacktrace", "crash", "plante", "marche pas",
    "fails", "failing", "not working",
)

# Docker keyword detector — triggers tool injection in Claude / status injection in Ollama
_DOCKER_KW = re.compile(
    r"\b(docker|container|compose|chromadb|postgres|redis|traefik|nexus_\w+)\b"
    r"|quel\s+(service|container)|les?\s+containers?|est[- ]ce\s+que\s+docker"
    r"|restart\s+\w+|stop\s+\w+container|start\s+\w+container"
    r"|logs?\s+(du\s+)?(container|service)",
    re.I,
)

# Docker status/action + Skill-list detectors — compiled once at import, used per request
_DOCKER_SHOW_KW = re.compile(
    r"\b(montre|liste|affiche|show|donne|quels?|combien|ps|status|statut|état|voir|check|ping)\b"
    r"|\bup\b|\bdown\b|\brunning\b",
    re.I,
)
_DOCKER_ACTION_KW = re.compile(
    r"\b(restart|redémarre|stop|arrête|start|démarre|lance|kill|rm|remove)\b", re.I
)
_SKILL_LIST_KW = re.compile(
    r"\bskill?s?\b|skils?\b|comp[eé]tences?\b|capacit[eé]s?\b|\bsavoir-faire\b|\bprocédures?\b",
    re.I,
)
_SKILL_LIST_SHOW_KW = re.compile(
    r"\b(liste|list|montre|affiche|show|quels?|quelles?|donne|voir|dis.?moi|what|have|got|as-tu|avez)\b",
    re.I,
)
# Action verbs that mean "run/apply a specific skill" — those must NOT trigger
# the bypass-catalog shortcut. Claude should call `skill_get` + follow the
# protocol via tool_use instead.
_SKILL_ACTION_KW = re.compile(
    r"\b(utilise|use|applique|apply|lance|launch|run|exec|execute|exécute|invoque|invoke|do|fais|fait)\b",
    re.I,
)
# STL-modification intent → expose the stl_* tools (repair/scale/hollow/cut/validate).
# "génère un stl" is caught earlier by detect_pipeline; here we catch *modify* asks.
_STL_KW = re.compile(
    r"\.stl\b|\.3mf\b|\bstl\b|\b3mf\b|\bmesh\b|maillage|figurine|"
    r"répar|repair|watertight|manifold|"
    r"scale|redimensionn|agrandi|rédui|rédui|"
    r"creus|évide|evide|hollow|"
    r"découp|decoup|\bcut\b|"
    r"imprimable|décim|decim|"
    r"\bbambu\b|convert",
    re.I,
)

# Image jointe + intention 3D/impression -> on déclenche la VRAIE mission
# image-to-3D (forge) au lieu de laisser le modèle de chat HALLUCINER "Meshy en
# cours… export…". Volontairement resserré (pas "personnage"/"modèle" seuls pour
# éviter de se déclencher sur un simple "décris ce personnage").
_STL_IMG_INTENT = re.compile(
    r"\bstl\b|\b3d\b|3d[\s-]?print|imprim|\bprint\b|figurine|maquette|sculpt|"
    r"\bmeshy\b|\bbambu\b|mod[eè]le\s*3d|statue|miniature|\bforge\b|"
    # objets plats 2D-depuis-image → voie jeton relief (relief_token.is_token_request)
    r"\bjeton(s)?\b|\btoken(s)?\b|\bcoin(s)?\b|\bm[ée]daille(s)?\b|\bmedal(s)?\b|"
    r"\bbadge(s)?\b|\bpog(s)?\b|\bcoaster(s)?\b|\bmagnet(s)?\b",
    re.I,
)

# Dernière mission forge lancée PAR session — pour répondre au VRAI statut sur
# "done?/fini?/c'est prêt?" au lieu de laisser le modèle halluciner la progression.
_LAST_FORGE_MISSION: dict[str, str] = {}
_STL_STATUS_INTENT = re.compile(
    r"\bdone\b|\bfini[se]?\b|termin|\bpr[eê]t\b|\bready\b|status|statut|avancement|"
    r"progress|o[uù]\s+en\s+est|et\s+maintenant|and\s+now|c'?est\s+bon|[çc]a\s+avance|"
    r"alors\s*\?",
    re.I,
)


def _needs_memory(msg: str) -> bool:
    """Déclenche l'injection brain/vault : message long, complexe, ou debug."""
    m = (msg or "").strip()
    if len(m) > _MEM_MIN_CHARS:
        return True
    if should_use_claude(m):
        return True
    low = m.lower()
    return any(k in low for k in _DEBUG_KEYWORDS)


@router.post("/v1/chat/completions")
def chat_completion(req: ChatRequest, request: Request):
    session_id = _get_session_id(req, request)

    # ── Session continuity — capturer AVANT add_message ──────
    _was_new_session = is_new_session(session_id)

    if req.messages:
        new_msgs = [
            _build_chat_msg(m)
            for m in req.messages
            # Keep messages with text OR with images (images alone = "what is this?")
            if m.role in ("user", "assistant") and (m.content.strip() or m.images)
        ]
        last_user = next(
            (_text_of(m["content"]) for m in reversed(new_msgs) if m["role"] == "user"),
            None
        )
        if last_user:
            add_message(session_id, "user", last_user)
        anthropic_messages = new_msgs

    elif req.message:
        add_message(session_id, "user", req.message)
        anthropic_messages = get_history(session_id)

    else:
        raise HTTPException(422, "Fournir 'message' ou 'messages'")

    last_user_msg = next(
        (_text_of(m["content"]) for m in reversed(anthropic_messages) if m["role"] == "user"),
        ""
    )

    # Appels LLM INTERNES (skip_pipeline=True : génération de concept STL, plan
    # ULTRON Forge…) : on coupe TOUT le routing d'intention (docker/skills/cheat/
    # pipeline) ET l'exposition des outils → completion LLM pure, jamais détournée
    # vers un template ou un appel d'outil. Sans ça, un prompt de design contenant
    # "docker"/"cheat"/"compétence"/"figurine" auto-déclenchait un short-circuit.
    _routing_on = not req.skip_pipeline

    # Detect whether this message is about Docker / containers
    _needs_docker = bool(_DOCKER_KW.search(last_user_msg))

    # ── Shortcut Docker STATUS — bypass LLM entièrement ─────
    # Si la question concerne l'affichage/liste des containers (pas une action start/stop/restart),
    # on formate la réponse directement depuis l'API Docker sans passer par Claude ou Ollama.
    if _routing_on and _needs_docker and _DOCKER_SHOW_KW.search(last_user_msg) and not _DOCKER_ACTION_KW.search(last_user_msg):
        try:
            from tools.docker_tools import docker_status as _ds
            _dstat = _ds()
            if _dstat["ok"]:
                _up   = _dstat["up"]
                _tot  = _dstat["total"]
                _rows = []
                for _c in _dstat["containers"]:
                    _state = "UP  " if _c["running"] else "DOWN"
                    _name  = _c["name"].replace("nexus_", "")
                    # Ports : seulement les ports hote (ex: [8000, 5173])
                    _raw_ports = _c.get("ports", "") or ""
                    _plist = []
                    for _pp in _raw_ports.split(","):
                        _pp = _pp.strip()
                        if "->" in _pp:
                            _hp = _pp.split("->")[0].split(":")[-1]
                            if _hp and _hp not in _plist:
                                _plist.append(_hp)
                    _ports = f"  [{', '.join(_plist)}]" if _plist else ""
                    # Status : sans les parens de sante
                    _st = _c["status"].split("(")[0].strip()
                    _rows.append(f"  {_state}  {_name:<20}{_st}{_ports}")
                _docker_resp = f"{_up}/{_tot} containers en ligne.\n\n" + "\n".join(_rows)
            else:
                _docker_resp = f"Docker inaccessible : {_dstat.get('error', '?')}"
        except Exception as _de:
            _docker_resp = f"Erreur Docker : {_de}"
        add_message(session_id, "assistant", _docker_resp)
        _dreq_id = f"chatcmpl-docker-{int(time.time())}"
        # Le frontend envoie toujours stream=True — on retourne du SSE
        if req.stream:
            return StreamingResponse(
                _stream_text(_docker_resp, "docker-direct", _dreq_id),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return {
            "id":      _dreq_id,
            "object":  "chat.completion",
            "model":   "docker-direct",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": _docker_resp}, "finish_reason": "stop"}],
            "usage":   {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    # ── Shortcut SKILLS — liste directe sans LLM ─────────────
    # Trigger only when the intent is unambiguously "give me the catalog":
    #   1. mentions the skill concept
    #   2. uses a show-verb (liste/show/quels…) OR is a 1-2 word query
    #   3. AND does NOT contain an action verb (utilise/applique/lance/…)
    # The action-verb guard lets Claude handle "applique le skill humanizer"
    # via skill_get tool-use instead of being short-circuited to a catalog dump.
    _skill_msg_short  = len(last_user_msg.strip().split()) <= 2
    _is_skill_action  = bool(_SKILL_ACTION_KW.search(last_user_msg))
    if _routing_on and _SKILL_LIST_KW.search(last_user_msg) and not _is_skill_action and (
        _SKILL_LIST_SHOW_KW.search(last_user_msg) or _skill_msg_short
    ):
        try:
            from tools.skill_tools import skill_list as _sl
            _sdata = _sl()
            if _sdata["ok"] and _sdata["total"] > 0:
                _slines = [f"{_sdata['total']} skills installées :"]
                for _sk in _sdata["skills"]:
                    _slines.append(f"  {_sk['name']} — {_sk['description']}")
                _skill_resp = "\n".join(_slines)
            else:
                _skill_resp = "Aucune skill installée."
        except Exception as _se:
            _skill_resp = f"Erreur lecture skills : {_se}"
        add_message(session_id, "assistant", _skill_resp)
        _sreq_id = f"chatcmpl-skill-{int(time.time())}"
        if req.stream:
            return StreamingResponse(
                _stream_text(_skill_resp, "skill-direct", _sreq_id),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return {
            "id": _sreq_id, "object": "chat.completion", "model": "skill-direct",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": _skill_resp}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    # ── Shortcut JARVIS: RUN CHEAT CODE ─────────────────────
    if _routing_on and "jarvis" in last_user_msg.lower() and "cheat" in last_user_msg.lower():
        import asyncio as _asyncio

        from pipeline_runner import run_cheat_code
        try:
            report = _asyncio.run(run_cheat_code(voice=True))
        except Exception as _e:
            report = {"status": "error", "error": str(_e), "agents": {"online": 0, "total": 0, "details": []}, "pipelines": {}}
        agents_ok    = report["agents"]["online"]
        agents_total = report["agents"]["total"]
        vault_info   = report.get("vault", {})
        total_mems   = vault_info.get("total_memories", 0)
        eco          = report.get("ecosystem", {})
        eco_score    = eco.get("score", "—")
        eco_grade    = eco.get("grade", "—")
        daily_info   = report.get("daily_tasks", {})
        cheat_text   = (
            f"⚡ **CHEAT CODE ULTIME ACTIVÉ**\n\n"
            f"**Agents :** {agents_ok}/{agents_total} en ligne\n"
            + "".join(
                f"- {'✅' if a['ok'] else '❌'} {a['agent']}\n"
                for a in report["agents"]["details"]
            )
            + f"\n**Ecosystem :** {eco_score}/100 Grade {eco_grade}\n"
            + f"**Daily tasks :** {daily_info.get('passed','?')}/{daily_info.get('total','?')} OK\n"
            + f"**Vault :** {total_mems} mémoires · {'✅' if report.get('vault_id') else '⚠️ hors ligne'}\n"
            + f"**Statut :** {report['status'].upper()}\n\n"
            + "*Notification vocale envoyée.*"
        )
        add_message(session_id, "assistant", cheat_text)
        return {
            "id":      f"chatcmpl-cheat-{int(time.time())}",
            "object":  "chat.completion",
            "model":   "cheat-code",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": cheat_text}, "finish_reason": "stop"}],
            "usage":   {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    # ── Shortcut IMAGE -> STL (image-to-3D) — déclenche la VRAIE mission forge
    #    au lieu de laisser JARVIS halluciner le pipeline. Une image jointe + une
    #    intention 3D/impression => mission image-to-3D réelle (Meshy -> STL),
    #    lancée via /v1/forge/mission (retour immédiat, run en arrière-plan). ──
    _last_user_imgs = None
    if req.messages:
        for _m in reversed(req.messages):
            if _m.role == "user" and _m.images:
                _last_user_imgs = _m.images
                break
    if _routing_on and _last_user_imgs and _STL_IMG_INTENT.search(last_user_msg):
        import os as _os
        import urllib.request as _ureq
        _img0 = _last_user_imgs[0]
        _data_uri = _img0 if _img0.startswith("data:") else f"data:image/png;base64,{_img0}"
        _auto_bambu = bool(re.search(r"\bbambu\b", last_user_msg, re.I))
        _prompt_txt = (last_user_msg.strip() or "image-to-3D model")[:300]
        _port = _os.getenv("BACKEND_PORT", "8000")
        _payload = json.dumps({"prompt": _prompt_txt, "image": _data_uri,
                               "auto_bambu": _auto_bambu}).encode()
        try:
            _rq = _ureq.Request(f"http://127.0.0.1:{_port}/v1/forge/mission",
                                data=_payload, method="POST",
                                headers={"Content-Type": "application/json"})
            with _ureq.urlopen(_rq, timeout=30) as _rsp:   # noqa: S310 - localhost self-call
                _fdata = json.loads(_rsp.read().decode())
            _mid = _fdata.get("mission_id")
        except Exception as _fe:
            _fdata, _mid = {"error": str(_fe)}, None
        if _mid:
            _LAST_FORGE_MISSION[session_id] = _mid   # pour les questions de statut
            _stl_text = (
                f"Mission STL image-to-3D lancee : #{_mid}.\n\n"
                "Meshy genere le modele 3D a partir de ton image (environ 2 a 3 "
                "minutes), puis reparation, orientation FDM et export STL. "
                + ("Bambu Studio s'ouvrira automatiquement a la fin. " if _auto_bambu else "")
                + "Le STL final arrive dans le dossier Jarvis/STL ; suis l'avancement "
                "reel dans le Pipeline Hub ou le Forge Hub. La generation tourne "
                "vraiment en arriere-plan (aucune simulation)."
            )
        else:
            _stl_text = ("Echec du lancement de la mission STL : "
                         f"{_fdata.get('detail') or _fdata.get('error') or 'reponse inattendue'}. "
                         "Verifie que le backend et Meshy sont operationnels.")
        add_message(session_id, "assistant", _stl_text)
        _stl_id = f"chatcmpl-stl-{int(time.time())}"
        if req.stream:
            return StreamingResponse(
                _stream_text(_stl_text, "stl-image-to-3d", _stl_id),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return {
            "id": _stl_id, "object": "chat.completion", "model": "stl-image-to-3d",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": _stl_text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    # ── Shortcut STATUT mission STL — "done?/fini?/c'est prêt?" sur une mission
    #    récente => on lit le VRAI statut forge au lieu de laisser le modèle
    #    halluciner ("Meshy still processing… I'll export…"). ──
    _sess_mid = _LAST_FORGE_MISSION.get(session_id)
    if (_routing_on and not _last_user_imgs and _sess_mid
            and len(last_user_msg.split()) <= 8
            and _STL_STATUS_INTENT.search(last_user_msg)):
        import os as _os2
        import urllib.request as _ureq2
        _port2 = _os2.getenv("BACKEND_PORT", "8000")
        try:
            with _ureq2.urlopen(  # noqa: S310 - localhost self-call
                f"http://127.0.0.1:{_port2}/v1/forge/mission/{_sess_mid}", timeout=15
            ) as _r2:
                _ms = json.loads(_r2.read().decode())
        except Exception as _se2:
            _ms = {"error": str(_se2)}
        _mst = _ms.get("status")
        if _mst == "completed":
            _ff = (_ms.get("files") or {}).get("jarvis_stl") or (_ms.get("files") or {}).get("final_stl") or ""
            _ffn = _ff.replace("\\", "/").split("/")[-1] if _ff else ""
            _sc = (_ms.get("report") or {}).get("printability_score")
            _status_text = ("Mission #" + str(_sess_mid) + " : TERMINEE. "
                            + (f"Fichier STL : {_ffn}. " if _ffn else "")
                            + (f"Imprimabilite {_sc}/100. " if _sc is not None else "")
                            + "Il est dans le dossier Jarvis/STL.")
        elif _mst in ("failed", "error"):
            _status_text = f"Mission #{_sess_mid} : ECHOUEE — {_ms.get('error', 'erreur inconnue')}."
        elif _mst:
            _pct = _ms.get("progress_pct", 0)
            _cstep = _ms.get("current_step", "?")
            _status_text = (f"Mission #{_sess_mid} : EN COURS — {_pct}% (etape : {_cstep}). "
                            "Je lis le vrai statut du pipeline forge (pas une simulation). "
                            "Redemande dans une minute.")
        else:
            _status_text = (f"Mission #{_sess_mid} introuvable (peut-etre purgee du cache). "
                            "Relance une generation si besoin.")
        add_message(session_id, "assistant", _status_text)
        _ssid = f"chatcmpl-stlstatus-{int(time.time())}"
        if req.stream:
            return StreamingResponse(
                _stream_text(_status_text, "stl-status", _ssid),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return {
            "id": _ssid, "object": "chat.completion", "model": "stl-status",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": _status_text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    # ── Pipelines : START ALL · DAILY RESEARCH · RAPPORT · STL ──
    from pipeline_runner import detect_pipeline, execute_pipeline
    from pipeline_runner import format_response as _fmt_pipe
    # skip_pipeline = appel interne (concept STL, plan Forge) → pas de routing,
    # sinon le message interne s'auto-déclenche en mission fantôme.
    _pipe = None if req.skip_pipeline else detect_pipeline(last_user_msg)
    if _pipe:
        import asyncio as _asyncio2
        _pipe_id, _pipe_arg = _pipe
        try:
            _result = _asyncio2.run(execute_pipeline(_pipe_id, _pipe_arg, voice=True))
        except Exception as _pe:
            _result = {"ok": False, "error": str(_pe)}
        _pipe_text = _fmt_pipe(_pipe_id, _result)
        add_message(session_id, "assistant", _pipe_text)
        return {
            "id":      f"chatcmpl-pipe-{int(time.time())}",
            "object":  "chat.completion",
            "model":   f"pipeline:{_pipe_id}",
            "created": int(time.time()),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": _pipe_text}, "finish_reason": "stop"}],
            "usage":   {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    # ─────────────────────────────────────────────────────────

    ollama_available = is_ollama_available()

    # Si le JSON spécifie un modèle Ollama → forcer Ollama
    if req.model and ("qwen" in req.model or "llama" in req.model or "deepseek" in req.model):
        use_claude = False
    # Si le JSON spécifie un modèle Claude → forcer Claude
    elif req.model and "claude" in req.model:
        use_claude = True
    else:
        use_claude = should_use_claude(last_user_msg) or not ollama_available

    # Vision override — only Claude (haiku 4.5 / sonnet 4.6) can SEE images.
    # qwen3 / deepseek are text-only, so a multimodal message MUST go to Claude.
    if _has_images(anthropic_messages):
        use_claude = True

    facts      = load_facts()
    system     = build_system_prompt(req.system or _build_base_system(), facts)  # relit config.json à chaque requête (TTL 30s)

    # ── Session continuity — inject résumé si nouvelle session ──
    _sc_cfg = load_config().get("session_continuity", {})
    if _was_new_session and _sc_cfg.get("inject_on_new_session", True):
        _prev_summary = get_last_session_summary(session_id)
        if _prev_summary:
            system = (
                "━━━ REPRISE DE SESSION ━━━\n"
                + _prev_summary
                + "\n━━━ FIN DU RÉSUMÉ — continue naturellement ━━━\n\n"
            ) + system

    # ── Memory compression — déclenche si seuil atteint ─────────
    # Off the request's critical path: a long session would otherwise block the
    # reply for up to 10s on a synchronous qwen3:14b summarization. The summary
    # only matters for the NEXT message, so run it fire-and-forget in a thread.
    # (The current request already captured anthropic_messages, so the in-place
    # session rewrite can't race it.)
    threading.Thread(
        target=compress_session_sync, args=(session_id,), daemon=True
    ).start()

    # Rappel langue injecté à la fin du system prompt — modèles suivent mieux la dernière instruction
    # Lu depuis config.json (cache TTL 30s) — jamais hardcodé
    _chat_lang = load_config().get("jarvis", {}).get("language", "Français")
    system += (
        f"\n\n[LANGUE] Par défaut réponds en {_chat_lang}. MAIS si l'utilisateur écrit dans "
        f"une autre langue OU demande explicitement une langue (ex: « réponds en anglais », "
        f"« in English »), réponds ENTIÈREMENT dans CETTE langue — cette consigne prime sur "
        f"toute règle « toujours en {_chat_lang} ». 1 à 2 phrases max sauf si détail demandé. "
        f"Texte brut — pas de markdown, pas de listes, pas de titres. ZERO emoji — jamais."
    )

    # ── Skills catalog — injection compacte dans le system prompt ───────────
    try:
        _skill_cat = _skill_catalog_text()
        if _skill_cat:
            system += f"\n\n{_skill_cat}"
    except Exception:
        pass

    # ── Brain/Vault contextuel (option 2 — triggers: long / complexe / debug) ──
    memory_meta = {"retrieved": False, "fragments": 0, "ms": 0, "confidence": 0}
    if _needs_memory(last_user_msg):
        import asyncio as _aio_mem
        import time as _t_mem
        _m0 = _t_mem.perf_counter()
        try:
            from vault.memory_manager import vault_query
            _hits = _aio_mem.run(vault_query(last_user_msg))[:5]
        except Exception:
            _hits = []
        if _hits:
            system += "\n\n[Memory Retrieved — brain & vault]\n" + "\n".join(
                f"- [{h.get('collection','?')}] {h['text'][:160]}" for h in _hits
            )
            _top = max((h.get("score", 0) for h in _hits), default=0)
            memory_meta = {
                "retrieved":  True,
                "fragments":  len(_hits),
                "ms":         round((_t_mem.perf_counter() - _m0) * 1000),
                "confidence": round(max(0.0, min(1.0, _top)) * 100),
            }

    req_id     = f"chatcmpl-{int(time.time())}"
    text       = ""
    model_used = ""

    # ── Ollama (gratuit) ─────────────────────────────────
    if not use_claude and ollama_available:
        print("[chat] OLLAMA — gratuit")
        _budget["appels_ollama"] += 1
        budget_tracker.record_ollama_call()
        model_used  = OLLAMA_MODEL
        # Docker context injection for Ollama (no native tool_use in Ollama)
        # Fetched once, injected in BOTH system prompt AND user message for maximum compliance
        _ollama_sys    = system
        _docker_block  = ""
        if _needs_docker:
            try:
                _docker_block = _docker_quick_status()
                _ollama_sys += (
                    "\n\n[DONNEES DOCKER EN TEMPS REEL]\n"
                    + _docker_block
                    + "\n\nUtilise ces donnees reelles pour repondre. "
                    "Ne dis jamais 'exécutez docker ps'. Ne dis jamais 'je ne peux pas acceder'. "
                    "Les donnees sont ici, utilise-les."
                )
            except Exception as _de:
                print(f"[docker] quick_status_text error: {_de}")

        # Pour Ollama : rappel aussi dans le dernier message utilisateur
        ollama_msgs_raw = [{"role": "system", "content": _ollama_sys}] + anthropic_messages
        # Ajoute le rappel langue + brièveté en fin de message user (Ollama suit mieux la dernière instruction)
        ollama_msgs = []
        for i, msg in enumerate(ollama_msgs_raw):
            if i == len(ollama_msgs_raw) - 1 and msg["role"] == "user":
                _tail = (f"[Langue: {_chat_lang} par défaut, MAIS si l'utilisateur demande ou "
                         f"écrit dans une autre langue (ex: anglais), réponds dans CETTE langue. "
                         f"MAX 2 phrases courtes. Texte brut, zéro markdown/liste/titre, ZERO emoji.]")
                # Si Docker requis : injecte les données directement dans le message user
                if _needs_docker and _docker_block:
                    _docker_inject = (
                        f"\n\n[Données Docker réelles]\n{_docker_block}\n"
                        "Réponds en utilisant ces données. Ne suggère jamais d'exécuter une commande."
                    )
                    ollama_msgs.append({"role": "user", "content": msg["content"] + _docker_inject + f"\n\n{_tail}"})
                else:
                    ollama_msgs.append({"role": "user", "content": msg["content"] + f"\n\n{_tail}"})
            else:
                ollama_msgs.append(msg)

        # ── Real streaming path — tokens arrive live, no 60s freeze ──────
        if req.stream:
            def _ollama_real_stream():
                full_text = ""
                _rid = req_id
                _mid = model_used
                _mem = memory_meta
                _sid = session_id
                # opening delta (role)
                yield _sse({
                    "id": _rid, "object": "chat.completion.chunk",
                    "model": _mid,
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}],
                })
                for _chunk in stream_ollama_chat(ollama_msgs, OLLAMA_MODEL):
                    full_text += _chunk
                    yield _sse({
                        "id": _rid, "object": "chat.completion.chunk",
                        "model": _mid,
                        "choices": [{"index": 0, "delta": {"content": _chunk}, "finish_reason": None}],
                    })
                # Fallback si Ollama retourne rien (crash / think-only / timeout)
                if not full_text.strip():
                    full_text = "Réponds à cette question." if False else (
                        ask_ollama_chat(
                            [{"role": "user", "content": last_user_msg}],
                            OLLAMA_MODEL,
                        ) or ""
                    )
                    if full_text:
                        full_text = strip_think_tags(full_text)
                        yield _sse({
                            "id": _rid, "object": "chat.completion.chunk",
                            "model": _mid,
                            "choices": [{"index": 0, "delta": {"content": full_text}, "finish_reason": None}],
                        })
                    else:
                        full_text = "Modele local indisponible. Relance Ollama ou utilise !claude."
                        yield _sse({
                            "id": _rid, "object": "chat.completion.chunk",
                            "model": _mid,
                            "choices": [{"index": 0, "delta": {"content": full_text}, "finish_reason": None}],
                        })
                # final chunk + [DONE]
                _final = {
                    "id": _rid, "object": "chat.completion.chunk",
                    "model": _mid,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                if _mem:
                    _final["memory"] = _mem
                yield _sse(_final)
                yield "data: [DONE]\n\n"
                # Persist to session after stream completes
                if full_text:
                    add_message(_sid, "assistant", full_text)
                    print(f"[chat] ollama-stream modèle={_mid} '{full_text[:50]}...'")
                else:
                    print("[chat] ollama-stream — pas de réponse")

            return StreamingResponse(
                _ollama_real_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control":     "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection":        "keep-alive",
                },
            )

        # ── Non-streaming path — collect full response, strip think tags ─
        text = ask_ollama_chat(ollama_msgs, OLLAMA_MODEL)
        if text:
            text = strip_think_tags(text)  # Remove <think>...</think> from qwen3/deepseek-r1
        if not text:
            use_claude = True

    # ── Claude (payant) ──────────────────────────────────
    if use_claude or not text:
        if not _budget_ok():
            text       = (
                f"🛑 Budget ${BUDGET_MAX_USD} atteint "
                f"(${_budget['cout_usd']:.3f} dépensé). "
                "Redémarre le backend pour continuer."
            )
            model_used = "bloqué"
        else:
            _auto_model = get_claude_model(last_user_msg, CLAUDE_MODEL, CLAUDE_MODEL_GROS)
            model_used  = (req.model if req.model and req.model.strip() else _auto_model)
            _tag = "SONNET" if model_used == CLAUDE_MODEL_GROS else "HAIKU"
            print(f"[chat] CLAUDE {_tag} — routing auto")
            try:
                # Tool gating — only attach the tools the message actually needs.
                # Trivial messages ("Status?") get NO tools → no pointless tool
                # round-trips, Haiku answers directly in one streamed call.
                _docker_tools = _DOCKER_TOOL_DEFS if _needs_docker else []
                # Skill tools only when the message actually references a skill /
                # compétence concept — NOT on a bare generic verb ("use", "do",
                # "fais"), which used to let a casual question ("should I use a
                # queue for the STL batch jobs?") fire a real pipeline skill.
                _skill_tools  = _SKILL_TOOL_DEFS if _SKILL_LIST_KW.search(last_user_msg) else []
                _brain_tools  = _BRAIN_TOOL_DEFS if _needs_memory(last_user_msg) else []
                _stl_tools    = _STL_TOOL_DEFS if _STL_KW.search(last_user_msg) else []
                # Appel interne (skip_pipeline) → aucun outil : completion pure.
                _all_tools    = [] if not _routing_on else (_docker_tools + _skill_tools + _brain_tools + _stl_tools)

                # Real streaming — the frontend always sends stream=True. Stream
                # tokens live instead of blocking then replaying via _stream_text.
                if req.stream:
                    return StreamingResponse(
                        _claude_stream_gen(
                            model_used, system, anthropic_messages, _all_tools,
                            req.max_tokens, req.temperature, session_id, req_id,
                            memory_meta,
                        ),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control":     "no-cache",
                            "X-Accel-Buffering": "no",
                            "Connection":        "keep-alive",
                        },
                    )

                _tool_msgs    = list(anthropic_messages)  # working copy (non-stream)
                _total_in, _total_out = 0, 0

                while True:
                    _create_kw = dict(
                        model=model_used,
                        max_tokens=req.max_tokens,
                        temperature=req.temperature,
                        system=system,
                        messages=_tool_msgs,
                    )
                    if _all_tools:
                        _create_kw["tools"] = _all_tools

                    resp = claude.messages.create(**_create_kw)
                    _total_in  += resp.usage.input_tokens
                    _total_out += resp.usage.output_tokens

                    if resp.stop_reason == "tool_use":
                        # Execute each tool call and collect results
                        _tool_results = []
                        for _blk in resp.content:
                            if getattr(_blk, "type", None) == "tool_use":
                                _tname = _blk.name
                                print(f"[tool] calling {_tname} {_blk.input}")
                                if _tname.startswith("skill_"):
                                    _res_str = _skill_dispatch(_tname, _blk.input)
                                elif _tname.startswith("brain_"):
                                    _res_str = _brain_dispatch(_tname, _blk.input)
                                elif _tname.startswith("stl_"):
                                    _res_str = _stl_dispatch(_tname, _blk.input)
                                else:
                                    _res_str = _docker_dispatch(_tname, _blk.input)
                                _tool_results.append({
                                    "type":        "tool_result",
                                    "tool_use_id": _blk.id,
                                    "content":     _res_str,
                                })
                        # Append assistant turn + tool results for next loop
                        _tool_msgs.append({"role": "assistant", "content": resp.content})
                        _tool_msgs.append({"role": "user",      "content": _tool_results})
                    else:
                        text = "".join(
                            b.text for b in resp.content
                            if getattr(b, "type", None) == "text"
                        )
                        break

                _enregistrer_cout(
                    _total_in + _total_out,
                    model_used,
                    input_tokens=_total_in,
                    output_tokens=_total_out,
                )
            except APIError as e:
                _sc  = getattr(e, "status_code", 502)
                _msg = str(e)
                # ── Crédit Anthropic épuisé → fallback Ollama + message clair ──
                _is_credit = "credit balance" in _msg.lower() or "insufficient" in _msg.lower()
                if _is_credit:
                    print("[claude] Crédit épuisé — fallback Ollama")
                    model_used = OLLAMA_MODEL
                    if ollama_available:
                        _fb_msgs = [{"role": "system", "content": system}] + anthropic_messages
                        text = ask_ollama_chat(_fb_msgs, OLLAMA_MODEL)
                        if text:
                            text = strip_think_tags(text)
                    if not text:
                        text = (
                            "⚠️ **Crédits Anthropic épuisés.** Je bascule sur Ollama local.\n"
                            "Recharge les crédits sur https://console.anthropic.com/settings/billing\n"
                            "En attendant, je fonctionne en mode Ollama (qwen3:14b)."
                        )
                    # Mark account as credit-exhausted to skip future Claude calls this session
                    _budget["cout_usd"] = BUDGET_MAX_USD + 1.0
                elif _sc in (400, 422):
                    # Bad request — log but return friendly message instead of crashing
                    print(f"[claude] 400/422 APIError: {_msg[:200]}")
                    text = f"⚠️ Erreur API Claude ({_sc}). Basculement sur Ollama..."
                    if ollama_available:
                        _fb_msgs = [{"role": "system", "content": system}] + anthropic_messages
                        _fb_text = ask_ollama_chat(_fb_msgs, OLLAMA_MODEL)
                        if _fb_text:
                            text = strip_think_tags(_fb_text)
                            model_used = OLLAMA_MODEL
                else:
                    raise HTTPException(_sc, detail=_msg)
            except Exception as e:
                raise HTTPException(500, detail=str(e))

    if not text:
        text = "Désolé David, je n'ai pas pu générer de réponse. Réessaie."

    text = _strip_decorations(text)  # no emoji/symbols (TTS + plain-text persona)
    print(f"[chat] modèle={model_used} '{text[:50]}...'")
    add_message(session_id, "assistant", text)

    if req.stream:
        return StreamingResponse(
            _stream_text(text, model_used, req_id, memory=memory_meta),
            media_type="text/event-stream",
            headers={
                "Cache-Control":     "no-cache",
                "X-Accel-Buffering": "no",
                "Connection":        "keep-alive",
            },
        )

    return {
        "id":      req_id,
        "object":  "chat.completion",
        "model":   model_used,
        "created": int(time.time()),
        "memory": memory_meta,
        "choices": [{
            "index":         0,
            "message":       {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "total_tokens":      0,
        },
    }

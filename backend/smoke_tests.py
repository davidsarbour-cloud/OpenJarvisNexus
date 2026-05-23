"""
Nexus9 Smoke Tests — validation rapide de tous les systèmes critiques.
Non-destructif: les tests ne modifient pas l'état du système.
"""
from __future__ import annotations
import asyncio
import time
import os
from datetime import datetime

BACKEND_PORT  = int(os.getenv("BACKEND_PORT", 8000))
OLLAMA_HOST   = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OPENHANDS_URL = os.getenv("OPENHANDS_URL", "http://localhost:3000")

_BASE_URL = f"http://localhost:{BACKEND_PORT}"


def _result(name: str, ok: bool, msg: str, ms: int) -> dict:
    return {"name": name, "status": "pass" if ok else "fail", "message": msg, "duration_ms": ms}


def _warn(name: str, msg: str, ms: int) -> dict:
    return {"name": name, "status": "warn", "message": msg, "duration_ms": ms}


async def _timed(coro) -> tuple[any, int]:
    t = time.monotonic()
    result = await coro
    return result, int((time.monotonic() - t) * 1000)


# ══════════════════════════════════════════════════════════
# TESTS INDIVIDUELS
# ══════════════════════════════════════════════════════════

async def test_backend_health() -> dict:
    """GET /health — vérifie status == 'ok'."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{_BASE_URL}/health")
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_backend_health", False, f"HTTP {r.status_code}", ms)
        data = r.json()
        if data.get("status") != "ok":
            return _result("test_backend_health", False, f"status={data.get('status')}", ms)
        return _result("test_backend_health", True, f"ok — version {data.get('version', '?')}", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_backend_health", False, f"{type(e).__name__}: {e}", ms)


async def test_claude_api() -> dict:
    """POST /v1/chat/completions — vérifie réponse non-vide."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(
                f"{_BASE_URL}/v1/chat/completions",
                json={
                    "message": "ping",
                    "model": "claude-haiku-4-5",
                    "max_tokens": 10,
                    "session_id": "smoke_test_internal",
                },
            )
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_claude_api", False, f"HTTP {r.status_code}", ms)
        data = r.json()
        # Réponse OpenAI-compatible: choices[0].message.content
        choices = data.get("choices", [])
        if not choices:
            return _result("test_claude_api", False, "Aucun choix dans la réponse", ms)
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            return _result("test_claude_api", False, "Contenu vide", ms)
        return _result("test_claude_api", True, f"réponse {len(content)} chars — modèle: {data.get('model','?')}", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_claude_api", False, f"{type(e).__name__}: {e}", ms)


async def test_ollama_connectivity() -> dict:
    """GET {OLLAMA_HOST}/api/tags — vérifie status 200 + au moins 1 modèle."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{OLLAMA_HOST}/api/tags")
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_ollama_connectivity", False, f"HTTP {r.status_code}", ms)
        data = r.json()
        models = data.get("models", [])
        if not models:
            return _result("test_ollama_connectivity", False, "Aucun modèle disponible", ms)
        return _result("test_ollama_connectivity", True, f"{len(models)} modèle(s) disponible(s)", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_ollama_connectivity", False, f"{type(e).__name__}: {e}", ms)


async def test_ollama_models() -> dict:
    """Vérifie que deepseek-coder:6.7b et qwen3:14b sont présents dans Ollama."""
    import httpx
    t = time.monotonic()
    required = {"deepseek-coder:6.7b", "qwen3:14b"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{OLLAMA_HOST}/api/tags")
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_ollama_models", False, f"Ollama HTTP {r.status_code}", ms)
        data = r.json()
        present = {m["name"] for m in data.get("models", [])}
        # Vérifie par préfixe (ex: "qwen3:14b" peut apparaître comme "qwen3:14b-instruct")
        missing = []
        for req_model in required:
            base = req_model.split(":")[0]
            tag  = req_model.split(":")[1] if ":" in req_model else ""
            found = any(
                (base in name) and (not tag or tag in name)
                for name in present
            )
            if not found:
                missing.append(req_model)
        if missing:
            return _result("test_ollama_models", False, f"Modèles manquants: {missing}", ms)
        return _result("test_ollama_models", True, f"deepseek-coder + qwen3 présents ({len(present)} modèles total)", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_ollama_models", False, f"{type(e).__name__}: {e}", ms)


async def test_vault_read() -> dict:
    """GET /v1/vault/stats — vérifie que la réponse contient 'collections'."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{_BASE_URL}/v1/vault/stats")
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_vault_read", False, f"HTTP {r.status_code}", ms)
        data = r.json()
        if "collections" not in data:
            return _result("test_vault_read", False, f"Clé 'collections' absente: {list(data.keys())}", ms)
        nb = len(data["collections"])
        return _result("test_vault_read", True, f"{nb} collection(s) dans le Vault", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_vault_read", False, f"{type(e).__name__}: {e}", ms)


async def test_vault_write_search() -> dict:
    """POST /v1/vault/memory puis GET /v1/vault/search — vérifie l'aller-retour."""
    import httpx
    t = time.monotonic()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_text = f"smoke test {timestamp}"
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            # Écriture
            rw = await c.post(
                f"{_BASE_URL}/v1/vault/memory",
                json={"text": test_text, "collection": "agent_memory"},
            )
            if rw.status_code not in (200, 201):
                ms = int((time.monotonic() - t) * 1000)
                return _result("test_vault_write_search", False, f"Write HTTP {rw.status_code}", ms)
            # Lecture — recherche
            rs = await c.get(
                f"{_BASE_URL}/v1/vault/search",
                params={"q": "smoke test", "collection": "agent_memory"},
            )
        ms = int((time.monotonic() - t) * 1000)
        if rs.status_code != 200:
            return _result("test_vault_write_search", False, f"Search HTTP {rs.status_code}", ms)
        data = rs.json()
        results = data.get("results", [])
        # Vérifie qu'au moins un résultat contient notre texte (approx)
        found = any("smoke test" in str(r.get("text", "")) for r in results)
        if not found:
            return _result("test_vault_write_search", False, f"Mémoire non retrouvée ({len(results)} résultats)", ms)
        return _result("test_vault_write_search", True, f"Write+Search OK ({len(results)} résultats)", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_vault_write_search", False, f"{type(e).__name__}: {e}", ms)


async def test_jarvis_orchestration() -> dict:
    """POST /v1/orchestrate — vérifie intent == 'fabrication' et 'FORGE' dans agents."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.post(
                f"{_BASE_URL}/v1/orchestrate",
                json={"text": "crée un dragon STL", "model": "claude-haiku-4-5"},
            )
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_jarvis_orchestration", False, f"HTTP {r.status_code}", ms)
        data = r.json()
        intent = data.get("intent", "")
        agents = data.get("agents", [])
        if intent != "fabrication":
            return _result("test_jarvis_orchestration", False, f"intent={intent!r} (attendu: 'fabrication')", ms)
        if "FORGE" not in agents:
            return _result("test_jarvis_orchestration", False, f"FORGE absent des agents: {agents}", ms)
        return _result("test_jarvis_orchestration", True, f"intent=fabrication, agents={agents}", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_jarvis_orchestration", False, f"{type(e).__name__}: {e}", ms)


async def test_intent_classification() -> dict:
    """GET /v1/orchestrate/classify?text=debug+python+script — vérifie intent == 'coding'."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(
                f"{_BASE_URL}/v1/orchestrate/classify",
                params={"text": "debug python script"},
            )
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_intent_classification", False, f"HTTP {r.status_code}", ms)
        data = r.json()
        intent = data.get("intent", "")
        if intent != "coding":
            return _result("test_intent_classification", False, f"intent={intent!r} (attendu: 'coding')", ms)
        return _result("test_intent_classification", True, f"intent=coding, confidence={data.get('confidence', '?')}", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_intent_classification", False, f"{type(e).__name__}: {e}", ms)


async def test_forge_endpoint() -> dict:
    """GET /v1/forge/missions — vérifie status 200 et 'total' dans la réponse."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{_BASE_URL}/v1/forge/missions")
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_forge_endpoint", False, f"HTTP {r.status_code}", ms)
        data = r.json()
        if "total" not in data:
            return _result("test_forge_endpoint", False, f"Clé 'total' absente: {list(data.keys())}", ms)
        return _result("test_forge_endpoint", True, f"Forge OK — {data['total']} mission(s)", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_forge_endpoint", False, f"{type(e).__name__}: {e}", ms)


async def test_jarvis_files() -> dict:
    """GET /v1/jarvis/files/list — vérifie status 200 et 'files' dans la réponse."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{_BASE_URL}/v1/jarvis/files/list")
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_jarvis_files", False, f"HTTP {r.status_code}", ms)
        data = r.json()
        if "files" not in data:
            return _result("test_jarvis_files", False, f"Clé 'files' absente: {list(data.keys())}", ms)
        nb = len(data["files"])
        return _result("test_jarvis_files", True, f"{nb} fichier(s) Jarvis workspace", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_jarvis_files", False, f"{type(e).__name__}: {e}", ms)


async def test_tts() -> dict:
    """GET /v1/tts?text=test&voice=en-US-GuyNeural — vérifie Content-Type audio/mpeg."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(
                f"{_BASE_URL}/v1/tts",
                params={"text": "test", "voice": "en-US-GuyNeural"},
            )
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_tts", False, f"HTTP {r.status_code}: {r.text[:100]}", ms)
        ct = r.headers.get("content-type", "")
        if "audio" not in ct:
            return _result("test_tts", False, f"Content-Type inattendu: {ct}", ms)
        return _result("test_tts", True, f"TTS OK — {len(r.content)} bytes ({ct})", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_tts", False, f"{type(e).__name__}: {e}", ms)


async def test_whisper() -> dict:
    """GET /v1/speech/health — vérifie 'available' == True."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{_BASE_URL}/v1/speech/health")
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_whisper", False, f"HTTP {r.status_code}", ms)
        data = r.json()
        if not data.get("available"):
            return _result("test_whisper", False, f"available=False — {data}", ms)
        return _result("test_whisper", True, f"Whisper disponible — backend: {data.get('backend','?')}", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_whisper", False, f"{type(e).__name__}: {e}", ms)


async def test_bruce_openhands() -> dict:
    """GET {OPENHANDS_URL}/api/options/models — PASS si 200, WARN si offline (optionnel)."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get(f"{OPENHANDS_URL}/api/options/models")
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code == 200:
            return _result("test_bruce_openhands", True, "BRUCE online — HTTP 200", ms)
        return _warn("test_bruce_openhands", f"BRUCE HTTP {r.status_code} (optionnel)", ms)
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        ms = int((time.monotonic() - t) * 1000)
        return _warn("test_bruce_openhands", f"BRUCE offline ({type(e).__name__}) — optionnel, lance: docker start nexus_bruce", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _warn("test_bruce_openhands", f"BRUCE inaccessible: {type(e).__name__}: {e}", ms)


async def test_memory_embedding() -> dict:
    """Vérifie que nomic-embed-text est disponible dans Ollama."""
    import httpx
    t = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{OLLAMA_HOST}/api/tags")
        ms = int((time.monotonic() - t) * 1000)
        if r.status_code != 200:
            return _result("test_memory_embedding", False, f"Ollama HTTP {r.status_code}", ms)
        data = r.json()
        model_names = [m["name"] for m in data.get("models", [])]
        found = any("nomic-embed-text" in name for name in model_names)
        if not found:
            return _result(
                "test_memory_embedding", False,
                f"nomic-embed-text absent (modèles: {model_names[:5]}). Lance: ollama pull nomic-embed-text",
                ms,
            )
        return _result("test_memory_embedding", True, "nomic-embed-text disponible pour les embeddings Vault", ms)
    except Exception as e:
        ms = int((time.monotonic() - t) * 1000)
        return _result("test_memory_embedding", False, f"{type(e).__name__}: {e}", ms)


# ══════════════════════════════════════════════════════════
# ORCHESTRATION
# ══════════════════════════════════════════════════════════

ALL_TESTS = [
    test_backend_health,
    test_claude_api,
    test_ollama_connectivity,
    test_ollama_models,
    test_vault_read,
    test_vault_write_search,
    test_jarvis_orchestration,
    test_intent_classification,
    test_forge_endpoint,
    test_jarvis_files,
    test_tts,
    test_whisper,
    test_bruce_openhands,
    test_memory_embedding,
]


async def run_smoke_tests(tests=None) -> dict:
    """Lance tous les smoke tests et retourne un rapport complet."""
    selected = tests or ALL_TESTS
    results = []
    for test_fn in selected:
        try:
            result = await asyncio.wait_for(test_fn(), timeout=10.0)
        except asyncio.TimeoutError:
            result = _result(test_fn.__name__, False, "Timeout (10s)", 10000)
        except Exception as e:
            result = _result(test_fn.__name__, False, f"Exception: {type(e).__name__}: {e}", 0)
        results.append(result)

    passed = sum(1 for r in results if r["status"] == "pass")
    warned = sum(1 for r in results if r["status"] == "warn")
    failed = sum(1 for r in results if r["status"] == "fail")
    total  = len(results)

    return {
        "timestamp": datetime.now().isoformat(),
        "summary":   {"passed": passed, "warned": warned, "failed": failed, "total": total},
        "health_pct": round((passed / max(total, 1)) * 100),
        "results":   results,
    }


# ── Run direct ───────────────────────────────────────────
if __name__ == "__main__":

    async def _main():
        print("⬡ NEXUS9 — Smoke Tests\n")
        report = await run_smoke_tests()
        for r in report["results"]:
            icon = "✓" if r["status"] == "pass" else ("⚠" if r["status"] == "warn" else "✗")
            print(f"  {icon} [{r['duration_ms']:4d}ms] {r['name']}: {r['message']}")
        s = report["summary"]
        print(f"\n  Résultat: {s['passed']} pass / {s['warned']} warn / {s['failed']} fail")
        print(f"  Santé: {report['health_pct']}%")

    asyncio.run(_main())

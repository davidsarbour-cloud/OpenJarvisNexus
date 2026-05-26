"""
Model health check — tests all 4 Ollama models.
Run: python _check_models.py
"""
import re
import sys
import time

import httpx

OLLAMA = "http://127.0.0.1:11434"

MODELS = [
    ("qwen3:14b",           "JARVIS / QWEN / BRUCE",  "chat"),
    ("deepseek-coder:6.7b", "CORTANA",                "chat"),
    ("deepseek-r1:7b",      "NOVA",                   "chat"),
    ("nomic-embed-text",    "VAULT (embed)",           "embed"),
]

RESULTS = []

print("\n" + "="*65)
print("  NEXUS9 — MODEL HEALTH CHECK")
print("="*65)

# ── 1. Ollama ping ────────────────────────────────────────────────
try:
    r = httpx.get(f"{OLLAMA}/api/tags", timeout=5)
    installed = [m["name"] for m in r.json().get("models", [])]
    print(f"\n  Ollama : ONLINE  ({len(installed)} models installed)")
    for m in installed:
        sz = next((x["size"] for x in r.json()["models"] if x["name"]==m), 0)
        print(f"    • {m:<30} {sz//1024//1024//1024:.1f} GB" if sz > 1e9
              else f"    • {m:<30} {sz//1024//1024} MB")
except Exception as e:
    print(f"\n  Ollama : OFFLINE — {e}")
    sys.exit(1)

# ── 2. Per-model test ─────────────────────────────────────────────
print("\n" + "-"*65)
print("  INDIVIDUAL MODEL TESTS")
print("-"*65)

for model, agent, kind in MODELS:
    t0 = time.perf_counter()
    try:
        if kind == "embed":
            r = httpx.post(f"{OLLAMA}/api/embeddings",
                json={"model": model, "prompt": "nexus9 health check"},
                timeout=30)
            vec = r.json().get("embedding", [])
            ms = int((time.perf_counter() - t0) * 1000)
            if vec:
                status = "OK"
                detail = f"dim={len(vec)}  first3=[{vec[0]:.4f}, {vec[1]:.4f}, {vec[2]:.4f}]"
                icon = "[OK]"
            else:
                status = "FAIL"
                detail = "empty embedding"
                icon = "[!!]"

        else:  # chat
            r = httpx.post(f"{OLLAMA}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with exactly one word: ONLINE"}],
                    "stream": False,
                    "options": {"num_predict": 80, "temperature": 0, "num_ctx": 512},
                },
                timeout=120)
            data = r.json()
            raw = data.get("message", {}).get("content", "")
            # strip <think>...</think> blocks (deepseek-r1 / qwen3)
            clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            tokens = data.get("eval_count", 0)
            ms = int((time.perf_counter() - t0) * 1000)

            if clean:
                status = "OK"
                detail = f'reply=[{clean[:50]}]  tokens={tokens}'
                icon = "[OK]"
            elif tokens > 0:
                # Model generated tokens but only thinking — still functional
                status = "OK (think-only)"
                detail = f"think-mode active, {tokens} tokens generated, no visible output"
                icon = "[OK]"
            else:
                status = "FAIL"
                detail = "no response"
                icon = "[!!]"

        RESULTS.append((icon, model, agent, status, ms))
        print(f"\n  {icon} {model}")
        print(f"       Agent  : {agent}")
        print(f"       Status : {status}")
        print(f"       Detail : {detail}")
        print(f"       Time   : {ms}ms")

    except httpx.TimeoutException:
        ms = int((time.perf_counter() - t0) * 1000)
        RESULTS.append(("[!!]", model, agent, "TIMEOUT", ms))
        print(f"\n  [!!] {model}")
        print(f"       Agent  : {agent}")
        print(f"       Status : TIMEOUT after {ms}ms")

    except Exception as e:
        ms = int((time.perf_counter() - t0) * 1000)
        RESULTS.append(("[!!]", model, agent, f"ERROR: {e}", ms))
        print(f"\n  [!!] {model}")
        print(f"       Agent  : {agent}")
        print(f"       Status : ERROR — {e}")

# ── 3. Summary ────────────────────────────────────────────────────
print("\n" + "="*65)
ok  = sum(1 for r in RESULTS if r[0] == "[OK]")
fail = len(RESULTS) - ok
print(f"  SUMMARY : {ok}/{len(RESULTS)} models operational  |  {fail} issues")
print("="*65)
for icon, model, agent, status, ms in RESULTS:
    print(f"  {icon}  {model:<28} {agent:<22} {ms}ms")
print("="*65 + "\n")

if fail > 0:
    sys.exit(1)

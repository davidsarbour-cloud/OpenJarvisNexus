# smoke_test.py — Test complet NexusX9
import requests, json, time, sys
from datetime import datetime

BASE = "http://localhost:8000"
OLLAMA = "http://localhost:11434"

print("\n" + "="*50)
print(f"  NEXUSX9 SMOKE TESTS — {datetime.now().strftime('%H:%M:%S')}")
print("="*50 + "\n")

passed = 0
failed = 0

def test(name, method, url, body=None, expected=200):
    global passed, failed
    try:
        if method == "GET":
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, json=body, timeout=30)

        ok = r.status_code == expected or r.status_code < 300
        icon = "✅" if ok else "❌"
        print(f"{icon} {name:<35} → {r.status_code}")

        if ok: passed += 1
        else:  failed += 1

        return ok, r
    except Exception as e:
        print(f"❌ {name:<35} → OFFLINE ({str(e)[:40]})")
        failed += 1
        return False, None

print("── BACKEND PYTHON ──────────────────────────")
test("Backend Health",       "GET",  f"{BASE}/health")
test("Agents List",          "GET",  f"{BASE}/v1/agents")
test("Memory System",        "GET",  f"{BASE}/v1/memory")
test("Chat Jarvis",          "POST", f"{BASE}/v1/chat/completions",
     {"message": "ping test", "stream": False})

print("\n── OLLAMA GPU ──────────────────────────────")
ok, r = test("Ollama API",   "GET",  f"{OLLAMA}/api/tags")
if ok and r:
    data = r.json()
    models = data.get("models", [])
    print(f"   📦 Modèles installés: {len(models)}")
    for m in models:
        print(f"      → {m['name']} ({round(m.get('size',0)/(1024**3),1)}GB)")

ok, r = test("Modèles actifs","GET", f"{OLLAMA}/api/ps")
if ok and r:
    active = r.json().get("models", [])
    if active:
        m = active[0]
        vram = round(m.get('size_vram',0)/(1024**3),1)
        print(f"   ⚡ GPU CUDA actif: {m['name']} ({vram}GB VRAM)")
    else:
        print("   💤 Aucun modèle en mémoire (normal)")

print("\n── FRONTEND ────────────────────────────────")
test("NexusX9 UI",           "GET",  "http://localhost:3000")

print("\n" + "="*50)
print(f"  RÉSULTATS: {passed} ✅  |  {failed} ❌")
print("="*50 + "\n")

if failed > 0:
    print("⚠️  Corrige les erreurs avant de continuer\n")
    sys.exit(1)
else:
    print("🚀 Tout tourne — Ready to build!\n")
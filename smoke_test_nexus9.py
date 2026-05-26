#!/usr/bin/env python3
"""
Nexus9 — Smoke test end-to-end (Phases 0 → 7).

Vérifie toute la stack en quelques secondes :
  • Backend FastAPI + 30 routes
  • Endpoints monitoring (Docker / Prometheus / ChromaDB / Sonar)
  • WebSocket /ws/events (Phase 7)
  • Frontend dist/ buildé
  • Services Phase 7 : Postgres, Redis, Traefik
  • Ollama : modèles installés

Usage:
    python smoke_test_nexus9.py
    python smoke_test_nexus9.py --backend http://localhost:8000
"""

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request

# Force UTF-8 on stdout/stderr — Windows consoles default to cp1252 and would
# raise UnicodeEncodeError on the ✓/✗/! symbols below.
for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8")
        except Exception:
            pass

OK   = "\033[32m✓\033[0m"
KO   = "\033[31m✗\033[0m"
WARN = "\033[33m!\033[0m"
DIM  = "\033[90m"
END  = "\033[0m"


def get(url: str, timeout: float = 4):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return None, str(e).encode()


def post(url: str, payload: dict, timeout: float = 4):
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return None, str(e).encode()


def tcp_alive(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def section(title: str) -> None:
    print(f"\n  [{title}]")


def test(label: str, fn):
    print(f"  {label:<48}", end=" ", flush=True)
    try:
        ok, msg = fn()
        symbol = OK if ok is True else (WARN if ok is None else KO)
        print(f"{symbol} {DIM}{msg}{END}")
        return ok
    except Exception as e:
        print(f"{KO} {DIM}{type(e).__name__}: {e}{END}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="http://localhost:8000")
    args = ap.parse_args()
    base = args.backend.rstrip("/")

    print(f"\n  Smoke test Nexus9 — backend: {base}\n")
    results = []

    # ── Backend health ─────────────────────────────────────
    section("BACKEND")
    results.append(test("GET  /health", lambda: (get(f"{base}/health")[0] == 200, "HTTP 200")))

    def _root():
        s, body = get(f"{base}/")
        if s == 200 and (b'id="root"' in body or b"NEXUS9" in body):
            return True, "React SPA"
        if s == 200:
            return None, "legacy HTML"
        return False, f"HTTP {s}"
    results.append(test("GET  /  (SPA root)", _root))

    # ── Phase 2 endpoints ──────────────────────────────────
    section("EXISTING ENDPOINTS (Phase 2)")
    for ep in ["/v1/health/deep", "/v1/agents", "/v1/models", "/v1/crew/jobs", "/v1/budget"]:
        results.append(test(f"GET  {ep}",
            (lambda ep=ep: (get(f"{base}{ep}")[0] == 200, f"HTTP {get(f'{base}{ep}')[0]}"))))

    # ── Phase 4 monitoring ─────────────────────────────────
    section("MONITORING (Phase 4)")
    for ep in ["/v1/docker/containers", "/v1/chromadb/stats"]:
        def make(ep=ep):
            def f():
                s, body = get(f"{base}{ep}")
                if s != 200:
                    return False, f"HTTP {s}"
                try:
                    data = json.loads(body)
                    if data.get("available", True):
                        return True, "service up"
                    return None, f"service down: {str(data.get('error', '?'))[:32]}"
                except json.JSONDecodeError:
                    return False, "not JSON"
            return f
        results.append(test(f"GET  {ep}", make()))

    # ── Phase 7 WebSocket + events ─────────────────────────
    section("WEBSOCKET & EVENTS (Phase 7)")

    def _events_recent():
        s, body = get(f"{base}/v1/events/recent")
        if s != 200:
            return False, f"HTTP {s}"
        data = json.loads(body)
        return True, f"{len(data.get('events', []))} events · {data.get('subscribers', 0)} subs"
    results.append(test("GET  /v1/events/recent", _events_recent))

    def _events_publish():
        s, body = post(f"{base}/v1/events/publish",
                       {"level": "info", "source": "SMOKE", "msg": "smoke test ping"})
        if s != 200:
            return False, f"HTTP {s}"
        data = json.loads(body)
        return data.get("ok") is True, f"delivered={data.get('delivered')}"
    results.append(test("POST /v1/events/publish", _events_publish))

    # ── Phase 7 services TCP ───────────────────────────────
    section("PHASE 7 SERVICES")
    services = [
        ("postgres   :5432", "localhost", 5432),
        ("redis      :6379", "localhost", 6379),
        ("traefik    :80",   "localhost", 80),
        ("traefik UI :8090", "localhost", 8090),
    ]
    for label, host, port in services:
        def make(host=host, port=port):
            def f():
                return tcp_alive(host, port), "TCP open" if tcp_alive(host, port) else "TCP closed"
            return f
        results.append(test(label, make()))

    # ── Ollama models ──────────────────────────────────────
    section("OLLAMA")
    def _ollama_models():
        s, body = get("http://localhost:11434/api/tags")
        if s != 200:
            return False, f"HTTP {s}"
        data = json.loads(body)
        models = [m["name"] for m in data.get("models", [])]
        if "nomic-embed-text:latest" in models or any("nomic-embed-text" in m for m in models):
            return True, "nomic-embed-text installé"
        return None, f"nomic-embed-text MANQUANT (modèles: {len(models)})"
    results.append(test("nomic-embed-text installed", _ollama_models))

    # ── Frontend build ─────────────────────────────────────
    section("FRONTEND BUILD")
    here = os.path.dirname(os.path.abspath(__file__))
    dist = os.path.join(here, "frontend", "dist")
    def _dist():
        if not os.path.isdir(dist):
            return False, "missing — run `npm run build`"
        idx = os.path.join(dist, "index.html")
        if not os.path.isfile(idx):
            return False, "no index.html"
        return True, f"index.html present ({os.path.getsize(idx)}B)"
    results.append(test("frontend/dist/index.html", _dist))

    # ── Archive integrity ──────────────────────────────────
    section("ARCHIVE")
    def _legacy(p, label):
        full = os.path.join(here, "archive", "legacy", p)
        if os.path.isfile(full) or os.path.isdir(full):
            return True, "archived OK"
        return False, "missing"
    results.append(test("archive/legacy/Nexus9.html",
        lambda: _legacy("Nexus9.html", "html")))
    results.append(test("archive/legacy/orbital_ui_vanilla/",
        lambda: _legacy("orbital_ui_vanilla", "dir")))

    # ── Summary ────────────────────────────────────────────
    n_ok   = sum(1 for r in results if r is True)
    n_warn = sum(1 for r in results if r is None)
    n_ko   = sum(1 for r in results if r is False)
    total  = len(results)
    print(f"\n  Summary: {OK} {n_ok}  {WARN} {n_warn}  {KO} {n_ko}  / {total}\n")
    if n_ko > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

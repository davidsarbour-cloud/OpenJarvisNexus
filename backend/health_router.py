"""Health, telemetry & system-metrics endpoints.

Extracted from main.py. Reads shared state (budget, Anthropic client, http
client) from app_state; no dependency back on main.
"""

import os
import subprocess
import time
from datetime import datetime

import httpx
from app_state import (
    BUDGET_MAX_USD,
    CLAUDE_MODEL,
    _budget,
    _crew_jobs,
    claude,
    get_http,
)
from fastapi import APIRouter
from ollama_client import OLLAMA_MODEL, is_ollama_available

router = APIRouter(tags=["health"])


# ─── moved verbatim from main.py ───
_health_cache: dict = {"ollama_ok": None, "ts": 0.0}
_HEALTH_TTL = 8.0  # seconds — avoid hammering Ollama on every frontend poll

@router.get("/health")
def health():
    import time as _t
    now = _t.monotonic()
    if _health_cache["ollama_ok"] is None or now - _health_cache["ts"] > _HEALTH_TTL:
        _health_cache["ollama_ok"] = is_ollama_available()
        _health_cache["ts"] = now
    ollama_ok = _health_cache["ollama_ok"]
    return {
        "status":        "ok",
        "version":       "0.5.0",
        "claude_model":  CLAUDE_MODEL,
        "ollama_online": ollama_ok,
        "ollama_model":  OLLAMA_MODEL if ollama_ok else "non disponible",
        "budget": {
            "depense":       f"${_budget['cout_usd']:.4f}",
            "maximum":       f"${BUDGET_MAX_USD}",
            "restant":       f"${BUDGET_MAX_USD - _budget['cout_usd']:.4f}",
            "appels_ollama": _budget["appels_ollama"],
            "appels_claude": _budget["appels_claude"],
        }
    }


async def _hc_claude() -> str:
    """Health check Claude API — isolé pour asyncio.gather."""
    import asyncio
    try:
        await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                None,
                lambda: claude.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "ping"}],
                ),
            ),
            timeout=5.0,
        )
        return "ok"
    except asyncio.TimeoutError:
        return "timeout"
    except Exception as e:
        return f"error: {type(e).__name__}"

async def _hc_ollama() -> str:
    """Health check Ollama."""
    return "ok" if is_ollama_available() else "offline"

async def _hc_forge() -> str:
    """Health check Forge Room — vérifie que le dossier output existe."""
    try:
        from forge_room.fabrication_pipeline import FORGE_OUTPUT
        return "ok" if FORGE_OUTPUT.exists() else "error: forge_output absent"
    except Exception as e:
        return f"error: {e}"

async def _hc_meshy() -> str:
    """Health check Meshy API — utilise le client HTTP partagé."""
    meshy_key = os.getenv("MESHY_API_KEY", "")
    if not meshy_key:
        return "not_configured"
    if get_http() is None:
        return "error: client_not_ready"
    try:
        r = await get_http().get(
            "https://api.meshy.ai/v2/text-to-3d",
            headers={"Authorization": f"Bearer {meshy_key}"},
            timeout=3.0,
        )
        return "ok" if r.status_code in (200, 401, 403) else f"error: HTTP {r.status_code}"
    except httpx.TimeoutException:
        return "timeout"
    except Exception as e:
        return f"error: {type(e).__name__}"

@router.get("/v1/health/deep")
async def health_deep():
    """Health check approfondi — teste chaque service en parallèle (asyncio.gather).
    Retourne: backend, claude_api, ollama, forge_room, meshy_api, timestamp.
    """
    import asyncio
    now = datetime.now().isoformat(timespec="seconds")

    # Tous les checks en parallèle — latence = max(individuel) au lieu de la somme
    claude_status, ollama_status, forge_status, meshy_status = await asyncio.gather(
        _hc_claude(), _hc_ollama(), _hc_forge(), _hc_meshy()
    )

    return {
        "backend":    "ok",
        "claude_api": claude_status,
        "ollama":     ollama_status,
        "forge_room": forge_status,
        "meshy_api":  meshy_status,
        "timestamp":  now,
    }

@router.get("/v1/savings")
def savings():
    return {"balance": 0}

@router.get("/v1/telemetry/stats")
def telemetry_stats():
    return {"stats": {}}

@router.get("/v1/telemetry/energy")
def telemetry_energy():
    return {"energy": 0}


_sys_net_state = {"t": 0.0, "bytes": 0}


def _read_vram() -> dict:
    """VRAM/GPU via nvidia-smi. Retourne des None si pas de GPU NVIDIA."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        used, total, util = (int(x.strip()) for x in out.stdout.strip().splitlines()[0].split(","))
        return {"vram": round(used / total * 100), "vram_used_mb": used,
                "vram_total_mb": total, "gpu_util": util}
    except Exception:
        return {"vram": None, "vram_used_mb": None, "vram_total_mb": None, "gpu_util": None}


def _collect_system_metrics() -> dict:
    """Collecte CPU/RAM/VRAM/stockage/réseau + health score (source unique)."""
    import sys

    import psutil
    cpu     = psutil.cpu_percent(interval=0.1)
    ram     = psutil.virtual_memory().percent
    storage = psutil.disk_usage("C:/" if sys.platform == "win32" else "/").percent
    g       = _read_vram()

    net   = psutil.net_io_counters()
    total = net.bytes_sent + net.bytes_recv
    now   = time.time()
    mbps  = 0.0
    if _sys_net_state["t"]:
        dt = now - _sys_net_state["t"]
        if dt > 0:
            mbps = (total - _sys_net_state["bytes"]) / dt / 1_000_000
    _sys_net_state["t"] = now
    _sys_net_state["bytes"] = total

    score = 100
    for v in (cpu, ram, g["vram"], storage):
        if v is None:
            continue
        if v > 90:
            score -= 15
        elif v > 80:
            score -= 8
        elif v > 70:
            score -= 3
    score = max(0, score)
    label = ("OPTIMAL" if score >= 85 else "GOOD" if score >= 70
             else "FAIR" if score >= 50 else "DEGRADED")

    return {
        "cpu": round(cpu), "ram": round(ram), "storage": round(storage),
        "vram": g["vram"], "vram_used_mb": g["vram_used_mb"],
        "vram_total_mb": g["vram_total_mb"], "gpu_util": g["gpu_util"],
        "network_mbps": round(max(0.0, mbps), 1),
        "health_score": score, "health_label": label,
    }


@router.get("/v1/system/metrics")
def system_metrics():
    """Métriques hardware temps réel pour le HUD (JSON)."""
    return _collect_system_metrics()


@router.get("/metrics")
def prometheus_metrics():
    """Exposition Prometheus des métriques hardware (host + GPU) pour le scrape."""
    from fastapi.responses import PlainTextResponse
    m = _collect_system_metrics()
    out: list[str] = []

    def gauge(name: str, val, help_: str):
        if val is None:
            return
        out.append(f"# HELP {name} {help_}")
        out.append(f"# TYPE {name} gauge")
        out.append(f"{name} {val}")

    gauge("nexus_cpu_percent",      m["cpu"],           "Host CPU usage percent")
    gauge("nexus_ram_percent",      m["ram"],           "Host RAM usage percent")
    gauge("nexus_storage_percent",  m["storage"],       "Host storage usage percent (C:)")
    gauge("nexus_vram_percent",     m["vram"],          "GPU VRAM usage percent")
    gauge("nexus_vram_used_mb",     m["vram_used_mb"],  "GPU VRAM used (MB)")
    gauge("nexus_vram_total_mb",    m["vram_total_mb"], "GPU VRAM total (MB)")
    gauge("nexus_gpu_util_percent", m["gpu_util"],      "GPU utilization percent")
    gauge("nexus_network_mbps",     m["network_mbps"],  "Host network throughput (MB/s)")
    gauge("nexus_health_score",     m["health_score"],  "Composite system health score (0-100)")

    return PlainTextResponse("\n".join(out) + "\n",
                             media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get("/api/digest")
def api_digest():
    return {
        "summary":       "OpenJarvis Nexus en ligne.",
        "alerts":        [],
        "agents_active": len([j for j in _crew_jobs.values() if j["status"] == "running"]),
        "timestamp":     int(time.time()),
    }

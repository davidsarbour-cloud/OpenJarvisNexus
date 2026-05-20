"""
Budget Tracker — persistance des coûts API Claude par jour/mois.
Fichier : backend/budget_logs.json
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path
from threading import Lock

BUDGET_FILE = Path(__file__).parent / "budget_logs.json"
_lock = Lock()

# Tarifs Claude (USD per 1K tokens, moyenne input+output)
PRICING = {
    "haiku":  {"input": 0.0008,  "output": 0.004},   # haiku-4-5
    "sonnet": {"input": 0.003,   "output": 0.015},   # sonnet-4-6
}


def _load() -> dict:
    if not BUDGET_FILE.exists():
        return {"daily": {}}
    try:
        return json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"daily": {}}


def _save(data: dict):
    BUDGET_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def record_call(model: str, input_tokens: int, output_tokens: int):
    """Enregistre un appel Claude dans le log persistant."""
    tier = "sonnet" if "sonnet" in model.lower() else "haiku"
    p = PRICING[tier]
    cost = (input_tokens / 1000) * p["input"] + (output_tokens / 1000) * p["output"]
    today = date.today().isoformat()

    with _lock:
        data = _load()
        day = data["daily"].setdefault(today, {
            "cost_usd":     0.0,
            "calls_claude": 0,
            "calls_ollama": 0,
            "tokens_in":    0,
            "tokens_out":   0,
            "models":       {},
        })
        day["cost_usd"]     += cost
        day["calls_claude"] += 1
        day["tokens_in"]    += input_tokens
        day["tokens_out"]   += output_tokens
        day["models"][model] = day["models"].get(model, 0) + 1
        _save(data)

    return cost


def record_ollama_call():
    """Enregistre un appel Ollama (gratuit)."""
    today = date.today().isoformat()
    with _lock:
        data = _load()
        day = data["daily"].setdefault(today, {
            "cost_usd": 0.0, "calls_claude": 0, "calls_ollama": 0,
            "tokens_in": 0, "tokens_out": 0, "models": {},
        })
        day["calls_ollama"] += 1
        _save(data)


def get_today() -> dict:
    data = _load()
    today = date.today().isoformat()
    return data["daily"].get(today, {
        "cost_usd": 0.0, "calls_claude": 0, "calls_ollama": 0,
        "tokens_in": 0, "tokens_out": 0,
    })


def get_history(days: int = 30) -> list:
    data = _load()
    result = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        entry = data["daily"].get(d, {
            "cost_usd": 0.0, "calls_claude": 0, "calls_ollama": 0,
            "tokens_in": 0, "tokens_out": 0,
        })
        result.append({"date": d, **entry})
    return result


def get_stats() -> dict:
    history = get_history(30)
    active_days  = [d for d in history if d["cost_usd"] > 0]
    weekly       = [d for d in history[-7:] if d["cost_usd"] > 0]
    monthly_total = sum(d["cost_usd"] for d in history)
    daily_avg     = monthly_total / max(len(active_days), 1)
    weekly_avg    = sum(d["cost_usd"] for d in weekly) / max(len(weekly), 1)
    monthly_proj  = daily_avg * 30

    return {
        "today":          get_today(),
        "daily_avg_usd":  round(daily_avg, 4),
        "weekly_avg_usd": round(weekly_avg, 4),
        "monthly_total":  round(monthly_total, 4),
        "monthly_proj":   round(monthly_proj, 4),
        "history_30d":    history,
    }

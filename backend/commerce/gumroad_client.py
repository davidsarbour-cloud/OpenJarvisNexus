"""
Gumroad API v2 client — read-only sales/revenue for the Command Center.

Auth: a personal access token (GUMROAD_ACCESS_TOKEN), generated in
Gumroad → Settings → Advanced → Applications → "Generate access token".
Passed as the `access_token` query param on each request. READ-ONLY: we only
GET /v2/sales to aggregate revenue — this client never writes to Gumroad.

Shape of get_sales_revenue() mirrors commerce.etsy_client.get_shop_revenue()
so the frontend revenue cards are interchangeable.
"""
from __future__ import annotations

import os
import time as _time
from datetime import datetime, timezone

import httpx

GUMROAD_ACCESS_TOKEN = os.getenv("GUMROAD_ACCESS_TOKEN", "")
GUMROAD_BASE = "https://api.gumroad.com/v2"


# ── Auth ──────────────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    """Vrai si GUMROAD_ACCESS_TOKEN est configuré."""
    return bool(GUMROAD_ACCESS_TOKEN)


def _auth_error() -> dict:
    return {
        "error": "Non authentifié — configure GUMROAD_ACCESS_TOKEN dans .env "
                 "(Gumroad → Settings → Advanced → Applications → Generate access token).",
    }


def _disconnected(days: int, error: str) -> dict:
    return {
        "connected": False, "error": error,
        "days": days, "currency": "USD",
        "total": 0.0, "orders": 0, "today": 0.0,
        "last_order": None, "recent": [],
    }


def _parse_ts(s: str) -> int:
    """ISO 8601 (Gumroad `created_at`, ex '2026-06-07T14:03:00Z') → epoch seconds."""
    try:
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


# ── Sales / Revenue ───────────────────────────────────────────────────────────

async def _get_sales_page(client: httpx.AsyncClient, after: str, page_key: str | None) -> dict:
    params: dict = {"access_token": GUMROAD_ACCESS_TOKEN, "after": after}
    if page_key:
        params["page_key"] = page_key
    resp = await client.get(f"{GUMROAD_BASE}/sales", params=params)
    if resp.is_success:
        return resp.json()
    return {"error": resp.text, "status_code": resp.status_code}


async def get_sales_revenue(days: int = 30, max_pages: int = 10) -> dict:
    """
    Agrège le chiffre d'affaires Gumroad sur les N derniers jours (ventes brutes).
    Alimente la carte $$$ du Command Center.
    Retourne {connected, days, currency, total, orders, today, last_order, recent[]}.
    """
    if not is_authenticated():
        return _disconnected(days, _auth_error()["error"])

    now      = int(_time.time())
    midnight = now - (now % 86400)                                   # UTC, comme l'Etsy
    after    = datetime.fromtimestamp(now - days * 86400, tz=timezone.utc).strftime("%Y-%m-%d")

    total  = 0.0
    today  = 0.0
    orders = 0
    recent: list[dict] = []
    page_key: str | None = None

    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(max_pages):
            data = await _get_sales_page(client, after, page_key)
            if not isinstance(data, dict) or data.get("error"):
                # 1re page en erreur = non connecté ; page suivante = on garde l'acquis.
                if orders == 0:
                    err = (data or {}).get("error", "réponse Gumroad invalide") \
                        if isinstance(data, dict) else "réponse Gumroad invalide"
                    return _disconnected(days, err)
                break

            sales = data.get("sales", []) or []
            for s in sales:
                if s.get("refunded"):
                    continue                                         # on ne compte pas les remboursés
                amount  = float(s.get("price", 0) or 0) / 100.0      # Gumroad = montants en cents
                total  += amount
                orders += 1
                ts = _parse_ts(s.get("created_at", ""))
                if ts >= midnight:
                    today += amount
                recent.append({
                    "name":   s.get("product_name", ""),
                    "amount": round(amount, 2),
                    "ts":     ts,
                })

            page_key = data.get("next_page_key")
            if not page_key or not sales:
                break

    recent.sort(key=lambda x: x["ts"], reverse=True)
    return {
        "connected":  True,
        "days":       days,
        "currency":   "USD",
        "total":      round(total, 2),
        "orders":     orders,
        "today":      round(today, 2),
        "last_order": recent[0] if recent else None,
        "recent":     recent[:5],
    }

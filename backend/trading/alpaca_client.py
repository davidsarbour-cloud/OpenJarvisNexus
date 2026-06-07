"""
Alpaca Trading API v2 client — account, positions, orders (stocks + crypto).

Auth se fait via deux headers sur chaque requête : APCA-API-KEY-ID et
APCA-API-SECRET-KEY (paire générée dans le dashboard Alpaca — PAS le seed 2FA).
ALPACA_BASE_URL choisit paper (par défaut) vs live :
    paper = https://paper-api.alpaca.markets
    live  = https://api.alpaca.markets
"""
from __future__ import annotations

import os

import httpx

ALPACA_API_KEY_ID     = os.getenv("ALPACA_API_KEY_ID", "")
ALPACA_API_SECRET_KEY = os.getenv("ALPACA_API_SECRET_KEY", "")
ALPACA_BASE_URL       = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets").rstrip("/")


# ── Auth ────────────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    """Vrai si la paire de clés API Alpaca est configurée."""
    return bool(ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY)


def is_paper() -> bool:
    """Vrai si on pointe sur l'environnement paper (simulation)."""
    return "paper-api" in ALPACA_BASE_URL


def _headers() -> dict:
    return {
        "APCA-API-KEY-ID":     ALPACA_API_KEY_ID,
        "APCA-API-SECRET-KEY": ALPACA_API_SECRET_KEY,
        "Content-Type":        "application/json",
    }


def _auth_error() -> dict:
    return {
        "error": "Non authentifié — configure ALPACA_API_KEY_ID + "
                 "ALPACA_API_SECRET_KEY dans .env (dashboard Alpaca → API Keys).",
    }


async def _get(path: str, params: dict | None = None) -> dict | list:
    if not is_authenticated():
        return _auth_error()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{ALPACA_BASE_URL}{path}", headers=_headers(), params=params)
    if resp.is_success:
        return resp.json()
    return {"error": resp.text, "status_code": resp.status_code}


# ── Account ─────────────────────────────────────────────────────────────────

async def get_account() -> dict:
    """
    Détails du compte : equity, buying power, cash, statut, jour de trade.
    GET /v2/account
    """
    return await _get("/v2/account")  # type: ignore[return-value]


async def get_account_summary() -> dict:
    """
    Vue condensée pour le Command Center (carte portefeuille).
    Retourne {connected, paper, currency, equity, last_equity, cash,
              buying_power, pnl_today, pnl_today_pct, status}.
    """
    data = await get_account()
    if not isinstance(data, dict) or data.get("error"):
        return {
            "connected": False,
            "paper":     is_paper(),
            "error":     (data or {}).get("error", "réponse Alpaca invalide")
                         if isinstance(data, dict) else "réponse Alpaca invalide",
            "equity": 0.0, "last_equity": 0.0, "cash": 0.0,
            "buying_power": 0.0, "pnl_today": 0.0, "pnl_today_pct": 0.0,
            "currency": "USD", "status": "unknown",
        }

    equity      = float(data.get("equity", 0) or 0)
    last_equity = float(data.get("last_equity", 0) or 0)
    pnl_today   = equity - last_equity
    pnl_pct     = (pnl_today / last_equity * 100) if last_equity else 0.0
    return {
        "connected":     True,
        "paper":         is_paper(),
        "currency":      data.get("currency", "USD"),
        "equity":        round(equity, 2),
        "last_equity":   round(last_equity, 2),
        "cash":          round(float(data.get("cash", 0) or 0), 2),
        "buying_power":  round(float(data.get("buying_power", 0) or 0), 2),
        "pnl_today":     round(pnl_today, 2),
        "pnl_today_pct": round(pnl_pct, 2),
        "status":        data.get("status", "unknown"),
    }


# ── Positions ───────────────────────────────────────────────────────────────

async def get_positions() -> list | dict:
    """Positions ouvertes. GET /v2/positions"""
    return await _get("/v2/positions")


# ── Orders ──────────────────────────────────────────────────────────────────

async def get_orders(status: str = "open", limit: int = 50) -> list | dict:
    """
    Liste des ordres. status ∈ {open, closed, all}. GET /v2/orders
    """
    return await _get("/v2/orders", params={"status": status, "limit": limit})


async def submit_order(
    symbol: str,
    side: str,
    qty: float | None = None,
    notional: float | None = None,
    order_type: str = "market",
    time_in_force: str = "day",
    limit_price: float | None = None,
) -> dict:
    """
    Passe un ordre. Fournir SOIT qty (nombre d'actions) SOIT notional ($).
    side ∈ {buy, sell} ; order_type ∈ {market, limit, stop, stop_limit}.
    POST /v2/orders
    """
    if not is_authenticated():
        return _auth_error()
    if not symbol.strip():
        return {"error": "symbol manquant"}
    if (qty is None) == (notional is None):
        return {"error": "fournir exactement un de qty ou notional"}
    if side not in ("buy", "sell"):
        return {"error": "side doit être 'buy' ou 'sell'"}

    body: dict = {
        "symbol":        symbol.upper(),
        "side":          side,
        "type":          order_type,
        "time_in_force": time_in_force,
    }
    if qty is not None:
        body["qty"] = str(qty)
    if notional is not None:
        body["notional"] = str(notional)
    if limit_price is not None:
        body["limit_price"] = str(limit_price)

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{ALPACA_BASE_URL}/v2/orders", headers=_headers(), json=body)
    if resp.is_success:
        return resp.json()
    return {"error": resp.text, "status_code": resp.status_code}


async def cancel_order(order_id: str) -> dict:
    """Annule un ordre ouvert. DELETE /v2/orders/{id}"""
    if not is_authenticated():
        return _auth_error()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.delete(f"{ALPACA_BASE_URL}/v2/orders/{order_id}", headers=_headers())
    if resp.is_success:
        return {"ok": True, "order_id": order_id}
    return {"error": resp.text, "status_code": resp.status_code}

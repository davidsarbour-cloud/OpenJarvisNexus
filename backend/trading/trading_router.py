"""
Trading Router — endpoints FastAPI pour l'API Alpaca (stocks + crypto).

GET  /v1/trading/status              — auth configurée ? paper/live ?
GET  /v1/trading/account            — détails complets du compte Alpaca
GET  /v1/trading/summary           — vue condensée (carte Command Center)
GET  /v1/trading/positions         — positions ouvertes
GET  /v1/trading/orders            — liste des ordres (open|closed|all)
POST /v1/trading/orders            — passe un ordre (qty OU notional)
DELETE /v1/trading/orders/{id}     — annule un ordre ouvert
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from trading import alpaca_client as ac

router = APIRouter(prefix="/v1/trading", tags=["Trading"])


class OrderRequest(BaseModel):
    symbol: str
    side: str                       # buy | sell
    qty: float | None = None        # nombre d'actions
    notional: float | None = None   # montant $ (alternative à qty)
    order_type: str = "market"      # market | limit | stop | stop_limit
    time_in_force: str = "day"
    limit_price: float | None = None


@router.get("/status", summary="Statut de la configuration Alpaca")
async def status():
    return {
        "authenticated": ac.is_authenticated(),
        "paper":         ac.is_paper(),
        "base_url":      ac.ALPACA_BASE_URL,
    }


@router.get("/account", summary="Détails complets du compte Alpaca")
async def account():
    data = await ac.get_account()
    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=502, detail=data["error"])
    return data


@router.get("/summary", summary="Vue condensée du portefeuille (Command Center)")
async def summary():
    return await ac.get_account_summary()


@router.get("/positions", summary="Positions ouvertes")
async def positions():
    data = await ac.get_positions()
    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=502, detail=data["error"])
    return data


@router.get("/orders", summary="Liste des ordres")
async def orders(status: str = "open", limit: int = 50):
    data = await ac.get_orders(status=status, limit=limit)
    if isinstance(data, dict) and data.get("error"):
        raise HTTPException(status_code=502, detail=data["error"])
    return data


@router.post("/orders", summary="Passe un ordre")
async def place_order(body: OrderRequest):
    result = await ac.submit_order(
        symbol=body.symbol,
        side=body.side,
        qty=body.qty,
        notional=body.notional,
        order_type=body.order_type,
        time_in_force=body.time_in_force,
        limit_price=body.limit_price,
    )
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/orders/{order_id}", summary="Annule un ordre ouvert")
async def cancel(order_id: str):
    result = await ac.cancel_order(order_id)
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

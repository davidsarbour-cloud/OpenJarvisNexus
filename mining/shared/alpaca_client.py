"""Alpaca execution client — the last line before real money.

HARD paper/live double-gate:
    LIVE requires  ALPACA_MODE=live  AND  I_UNDERSTAND_LIVE_RISK=yes.
Anything else routes to the PAPER endpoint, no exceptions. The data-only
providers (Polygon / Finnhub / FMP) never reach this class — only Alpaca
executes orders.

`alpaca` is imported lazily so the module imports without alpaca-py installed.
"""
from __future__ import annotations

from shared.config import Settings


class AlpacaBroker:
    def __init__(self, settings: Settings):
        self._s = settings
        self._client = None

    def _paper(self) -> bool:
        return not self._s.live_enabled

    def connect(self) -> "AlpacaBroker":
        from alpaca.trading.client import TradingClient
        self._client = TradingClient(self._s.alpaca_key, self._s.alpaca_secret,
                                     paper=self._paper())
        return self

    def equity(self) -> float:
        try:
            return float(self._client.get_account().equity)
        except Exception:
            return 100.0  # paper scaffold fallback

    def submit(self, ticker: str, qty: float, side: str):
        """Market order. Refuses to BUY live unless the double-gate is armed."""
        if side == "buy" and self._s.mode == "live" and not self._s.live_enabled:
            raise RuntimeError("LIVE blocked — set I_UNDERSTAND_LIVE_RISK=yes to arm live trading")
        if self._client is None:
            raise RuntimeError("broker not connected — call connect() first")
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest
        req = MarketOrderRequest(
            symbol=ticker, qty=qty,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        return self._client.submit_order(req)

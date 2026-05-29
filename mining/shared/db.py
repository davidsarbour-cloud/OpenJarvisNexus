"""Postgres persistence — source of truth for fills + day-state recovery.

The risk-manager persists every fill here and, on boot, rebuilds today's
DayState from the fills since midnight UTC. That makes the trade cap / exposure
/ daily-loss limits survive a restart — critical once real money is involved
(a restarted bot that forgot it already traded 20 times would blow the cap).

`psycopg` is imported lazily so the module imports without it installed. If
Postgres is unreachable the risk-manager falls back to in-memory state.
"""
from __future__ import annotations

import datetime as dt

from shared.config import Settings
from shared.risk import DayState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fills (
  id     BIGSERIAL PRIMARY KEY,
  ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
  ticker TEXT NOT NULL,
  side   TEXT NOT NULL,
  qty    DOUBLE PRECISION NOT NULL,
  price  DOUBLE PRECISION NOT NULL,
  pnl    DOUBLE PRECISION NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS fills_ts_idx ON fills (ts);
"""


class Store:
    def __init__(self, settings: Settings):
        self._s = settings
        self._conn = None

    async def connect(self) -> "Store":
        import psycopg
        self._conn = await psycopg.AsyncConnection.connect(self._s.postgres_url, autocommit=True)
        async with self._conn.cursor() as cur:
            await cur.execute(_SCHEMA)
        return self

    async def persist_fill(self, ticker: str, side: str, qty: float,
                           price: float, pnl: float = 0.0) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO fills (ticker, side, qty, price, pnl) VALUES (%s, %s, %s, %s, %s)",
                (ticker, side, qty, price, pnl),
            )

    async def rebuild_day_state(self, start_equity: float) -> DayState:
        """Reconstruct today's DayState from fills since midnight UTC."""
        st = DayState(start_equity=start_equity, equity=start_equity)
        since = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        async with self._conn.cursor() as cur:
            await cur.execute(
                "SELECT ticker, side, qty, price, pnl FROM fills WHERE ts >= %s ORDER BY ts",
                (since,),
            )
            rows = await cur.fetchall()
        for ticker, side, qty, price, pnl in rows:
            if side == "buy":
                st.trades_today[ticker] = st.trades_today.get(ticker, 0) + 1
                st.open_exposure[ticker] = st.open_exposure.get(ticker, 0.0) + qty * price
            else:
                st.open_exposure[ticker] = 0.0
                st.equity += pnl
        return st

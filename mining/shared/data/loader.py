"""Historical bar loaders → list[Bar] for the backtester.

Two sources:
  - yfinance  : keyless, free. 1y of 1h bars works (yfinance caps intraday
                at 60d for <=30m, but allows 1h up to 730d). Good enough to
                judge the edge directionally without an Alpaca account.
  - alpaca    : the real deal — 1y of 5/15-min bars via the free IEX feed.
                Needs ALPACA_API_KEY / ALPACA_API_SECRET. Ready for when
                you've got keys; falls back with a clear message otherwise.

Both return the SAME Bar list the strategy/backtester consume, so swapping
sources changes nothing downstream.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_MINING_ROOT = Path(__file__).resolve().parents[2]
if str(_MINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_MINING_ROOT))

from shared.strategy.base import Bar  # noqa: E402


def load_yfinance(ticker: str, period: str = "1y", interval: str = "1h") -> list[Bar]:
    """Fetch OHLCV bars via yfinance. interval: 1h (1y ok), 15m/5m (<=60d)."""
    import yfinance as yf

    df = yf.download(ticker, period=period, interval=interval,
                     progress=False, auto_adjust=True)
    if df is None or len(df) == 0:
        return []

    # yfinance returns a MultiIndex column frame for single tickers in recent
    # versions ((field, ticker)). Flatten to plain field access.
    def col(name: str):
        if (name, ticker) in df.columns:
            return df[(name, ticker)]
        return df[name]

    bars: list[Bar] = []
    o, h, l, c, v = (col("Open"), col("High"), col("Low"), col("Close"), col("Volume"))
    for ts, idx in zip(df.index, range(len(df))):
        try:
            bars.append(Bar(
                ts=str(ts),
                open=float(o.iloc[idx]),
                high=float(h.iloc[idx]),
                low=float(l.iloc[idx]),
                close=float(c.iloc[idx]),
                volume=float(v.iloc[idx]),
            ))
        except Exception:
            continue
    return bars


def load_alpaca(ticker: str, start: str, end: str, timeframe: str = "15Min") -> list[Bar]:
    """Fetch OHLCV bars via Alpaca historical data (free IEX feed).

    timeframe: '1Min' | '5Min' | '15Min' | '1Hour' | '1Day'.
    Requires ALPACA_API_KEY + ALPACA_API_SECRET in env. This is READ-ONLY
    market data — no account funding, no trading.
    """
    key, secret = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_API_SECRET")
    if not key or not secret:
        raise RuntimeError(
            "Alpaca keys absentes. Crée un compte gratuit sur alpaca.markets, "
            "puis mets ALPACA_API_KEY / ALPACA_API_SECRET dans mining/.env.mining. "
            "(données historiques = gratuit, aucun financement requis)"
        )
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "alpaca-py non installé. `pip install alpaca-py` dans backend/.venv."
        ) from e

    _TF = {
        "1Min":  TimeFrame(1, TimeFrameUnit.Minute),
        "5Min":  TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
        "1Day":  TimeFrame(1, TimeFrameUnit.Day),
    }[timeframe]

    client = StockHistoricalDataClient(key, secret)
    req = StockBarsRequest(symbol_or_symbols=ticker, timeframe=_TF,
                           start=start, end=end)
    barset = client.get_stock_bars(req)
    bars: list[Bar] = []
    for b in barset.data.get(ticker, []):
        bars.append(Bar(
            ts=b.timestamp.isoformat(), open=float(b.open), high=float(b.high),
            low=float(b.low), close=float(b.close), volume=float(b.volume),
        ))
    return bars

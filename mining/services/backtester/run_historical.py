"""Backtest the momentum+trailing strategy on REAL historical bars.

Intrabar-aware + PESSIMISTIC exit modelling (the honest choice):
for each bar while in a position, the bar's LOW is tested against the stop
computed from the PRIOR high-water FIRST (assume the adverse dip happened
before any new high) — only if we survive does the high-water ratchet up
with the bar's HIGH. This deflates results slightly vs reality but never
flatters them, which is what you want before risking money.

Entries fire at the bar close when the momentum/volume/trend filters align.

Usage:
    python -m mining.services.backtester.run_historical                 # NVDA+TSLA, yfinance, 1y, 1h
    python -m mining.services.backtester.run_historical --source alpaca # needs keys, 15Min
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_MINING_ROOT = Path(__file__).resolve().parents[2]
if str(_MINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_MINING_ROOT))

from shared.strategy.base import Bar  # noqa: E402
from shared.strategy.momentum_trailing import (  # noqa: E402
    MomentumTrailing,
    stop_price,
    update_high_water,
)

from services.backtester.backtester import BacktestResult, Trade  # noqa: E402


def run_ohlc_backtest(
    bars: list[Bar],
    strat: MomentumTrailing,
    start_equity: float = 10_000.0,
    risk_per_trade_pct: float = 0.10,
    slippage_pct: float = 0.0005,        # 0.05% per side (realistic market-order slip)
    commission_per_trade: float = 0.0,   # Alpaca stocks = $0; parametrised anyway
) -> BacktestResult:
    """OHLC + pessimistic intrabar exit + transaction costs.

    `strat` is a freshly-built (configured) MomentumTrailing — the sweep
    passes a new one per param combo. Slippage applies to BOTH sides
    (buy fills above close, sell fills below stop) — that's where a thin
    edge dies, so it must be modelled before any capital is risked.
    """
    res = BacktestResult(start_equity=start_equity)
    equity = start_equity
    open_entry = open_ts = open_qty = None  # type: ignore

    for bar in bars:
        roc       = strat.roc.update(bar.close)
        vol_ratio = strat.vol.update(bar.volume)
        atr       = strat.atr.update(bar.high, bar.low, bar.close)
        strat.trend.update(bar.close)

        if strat.position is None:
            if strat.entry_signal(bar, roc, vol_ratio, atr):
                fill = bar.close * (1 + slippage_pct)              # buy pays up
                notional = equity * risk_per_trade_pct
                qty = round(notional / fill, 4) if fill else 0
                if qty > 0:
                    strat.open_position(fill, qty)
                    open_entry, open_ts, open_qty = fill, bar.ts, qty
        else:
            pos = strat.position
            s = stop_price(pos)                                    # stop from prior state
            if bar.low <= s:
                exit_px = s * (1 - slippage_pct)                   # sell gets less
                trade = Trade(open_ts, open_entry, bar.ts, exit_px, open_qty,
                              f"stop {s:.2f} (high {pos.high_water:.2f})")
                if commission_per_trade:
                    equity -= 2 * commission_per_trade
                res.trades.append(trade)
                equity += trade.pnl
                strat.close_position()
            else:
                update_high_water(pos, bar.high)

        unreal = 0.0
        if strat.position is not None:
            unreal = (bar.close - strat.position.entry) * strat.position.qty
        res.equity_curve.append(equity + unreal)

    return res


def _load(source: str, ticker: str, period: str, interval: str) -> list[Bar]:
    from shared.data.loader import load_alpaca, load_yfinance
    if source == "alpaca":
        from datetime import datetime, timedelta
        end = datetime.now()
        start = end - timedelta(days=365)
        tf = {"1h": "1Hour", "15m": "15Min", "5m": "5Min"}.get(interval, "15Min")
        return load_alpaca(ticker, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), tf)
    return load_yfinance(ticker, period=period, interval=interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="yfinance", choices=["yfinance", "alpaca"])
    ap.add_argument("--tickers", default="NVDA,TSLA")
    ap.add_argument("--period", default="1y")
    ap.add_argument("--interval", default="1h")
    args = ap.parse_args()

    print(f"=== Backtest {args.source} · {args.tickers} · {args.period} · {args.interval} ===\n")
    for ticker in args.tickers.split(","):
        ticker = ticker.strip()
        try:
            bars = _load(args.source, ticker, args.period, args.interval)
        except Exception as e:
            print(f"  {ticker}: LOAD FAILED — {e}\n")
            continue
        if not bars:
            print(f"  {ticker}: no bars returned\n")
            continue
        res = run_ohlc_backtest(bars, MomentumTrailing(ticker))
        print(f"  {ticker}  ({len(bars)} bars, {bars[0].ts[:10]} -> {bars[-1].ts[:10]})")
        print(f"    {res.summary()}")
        if res.trades:
            wins = res.wins
            print(f"    avg win {sum(t.pnl_pct for t in wins)/len(wins):+.2f}%"
                  if wins else "    no wins", end="")
            losses = res.losses
            print(f"  |  avg loss {sum(t.pnl_pct for t in losses)/len(losses):+.2f}%"
                  if losses else "  |  no losses")
            best = max(res.trades, key=lambda t: t.pnl_pct)
            worst = min(res.trades, key=lambda t: t.pnl_pct)
            print(f"    best {best.pnl_pct:+.2f}%  worst {worst.pnl_pct:+.2f}%")
        print()


if __name__ == "__main__":
    main()

"""Parameter sweep — find thresholds that give a NET positive edge after
costs, instead of trusting the hand-picked defaults.

Grid-searches the entry filters (min_roc, min_volume_ratio, max_atr_pct)
and the stop geometry (initial_stop, activate_tp, trail). Each combo is
backtested on every ticker with slippage ON, then ranked by combined net
PnL. Data is fetched ONCE per ticker and reused across all combos.

Honesty guards baked in:
  - slippage always on (0.05%/side default)
  - results are COMBINED across tickers (a combo that only works on one
    name is likely overfit)
  - prints how many combos were tested so you can gauge multiple-comparison
    risk (more combos tried = higher odds the "best" is luck)

Usage:
    python -m mining.services.backtester.sweep --tickers NVDA,TSLA --period 1y --interval 1h
"""
from __future__ import annotations

import argparse
import itertools
import sys
from dataclasses import dataclass
from pathlib import Path

_MINING_ROOT = Path(__file__).resolve().parents[2]
if str(_MINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_MINING_ROOT))

from shared.strategy.base import Bar  # noqa: E402
from shared.strategy.momentum_trailing import MomentumTrailing  # noqa: E402

from services.backtester.run_historical import _load, run_ohlc_backtest  # noqa: E402

# ── Grid (kept modest — combos = product of all lists) ───────────────────────
GRID = {
    "min_roc":          [0.2, 0.4, 0.8],
    "min_volume_ratio": [1.2, 1.5, 2.0],
    "max_atr_pct":      [3.0, 5.0],
    "initial_stop_pct": [0.01, 0.015],
    "activate_tp_pct":  [0.02, 0.03],
    "trail_pct":        [0.01, 0.015],
}


@dataclass
class ComboResult:
    params:    dict
    net_pnl:   float
    trades:    int
    win_rate:  float
    profit_factor: float
    max_dd:    float


def run_sweep(bars_by_ticker: dict[str, list[Bar]], slippage_pct: float) -> list[ComboResult]:
    keys = list(GRID.keys())
    combos = list(itertools.product(*(GRID[k] for k in keys)))
    results: list[ComboResult] = []

    for values in combos:
        params = dict(zip(keys, values))
        net_pnl = 0.0
        total_trades = 0
        total_wins = 0
        gross_win = gross_loss = 0.0
        worst_dd = 0.0
        for ticker, bars in bars_by_ticker.items():
            strat = MomentumTrailing(ticker, **params)
            res = run_ohlc_backtest(bars, strat, slippage_pct=slippage_pct)
            net_pnl      += res.total_pnl
            total_trades += res.n_trades
            total_wins   += len(res.wins)
            gross_win    += sum(t.pnl for t in res.wins)
            gross_loss   += abs(sum(t.pnl for t in res.losses))
            worst_dd      = max(worst_dd, res.max_drawdown_pct)
        results.append(ComboResult(
            params=params,
            net_pnl=net_pnl,
            trades=total_trades,
            win_rate=(total_wins / total_trades * 100.0) if total_trades else 0.0,
            profit_factor=(gross_win / gross_loss) if gross_loss else float("inf"),
            max_dd=worst_dd,
        ))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="yfinance", choices=["yfinance", "alpaca"])
    ap.add_argument("--tickers", default="NVDA,TSLA")
    ap.add_argument("--period", default="1y")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--slippage", type=float, default=0.0005)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    # Fetch each ticker ONCE
    bars_by_ticker: dict[str, list[Bar]] = {}
    for ticker in args.tickers.split(","):
        ticker = ticker.strip()
        bars = _load(args.source, ticker, args.period, args.interval)
        if bars:
            bars_by_ticker[ticker] = bars
            print(f"loaded {ticker}: {len(bars)} bars")
        else:
            print(f"skip {ticker}: no bars")
    if not bars_by_ticker:
        print("No data — aborting.")
        return

    combos = 1
    for v in GRID.values():
        combos *= len(v)
    print(f"\nSweeping {combos} combos x {len(bars_by_ticker)} tickers, "
          f"slippage {args.slippage*100:.3f}%/side ...\n")

    results = run_sweep(bars_by_ticker, args.slippage)
    results.sort(key=lambda r: r.net_pnl, reverse=True)

    profitable = [r for r in results if r.net_pnl > 0]
    print(f"{len(profitable)}/{len(results)} combos net-positive after costs.\n")
    print(f"TOP {args.top} by net PnL (combined {args.tickers}):")
    print(f"{'net$':>8} {'trades':>7} {'win%':>6} {'PF':>5} {'maxDD%':>6}  params")
    print("-" * 90)
    for r in results[:args.top]:
        p = r.params
        pstr = (f"roc>={p['min_roc']} vol>={p['min_volume_ratio']} "
                f"atr<={p['max_atr_pct']} stop={p['initial_stop_pct']} "
                f"tp={p['activate_tp_pct']} trail={p['trail_pct']}")
        print(f"{r.net_pnl:8.2f} {r.trades:7d} {r.win_rate:6.1f} "
              f"{r.profit_factor:5.2f} {r.max_dd:6.1f}  {pstr}")

    # Honesty footer
    print(f"\n⚠️  {combos} combos tested → multiple-comparison risk. The 'best' "
          "combo is partly luck. Validate the winner out-of-sample (different "
          "period / tickers) before trusting it. Defaults were: "
          "roc>=0.3 vol>=1.3 atr<=5.0 stop=0.01 tp=0.02 trail=0.01.")


if __name__ == "__main__":
    main()

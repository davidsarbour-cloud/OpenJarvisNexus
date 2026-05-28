"""Multi-window (anchored) walk-forward — the rigorous robustness test.

A single 50/50 split can get lucky on the regime. This splits the series
into N chunks and walks forward:

    fold 1: optimize on chunk[0]      → test on chunk[1]
    fold 2: optimize on chunk[0..1]   → test on chunk[2]
    fold 3: optimize on chunk[0..2]   → test on chunk[3]
    fold 4: optimize on chunk[0..3]   → test on chunk[4]

Each fold RE-OPTIMIZES on its (expanding) training history, then trades
the next, unseen chunk. This tests the PROCESS ("optimize then trade
forward"), not a single fixed param set — which is how you'd actually
run it. Costs (slippage) on, combined across all tickers.

Also reports a FIXED combo (stop=1.5%/tp=+3%, the candidate default) across
every chunk, so we can see if a single robust setting holds without
re-fitting.

Usage:
    python -m mining.services.backtester.multiwindow --tickers ASML,INTC,AMD,NVDA,TSLA --folds 5 --capital 100
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

_MINING_ROOT = Path(__file__).resolve().parents[2]
if str(_MINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_MINING_ROOT))

from services.backtester.run_historical import _load  # noqa: E402
from services.backtester.sweep import GRID  # noqa: E402
from services.backtester.walkforward import _evaluate  # noqa: E402


def _chunks(seq, n):
    """Split a list into n contiguous, roughly-equal chunks."""
    size = len(seq) // n
    return [seq[i * size:(i + 1) * size] for i in range(n - 1)] + [seq[(n - 1) * size:]]


def _best_on(bars_by_ticker, capital, slippage):
    keys = list(GRID.keys())
    best = None
    for values in itertools.product(*(GRID[k] for k in keys)):
        params = dict(zip(keys, values))
        m = _evaluate(bars_by_ticker, params, capital, slippage)
        if best is None or m["net"] > best[1]["net"]:
            best = (params, m)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="yfinance")
    ap.add_argument("--tickers", default="ASML,INTC,AMD,NVDA,TSLA")
    ap.add_argument("--period", default="1y")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--capital", type=float, default=100.0)
    ap.add_argument("--slippage", type=float, default=0.0005)
    args = ap.parse_args()

    # Load + chunk each ticker
    chunks_by_ticker: dict[str, list] = {}
    for ticker in args.tickers.split(","):
        ticker = ticker.strip()
        bars = _load(args.source, ticker, args.period, args.interval)
        if not bars:
            print(f"skip {ticker}: no bars")
            continue
        chunks_by_ticker[ticker] = _chunks(bars, args.folds)
    if not chunks_by_ticker:
        print("No data.")
        return
    tickers = list(chunks_by_ticker)
    print(f"{len(tickers)} tickers, {args.folds} chunks each, capital ${args.capital:.0f}, "
          f"slippage {args.slippage*100:.3f}%/side\n")

    FIXED = dict(min_roc=0.30, min_volume_ratio=1.50, max_atr_pct=5.0,
                 initial_stop_pct=0.015, activate_tp_pct=0.03, trail_pct=0.01)

    def slice_by(idx):
        return {t: chunks_by_ticker[t][idx] for t in tickers}

    def slice_upto(idx):
        # expanding train window = concat chunks 0..idx-1
        out = {}
        for t in tickers:
            merged = []
            for j in range(idx):
                merged += chunks_by_ticker[t][j]
            out[t] = merged
        return out

    print("ANCHORED WALK-FORWARD (re-optimize each fold → trade next unseen chunk):")
    print(f"  {'fold':<6}{'OOS net$':>10}{'PF':>7}{'win%':>7}{'maxDD%':>8}  best params (stop/tp)")
    print("  " + "-" * 78)
    oos_nets, oos_pfs, pos_folds = [], [], 0
    for f in range(1, args.folds):
        train = slice_upto(f)        # chunks 0..f-1
        test  = slice_by(f)          # chunk f (unseen)
        params, _ = _best_on(train, args.capital, args.slippage)
        m = _evaluate(test, params, args.capital, args.slippage)
        oos_nets.append(m["net"])
        oos_pfs.append(m["pf"])
        if m["net"] > 0:
            pos_folds += 1
        tag = f"stop={params['initial_stop_pct']} tp={params['activate_tp_pct']}"
        print(f"  {f:<6}{m['net']:>10.2f}{m['pf']:>7.2f}{m['win']:>7.1f}{m['dd']:>8.1f}  {tag}")

    avg_pf = sum(p for p in oos_pfs if p != float('inf')) / max(len(oos_pfs), 1)
    total_oos = sum(oos_nets)
    print("\n  AGGREGATE OOS:")
    print(f"    net-positive folds: {pos_folds}/{args.folds - 1}")
    print(f"    summed OOS net: ${total_oos:+.2f}   avg OOS PF: {avg_pf:.2f}")

    # Fixed candidate-default combo, fold by fold (no re-fitting)
    print("\nFIXED combo (stop=1.5% tp=+3%) per chunk — no re-fit:")
    fixed_pos = 0
    for f in range(args.folds):
        m = _evaluate(slice_by(f), FIXED, args.capital, args.slippage)
        if m["net"] > 0:
            fixed_pos += 1
        print(f"  chunk {f}:  net ${m['net']:+7.2f}  PF {m['pf']:4.2f}  "
              f"win {m['win']:4.1f}%  trades {m['trades']}")
    print(f"  fixed-combo net-positive chunks: {fixed_pos}/{args.folds}")

    print("\nVERDICT:")
    if pos_folds >= (args.folds - 1) * 0.75 and avg_pf >= 1.1:
        print("  Edge holds across MOST walk-forward folds (process is robust). "
              "Strong signal the strategy generalizes — not a single-window fluke.")
    elif pos_folds >= (args.folds - 1) * 0.5:
        print("  Mixed: edge holds on some folds, not others. Likely regime-dependent "
              "(works in trends, struggles in chop). Treat as conditional, not unconditional.")
    else:
        print("  Edge FAILS across most folds — the single-window result was luck. "
              "Do NOT trade this as-is.")
    print("  Reminder: all 1h bars, one trend-friendly year. A real bear/chop year "
          "+ 5-15min bars (Alpaca) remain untested.")


if __name__ == "__main__":
    main()

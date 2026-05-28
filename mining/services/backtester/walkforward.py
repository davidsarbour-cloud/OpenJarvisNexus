"""Walk-forward / out-of-sample validation — the real anti-overfit test.

Procedure per run:
  1. Split each ticker's bars 50/50 by TIME → in-sample (IS) | out-of-sample (OOS).
  2. Sweep the param grid on the IS half only → pick the single combo with
     the best COMBINED net PnL across all tickers' IS halves.
  3. Apply that ONE combo to the OOS half (never seen during optimization).
  4. Also run the DEFAULT params on OOS as a baseline.

Verdict logic:
  - If the IS-best combo stays net-positive OOS with a similar profit
    factor → the edge is plausibly real (not just curve-fit).
  - If OOS collapses / goes negative → it was overfit. You learn this for
    $0 instead of with real money.

Everything is combined across the 5 tickers and costs (slippage) are on.

Usage:
    python -m mining.services.backtester.walkforward --tickers ASML,INTC,AMD,NVDA,TSLA --capital 100
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

_MINING_ROOT = Path(__file__).resolve().parents[2]
if str(_MINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_MINING_ROOT))

from shared.strategy.momentum_trailing import MomentumTrailing  # noqa: E402

from services.backtester.run_historical import _load, run_ohlc_backtest  # noqa: E402
from services.backtester.sweep import GRID  # noqa: E402


def _evaluate(bars_by_ticker, params, capital, slippage):
    """Combined net PnL / PF / trades / win% across tickers for one param set."""
    net = trades = wins = 0.0
    gw = gl = dd = 0.0
    per_ticker = {}
    for ticker, bars in bars_by_ticker.items():
        strat = MomentumTrailing(ticker, **params)
        res = run_ohlc_backtest(bars, strat, start_equity=capital, slippage_pct=slippage)
        net += res.total_pnl
        trades += res.n_trades
        wins += len(res.wins)
        gw += sum(t.pnl for t in res.wins)
        gl += abs(sum(t.pnl for t in res.losses))
        dd = max(dd, res.max_drawdown_pct)
        per_ticker[ticker] = res.total_pnl
    return {
        "net": net, "trades": trades,
        "win": (wins / trades * 100.0) if trades else 0.0,
        "pf": (gw / gl) if gl else float("inf"),
        "dd": dd, "per_ticker": per_ticker,
    }


def _best_on(bars_by_ticker, capital, slippage):
    """Grid-search → params with best combined net PnL on the given bars."""
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
    ap.add_argument("--capital", type=float, default=100.0)
    ap.add_argument("--slippage", type=float, default=0.0005)
    args = ap.parse_args()

    # Load + split 50/50 by time
    is_by, oos_by = {}, {}
    for ticker in args.tickers.split(","):
        ticker = ticker.strip()
        bars = _load(args.source, ticker, args.period, args.interval)
        if not bars:
            print(f"skip {ticker}: no bars")
            continue
        mid = len(bars) // 2
        is_by[ticker], oos_by[ticker] = bars[:mid], bars[mid:]
        print(f"loaded {ticker}: {len(bars)} bars -> IS {mid} / OOS {len(bars)-mid}")
    if not is_by:
        print("No data.")
        return

    combos = 1
    for v in GRID.values():
        combos *= len(v)
    print(f"\nCapital ${args.capital:.0f} · slippage {args.slippage*100:.3f}%/side · "
          f"{combos} combos optimized on IS, validated on OOS\n")

    DEFAULTS = dict(min_roc=0.30, min_volume_ratio=1.30, max_atr_pct=5.0,
                    initial_stop_pct=0.01, activate_tp_pct=0.02, trail_pct=0.01)

    best_params, is_m = _best_on(is_by, args.capital, args.slippage)

    # The 3 evaluations that matter
    oos_best = _evaluate(oos_by, best_params, args.capital, args.slippage)
    oos_def  = _evaluate(oos_by, DEFAULTS,    args.capital, args.slippage)

    def line(label, m):
        return (f"  {label:<34} net ${m['net']:+7.2f}  trades {m['trades']:>4}  "
                f"win {m['win']:4.1f}%  PF {m['pf']:4.2f}  maxDD {m['dd']:4.1f}%")

    print("IN-SAMPLE (optimized here):")
    print(line("best combo (IS)", is_m))
    p = best_params
    print(f"    -> {p}\n")

    print("OUT-OF-SAMPLE (never seen — the real test):")
    print(line("IS-best combo applied to OOS", oos_best))
    print(line("DEFAULT params on OOS (baseline)", oos_def))
    print()

    # Verdict
    print("VERDICT:")
    if oos_best["net"] > 0 and oos_best["pf"] >= 1.05:
        retention = (oos_best["net"] / is_m["net"] * 100.0) if is_m["net"] else 0.0
        print(f"  OOS net-positive (PF {oos_best['pf']:.2f}). Edge retained "
              f"{retention:.0f}% of IS net. Plausibly real — not just overfit.")
    else:
        print(f"  OOS net {oos_best['net']:+.2f} / PF {oos_best['pf']:.2f} — the "
              "IS-best params DID NOT hold out-of-sample. That's overfit. "
              "Good thing we found out for $0.")
    print(f"  Per-ticker OOS (best combo): {oos_best['per_ticker']}")
    print(f"\n  Note: ${args.capital:.0f} base + fractional shares; $ figures are "
          "tiny but % / PF are scale-invariant. The thesis is the PF + drawdown, "
          "not the dollar amount.")


if __name__ == "__main__":
    main()

"""Backtester sanity + determinism + metric correctness."""
import sys
from pathlib import Path

_MINING_ROOT = Path(__file__).resolve().parents[1]
if str(_MINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_MINING_ROOT))

from services.backtester.backtester import (  # noqa: E402
    BacktestResult,
    Trade,
    _synthetic_bars,
    run_backtest,
)
from shared.strategy.base import Bar  # noqa: E402


def test_runs_on_synthetic_data_without_error():
    bars = _synthetic_bars(n=300)
    res = run_backtest(bars, ticker="TEST")
    assert isinstance(res, BacktestResult)
    assert len(res.equity_curve) == len(bars)       # one equity point per bar
    assert res.n_trades >= 0


def test_deterministic_same_seed_same_result():
    """Same seed → identical trade count + PnL. Non-determinism in a
    backtester is a silent killer; lock it down."""
    a = run_backtest(_synthetic_bars(n=300, seed=42), ticker="T")
    b = run_backtest(_synthetic_bars(n=300, seed=42), ticker="T")
    assert a.n_trades == b.n_trades
    assert round(a.total_pnl, 6) == round(b.total_pnl, 6)


def test_metrics_math():
    res = BacktestResult(start_equity=10_000.0)
    # 2 wins, 1 loss
    res.trades = [
        Trade("t0", 100, "t1", 110, 1, "win"),   # +10
        Trade("t2", 100, "t3", 105, 1, "win"),   # +5
        Trade("t4", 100, "t5",  96, 1, "loss"),  # -4
    ]
    assert res.n_trades == 3
    assert round(res.total_pnl, 2) == 11.0
    assert round(res.win_rate, 1) == 66.7
    assert round(res.profit_factor, 2) == round(15 / 4, 2)


def test_flat_market_no_trades():
    """A perfectly flat series has no momentum/volume → no entries."""
    bars = [Bar(ts=f"t{i}", open=100, high=100, low=100, close=100, volume=1000)
            for i in range(100)]
    res = run_backtest(bars, ticker="FLAT")
    assert res.n_trades == 0
    assert res.total_pnl == 0.0


def test_one_position_at_a_time():
    """Strategy must never stack positions — backtester enforces single
    open position (buy ignored while in a trade)."""
    bars = _synthetic_bars(n=300)
    res = run_backtest(bars, ticker="T")
    # Every trade's entry ts must be strictly after the previous exit ts
    # (string ts are t0,t1,... so lexical compare works for <100; use index)
    def idx(ts: str) -> int: return int(ts[1:])
    for prev, nxt in zip(res.trades, res.trades[1:]):
        assert idx(nxt.entry_ts) >= idx(prev.exit_ts)

"""Exhaustive tests for the trailing-stop math — the part that moves money.

Covers David's exact worked example + the edge cases that matter:
ratchet-up-only, no premature trailing, stop-hit detection.
"""
import sys
from pathlib import Path

_MINING_ROOT = Path(__file__).resolve().parents[1]
if str(_MINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_MINING_ROOT))

from shared.strategy.momentum_trailing import Position, current_stop, should_sell  # noqa: E402


def spec_pos(entry: float, qty: float = 1) -> Position:
    """Position with David's EXACT original spec (-1% / +2% / -1%), so these
    mechanism tests stay valid regardless of what the module DEFAULTS become
    (defaults moved to the backtest-validated 1.5%/3% — see momentum_trailing)."""
    return Position(entry=entry, qty=qty,
                    initial_stop_pct=0.01, activate_tp_pct=0.02, trail_pct=0.01)


def test_david_worked_example():
    """entry 100 -> 99 ; 102 -> 100.98 ; 105 -> 103.95 ; <103.95 sells."""
    p = spec_pos(100.0, 10)
    assert current_stop(p, 100.0) == 99.0          # initial -1%
    assert round(current_stop(p, 102.0), 2) == 100.98   # +2% activates trailing
    assert round(current_stop(p, 105.0), 2) == 103.95   # ratchet to high*0.99
    assert not should_sell(p, 104.0)               # above stop → hold
    assert should_sell(p, 103.90)                  # below 103.95 → sell


def test_stop_is_monotonic_non_decreasing():
    """Trailing stop must never move DOWN, even if price dips then recovers."""
    p = spec_pos(100.0)
    current_stop(p, 110.0)            # stop = 108.9, high=110
    s_after_high = current_stop(p, 105.0)   # price dipped, but high stays 110
    assert round(s_after_high, 2) == 108.9  # stop unchanged (high-water held)


def test_no_trailing_before_plus_2pct():
    """Below +2% the stop stays at the fixed initial -1% from entry."""
    p = spec_pos(100.0)
    assert current_stop(p, 100.5) == 99.0   # +0.5% → still initial
    assert current_stop(p, 101.9) == 99.0   # +1.9% → still initial
    assert not p.trailing_active


def test_trailing_activates_exactly_at_2pct():
    p = spec_pos(200.0)
    assert current_stop(p, 203.99) == pytest_approx(200.0 * 0.99)  # +1.995% not yet
    assert not p.trailing_active
    current_stop(p, 204.0)                                          # exactly +2%
    assert p.trailing_active
    assert round(current_stop(p, 204.0), 2) == round(204.0 * 0.99, 2)


def test_immediate_stop_loss():
    """Price drops 1% below entry before any profit → sell."""
    p = spec_pos(100.0)
    assert not should_sell(p, 99.5)    # -0.5% → hold
    assert should_sell(p, 99.0)        # -1% → sell (at stop)
    assert should_sell(p, 98.0)        # -2% → sell


def pytest_approx(x, tol=1e-9):
    class _A:
        def __eq__(self, other): return abs(other - x) <= tol
    return _A()

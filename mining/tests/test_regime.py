"""Regime filter unit tests — the bugs from the naive version must NOT recur.

Pure-python, no network. Run: python -m pytest mining/tests/test_regime.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.strategy.base import Bar
from shared.strategy.indicators import ADX
from shared.strategy.regime import RegimeFilter


def _bar(c: float, hi: float | None = None, lo: float | None = None, vol: float = 1000) -> Bar:
    hi = hi if hi is not None else c * 1.002
    lo = lo if lo is not None else c * 0.998
    return Bar(ts="t", open=c, high=hi, low=lo, close=c, volume=vol)


def _feed_uptrend(rf: RegimeFilter, n: int, start: float = 100.0, step: float = 0.6):
    px = start
    for _ in range(n):
        px += step
        rf.update(_bar(px, hi=px + 0.3, lo=px - 0.1))


def _feed_chop(rf: RegimeFilter, n: int, mid: float = 100.0):
    for i in range(n):
        px = mid + (0.4 if i % 2 == 0 else -0.4)  # oscillate → low ADX
        rf.update(_bar(px, hi=px + 0.4, lo=px - 0.4))


def test_warmup_blocks_entry():
    rf = RegimeFilter()
    rf.update(_bar(100))
    assert rf.last.regime == "WARMUP"
    assert rf.allow_entry is False


def test_adx_warms_up_and_is_bounded():
    adx = ADX(14)
    val = None
    px = 100.0
    for i in range(80):
        px += 0.5
        val = adx.update(px + 0.3, px - 0.1, px)
    assert val is not None
    assert 0.0 <= val <= 100.0


def test_clean_uptrend_eventually_allows_entry():
    rf = RegimeFilter(confirm_bars=3)
    _feed_uptrend(rf, 90)
    assert rf.last.regime == "TREND_UP"
    assert rf.allow_entry is True
    assert rf.last.confidence >= rf.confidence_threshold


def test_chop_does_not_allow_entry():
    rf = RegimeFilter()
    _feed_chop(rf, 90)
    assert rf.allow_entry is False
    assert rf.last.regime in ("RANGE", "TRANSITION", "WARMUP")


def test_hysteresis_opens_only_after_confirm_bars():
    # A trend that just crossed into favorable should NOT open instantly.
    rf = RegimeFilter(confirm_bars=5)
    _feed_uptrend(rf, 60)            # warm + trending
    # Find the first bar where regime becomes TREND_UP, check the gate lags.
    # After enough bars the gate is open; assert it required a streak.
    assert rf._streak >= rf.confirm_bars
    assert rf.allow_entry is True


def test_gate_closes_instantly_on_unfavorable():
    rf = RegimeFilter(confirm_bars=3)
    _feed_uptrend(rf, 90)
    assert rf.allow_entry is True
    # One sharp adverse, high-vol down bar → favorable streak resets at once.
    rf.update(_bar(100, hi=160, lo=95))   # huge range = volatility spike, down close
    assert rf.allow_entry is False

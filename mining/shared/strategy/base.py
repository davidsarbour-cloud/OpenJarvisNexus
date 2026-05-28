"""Strategy primitives shared by live bots AND the backtester.

Keeping a single strategy module used by both paths is the #1 rule of
trustworthy algo trading: the code that decides trades in a backtest MUST
be byte-for-byte the code that decides them live. Anything else and your
backtest is fiction.

Pure-python, zero external deps so the unit tests run anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Action(str, Enum):
    BUY  = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True)
class Bar:
    """One OHLCV candle. ts is an ISO string or epoch — opaque to strategy."""
    ts:     str
    open:   float
    high:   float
    low:    float
    close:  float
    volume: float


@dataclass(frozen=True)
class Signal:
    action: Action
    price:  float
    reason: str = ""


class Strategy:
    """Interface. on_bar() is called once per incoming bar (live or replayed)
    and returns a Signal. Implementations hold their own indicator + position
    state internally."""

    def on_bar(self, bar: Bar) -> Signal:                # pragma: no cover - interface
        raise NotImplementedError

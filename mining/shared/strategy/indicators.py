"""Streaming technical indicators — pure python, O(1) per update.

Each indicator keeps a bounded rolling window so it works identically on a
live tick stream and on a historical replay. No numpy/pandas dependency so
the strategy + tests stay portable and instant.
"""
from __future__ import annotations

from collections import deque


class ROC:
    """Rate of change over `period` bars — momentum proxy. Returns % change
    of close vs the close `period` bars ago. None until warmed up."""
    def __init__(self, period: int = 10):
        self.period = period
        self._buf: deque[float] = deque(maxlen=period + 1)

    def update(self, close: float) -> float | None:
        self._buf.append(close)
        if len(self._buf) <= self.period:
            return None
        past = self._buf[0]
        if past == 0:
            return None
        return (close - past) / past * 100.0


class EMA:
    """Exponential moving average. None until first value seeds it."""
    def __init__(self, period: int):
        self.period = period
        self.k = 2.0 / (period + 1)
        self.value: float | None = None

    def update(self, x: float) -> float | None:
        self.value = x if self.value is None else (x - self.value) * self.k + self.value
        return self.value


class VolumeRatio:
    """Current volume / rolling average volume. >1.5 ≈ a volume spike.
    None until the window is full."""
    def __init__(self, period: int = 20):
        self.period = period
        self._buf: deque[float] = deque(maxlen=period)

    def update(self, volume: float) -> float | None:
        ratio: float | None = None
        if len(self._buf) == self.period:
            avg = sum(self._buf) / self.period
            ratio = (volume / avg) if avg > 0 else None
        self._buf.append(volume)
        return ratio


class ATR:
    """Average True Range over `period` — volatility. Uses Wilder smoothing.
    None until warmed up. Caller feeds (high, low, prev_close)."""
    def __init__(self, period: int = 14):
        self.period = period
        self._trs: deque[float] = deque(maxlen=period)
        self._atr: float | None = None
        self._prev_close: float | None = None

    def update(self, high: float, low: float, close: float) -> float | None:
        if self._prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self._prev_close), abs(low - self._prev_close))
        self._prev_close = close
        if self._atr is None:
            self._trs.append(tr)
            if len(self._trs) == self.period:
                self._atr = sum(self._trs) / self.period
        else:
            # Wilder smoothing
            self._atr = (self._atr * (self.period - 1) + tr) / self.period
        return self._atr


class Trend:
    """Fast EMA vs slow EMA. up() True when fast > slow (uptrend)."""
    def __init__(self, fast: int = 9, slow: int = 21):
        self.fast = EMA(fast)
        self.slow = EMA(slow)

    def update(self, close: float) -> tuple[float | None, float | None]:
        return self.fast.update(close), self.slow.update(close)

    def up(self) -> bool:
        return (
            self.fast.value is not None
            and self.slow.value is not None
            and self.fast.value > self.slow.value
        )

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


class ADX:
    """Average Directional Index (Wilder) — trend STRENGTH, not direction.

    ADX >= 25 ≈ a real trend, < 18 ≈ chop/range. Pure streaming, O(1)/bar.
    None until warmed up (~2*period bars: period to seed DI, period to seed ADX).
    Caller feeds (high, low, close) each bar.
    """
    def __init__(self, period: int = 14):
        self.period = period
        self._ph: float | None = None   # prev high / low / close
        self._pl: float | None = None
        self._pc: float | None = None
        self._tr = self._pdm = self._ndm = 0.0   # Wilder-smoothed sums
        self._seed = 0
        self._smoothed = False
        self._dx: deque[float] = deque(maxlen=period)
        self._adx: float | None = None

    def update(self, high: float, low: float, close: float) -> float | None:
        if self._pc is None:
            self._ph, self._pl, self._pc = high, low, close
            return None
        tr = max(high - low, abs(high - self._pc), abs(low - self._pc))
        up_move = high - self._ph
        dn_move = self._pl - low
        pdm = up_move if (up_move > dn_move and up_move > 0) else 0.0
        ndm = dn_move if (dn_move > up_move and dn_move > 0) else 0.0
        self._ph, self._pl, self._pc = high, low, close

        if not self._smoothed:
            self._tr += tr
            self._pdm += pdm
            self._ndm += ndm
            self._seed += 1
            if self._seed < self.period:
                return None
            self._smoothed = True
        else:
            self._tr = self._tr - self._tr / self.period + tr
            self._pdm = self._pdm - self._pdm / self.period + pdm
            self._ndm = self._ndm - self._ndm / self.period + ndm

        if self._tr == 0:
            return self._adx
        pdi = 100.0 * self._pdm / self._tr
        ndi = 100.0 * self._ndm / self._tr
        denom = pdi + ndi
        dx = 100.0 * abs(pdi - ndi) / denom if denom else 0.0
        self._dx.append(dx)
        if self._adx is None:
            if len(self._dx) == self.period:
                self._adx = sum(self._dx) / self.period
        else:
            self._adx = (self._adx * (self.period - 1) + dx) / self.period
        return self._adx


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

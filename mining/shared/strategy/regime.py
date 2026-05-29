"""Market regime filter — pure-python streaming, reuses the project indicators.

Goal (long-only momentum): only ENTER when the market is actually trending up;
sit in cash during chop / high-vol / panic. This formalises what the entry
filter already does implicitly — validated by the 2022 bear test, where the
strategy protected by simply staying out (findings §11b). It is NOT a
multi-strategy router (we have one strategy) and it NEVER changes position size
(sizing stays at the risk-manager's 1-2%, findings §8).

Fixes over the naive version that prompted this:
  - the confidence threshold is ACTUALLY enforced (one clean knob on ADX);
  - asymmetric hysteresis: the gate flips OFF instantly (safety) but only ON
    after `confirm_bars` consecutive favorable bars (no entry whipsaw);
  - PANIC is classified BEFORE HIGH_VOL (never shadowed);
  - explicit WARMUP until indicators are ready (no NaN / silent misclassify);
  - O(1) per bar, no pandas — identical code live and in backtest.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .base import Bar
from .indicators import ADX, ATR, Trend


@dataclass(frozen=True)
class RegimeState:
    regime: str          # WARMUP | TREND_UP | RANGE | HIGH_VOL | PANIC | TRANSITION
    confidence: float    # 0..1 (ADX-driven trend strength)
    allow_entry: bool    # the gate the strategy reads (after hysteresis)


class RegimeFilter:
    def __init__(
        self,
        adx_period: int = 14,
        atr_period: int = 14,
        ema_fast: int = 9,
        ema_slow: int = 21,
        adx_range: float = 18.0,          # below → labelled RANGE
        atr_vol_mult: float = 1.8,        # ATR above avg*mult → high volatility
        atr_avg_period: int = 20,
        confidence_threshold: float = 0.5,  # min ADX/50 to allow a long (0.5 ≈ ADX 25)
        confirm_bars: int = 3,            # consecutive favorable bars before gate opens
    ):
        self.adx = ADX(adx_period)
        self.atr = ATR(atr_period)
        self.trend = Trend(ema_fast, ema_slow)
        self._atr_hist: deque[float] = deque(maxlen=atr_avg_period)
        self._prev_close: float | None = None
        self.adx_range = adx_range
        self.atr_vol_mult = atr_vol_mult
        self.confidence_threshold = confidence_threshold
        self.confirm_bars = confirm_bars
        self._streak = 0
        self.last = RegimeState("WARMUP", 0.0, False)

    @property
    def allow_entry(self) -> bool:
        return self.last.allow_entry

    def update(self, bar: Bar) -> RegimeState:
        adx = self.adx.update(bar.high, bar.low, bar.close)
        atr = self.atr.update(bar.high, bar.low, bar.close)
        self.trend.update(bar.close)
        if atr is not None:
            self._atr_hist.append(atr)
        ret = 0.0
        if self._prev_close:
            ret = (bar.close - self._prev_close) / self._prev_close
        self._prev_close = bar.close

        if (adx is None or atr is None
                or len(self._atr_hist) < self._atr_hist.maxlen
                or self.trend.fast.value is None or self.trend.slow.value is None):
            self._streak = 0
            self.last = RegimeState("WARMUP", 0.0, False)
            return self.last

        avg_atr = sum(self._atr_hist) / len(self._atr_hist)
        up = self.trend.up()
        high_vol = atr > avg_atr * self.atr_vol_mult
        confidence = min(adx / 50.0, 1.0)

        # Classify — PANIC before HIGH_VOL so a crash is never mislabelled.
        if high_vol and not up and ret < 0:
            regime = "PANIC"
        elif high_vol:
            regime = "HIGH_VOL"
        elif adx < self.adx_range:
            regime = "RANGE"
        elif up and confidence >= self.confidence_threshold:
            regime = "TREND_UP"
        else:
            regime = "TRANSITION"

        favorable = regime == "TREND_UP"
        # Asymmetric hysteresis: open slowly, close instantly.
        self._streak = self._streak + 1 if favorable else 0
        allow = self._streak >= self.confirm_bars

        self.last = RegimeState(regime, round(confidence, 2), allow)
        return self.last

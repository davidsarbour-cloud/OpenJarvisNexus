"""Momentum + dynamic trailing-stop strategy — the core IP.

Entry  : momentum up (ROC) + volume spike + uptrend (EMA fast>slow) +
         volatility not excessive (ATR/price bounded).
Exit   : David's exact trailing rules —
           - initial stop  : -1% below entry
           - at +2%        : trailing activates
           - trailing      : stop = -1% below the high-water mark (ratchet)
           - sell when price <= current stop

The Position + stop math is isolated and exhaustively unit-tested
(tests/test_trailing_stop.py) because it's the part that directly moves
money. The strategy wrapper feeds bars and translates to Signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import Action, Bar, Signal, Strategy
from .indicators import ATR, ROC, Trend, VolumeRatio

# ── Tunable parameters (strategy-ai service may suggest new values) ──────────
INITIAL_STOP_PCT = 0.01   # -1% below entry
ACTIVATE_TP_PCT  = 0.02   # +2% high-water → trailing activates
TRAIL_PCT        = 0.01   # -1% below the high-water mark

# Entry filters
MIN_ROC          = 0.30   # min % rate-of-change to call it momentum
MIN_VOLUME_RATIO = 1.30   # current vol vs avg → spike threshold
MAX_ATR_PCT      = 5.0    # skip if ATR > 5% of price (too volatile)


@dataclass
class Position:
    entry:           float
    qty:             float
    high_water:      float = 0.0
    trailing_active: bool  = False
    # Stop params carried per-position so the backtester's param sweep can
    # vary them. Defaults = the module constants → existing callers and
    # tests keep the exact -1%/+2%/-1% behaviour.
    initial_stop_pct: float = INITIAL_STOP_PCT
    activate_tp_pct:  float = ACTIVATE_TP_PCT
    trail_pct:        float = TRAIL_PCT

    def __post_init__(self):
        if self.high_water == 0.0:
            self.high_water = self.entry


def current_stop(pos: Position, price: float) -> float:
    """Effective stop for `pos` at `price`. Monotonic non-decreasing.

    Mutates pos.high_water and pos.trailing_active (intended — the stop
    ratchets as new highs print). Matches David's worked example exactly:
      entry 100 -> 99.00 ; price 102 -> 100.98 ; price 105 -> 103.95.
    """
    pos.high_water = max(pos.high_water, price)
    if pos.high_water >= pos.entry * (1 + pos.activate_tp_pct):
        pos.trailing_active = True
    if pos.trailing_active:
        return pos.high_water * (1 - pos.trail_pct)
    return pos.entry * (1 - pos.initial_stop_pct)


def should_sell(pos: Position, price: float) -> bool:
    return price <= current_stop(pos, price)


# ── OHLC-aware primitives (used by the historical backtester) ────────────────
# Live bots get a tick STREAM, so current_stop(price) updates the high-water
# on every tick. A historical OHLC bar hides the intrabar path, so the
# backtester reasons about high/low separately and pessimistically. These
# pure helpers expose the state transitions without the tick coupling.

def stop_price(pos: Position) -> float:
    """Current stop from EXISTING state — pure, no mutation."""
    if pos.trailing_active:
        return pos.high_water * (1 - pos.trail_pct)
    return pos.entry * (1 - pos.initial_stop_pct)


def update_high_water(pos: Position, price: float) -> None:
    """Ratchet the high-water mark and arm trailing once +TP% is reached."""
    pos.high_water = max(pos.high_water, price)
    if pos.high_water >= pos.entry * (1 + pos.activate_tp_pct):
        pos.trailing_active = True


@dataclass
class MomentumTrailing(Strategy):
    """Per-ticker strategy instance. Holds indicator + position state.

    `sentiment_ok` is a hook the live bot sets from the Ollama sentiment
    signal (Redis `sentiment:{TICKER}`); in backtest it stays True.
    """
    ticker:        str
    roc_period:    int = 10
    vol_period:    int = 20
    atr_period:    int = 14
    sentiment_ok:  bool = True
    # Tunable filters + stop params (sweepable). Defaults = module constants.
    min_roc:          float = MIN_ROC
    min_volume_ratio: float = MIN_VOLUME_RATIO
    max_atr_pct:      float = MAX_ATR_PCT
    initial_stop_pct: float = INITIAL_STOP_PCT
    activate_tp_pct:  float = ACTIVATE_TP_PCT
    trail_pct:        float = TRAIL_PCT

    roc:   ROC         = field(init=False)
    vol:   VolumeRatio = field(init=False)
    atr:   ATR         = field(init=False)
    trend: Trend       = field(init=False)
    position: Position | None = field(default=None, init=False)

    def __post_init__(self):
        self.roc   = ROC(self.roc_period)
        self.vol   = VolumeRatio(self.vol_period)
        self.atr   = ATR(self.atr_period)
        self.trend = Trend()

    # ── Entry decision ──────────────────────────────────────────────────────
    def entry_signal(self, bar: Bar, roc, vol_ratio, atr) -> bool:
        if not self.sentiment_ok:
            return False
        if roc is None or vol_ratio is None or atr is None:
            return False                                   # not warmed up
        atr_pct = (atr / bar.close * 100.0) if bar.close else 999
        return (
            roc >= self.min_roc
            and vol_ratio >= self.min_volume_ratio
            and self.trend.up()
            and atr_pct <= self.max_atr_pct
        )

    # ── Per-bar tick ─────────────────────────────────────────────────────────
    def on_bar(self, bar: Bar) -> Signal:
        roc       = self.roc.update(bar.close)
        vol_ratio = self.vol.update(bar.volume)
        atr       = self.atr.update(bar.high, bar.low, bar.close)
        self.trend.update(bar.close)

        if self.position is None:
            if self.entry_signal(bar, roc, vol_ratio, atr):
                return Signal(Action.BUY, bar.close, reason="momentum+volume+trend")
            return Signal(Action.HOLD, bar.close)

        # In a position → manage the trailing stop
        stop = current_stop(self.position, bar.close)
        if bar.close <= stop:
            return Signal(Action.SELL, bar.close,
                          reason=f"stop hit @ {stop:.2f} (high {self.position.high_water:.2f})")
        return Signal(Action.HOLD, bar.close, reason=f"trailing stop {stop:.2f}")

    # ── Position lifecycle (called by backtester/bot on fills) ───────────────
    def open_position(self, entry: float, qty: float) -> None:
        self.position = Position(
            entry=entry, qty=qty,
            initial_stop_pct=self.initial_stop_pct,
            activate_tp_pct=self.activate_tp_pct,
            trail_pct=self.trail_pct,
        )

    def close_position(self) -> None:
        self.position = None

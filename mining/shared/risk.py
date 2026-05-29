"""Centralised risk manager — the safety core.

PURE decision functions (state passed in) so they're unit-testable and behave
identically in backtest and live. Workers NEVER execute directly: they emit an
order intent, and `approve_buy` here is the single chokepoint that says yes/no
and sizes the order.

Embeds the backtest lessons:
  - size at risk_per_trade_pct (1-2%), NOT 100% — survive the gap (§8)
  - daily-loss circuit breaker — stop the bleeding
  - per-day trade cap — PDT-aware, anti-overtrading (§7)
  - cooldown after a loss — no revenge trading
  - total exposure cap — never all-in across tickers
Selling (flattening) is ALWAYS allowed — reducing risk is never blocked.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from shared.config import RiskLimits


@dataclass
class DayState:
    """Per-day cluster state. Persist to Postgres; rebuild on boot."""
    start_equity:  float
    equity:        float
    trades_today:  dict[str, int]   = field(default_factory=dict)  # ticker -> buy count
    last_loss_ts:  dict[str, float] = field(default_factory=dict)  # ticker -> epoch of last losing exit
    open_exposure: dict[str, float] = field(default_factory=dict)  # ticker -> $ notional held


@dataclass(frozen=True)
class Decision:
    ok:     bool
    reason: str
    qty:    float = 0.0


def approve_buy(ticker: str, price: float, state: DayState, limits: RiskLimits,
                halted: bool, now: float | None = None,
                earnings_days: float | None = None) -> Decision:
    """The single gate every BUY passes through. Returns sized Decision.

    `earnings_days` = days until the ticker's next earnings (None/<0 = unknown).
    New entries are blocked inside the blackout window — earnings gaps are the
    backtest's #1 account-killer (findings §5) and no stop protects against them.
    """
    now = now if now is not None else time.time()

    if halted:
        return Decision(False, "global circuit breaker active")

    if earnings_days is not None and 0 <= earnings_days <= limits.earnings_blackout_days:
        return Decision(False, f"earnings blackout ({earnings_days:.0f}d to earnings)")

    dd = (state.equity / state.start_equity - 1) * 100 if state.start_equity else 0.0
    if dd <= -limits.max_daily_loss_pct:
        return Decision(False, f"daily loss limit hit ({dd:.1f}%)")

    if state.trades_today.get(ticker, 0) >= limits.max_trades_per_day:
        return Decision(False, "max trades/day reached")

    last = state.last_loss_ts.get(ticker)
    if last is not None and (now - last) < limits.cooldown_min_after_loss * 60:
        return Decision(False, "cooldown after loss")

    total_exp = sum(state.open_exposure.values())
    if state.equity and (total_exp / state.equity * 100) >= limits.max_total_exposure_pct:
        return Decision(False, "total exposure cap")

    # sizing: risk_per_trade % of equity, never above the per-position cap
    notional = min(
        state.equity * limits.risk_per_trade_pct / 100.0,
        state.equity * limits.max_position_pct / 100.0,
    )
    qty = round(notional / price, 4) if price else 0.0
    if qty <= 0:
        return Decision(False, "size rounds to zero")
    return Decision(True, "approved", qty)


def register_fill(state: DayState, ticker: str, side: str, qty: float,
                  price: float, pnl: float = 0.0) -> None:
    """Mutate day state after a confirmed fill."""
    if side == "buy":
        state.trades_today[ticker] = state.trades_today.get(ticker, 0) + 1
        state.open_exposure[ticker] = state.open_exposure.get(ticker, 0.0) + qty * price
    else:  # sell / flatten
        state.open_exposure[ticker] = 0.0
        state.equity += pnl
        if pnl < 0:
            state.last_loss_ts[ticker] = time.time()

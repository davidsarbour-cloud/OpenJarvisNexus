"""Deterministic backtester — replays historical bars through the SAME
strategy module the live bots use. No Alpaca, no money, no network.

Models fills at the signal bar's close (optimistic but consistent), one
position at a time per strategy instance. Reports the metrics that matter
for judging an edge: total return, win rate, profit factor, max drawdown,
trade count, avg win/loss.

Run:
    python -m mining.services.backtester.backtester        # synthetic demo
    (or import run_backtest and feed your own bars)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# Allow `python backtester.py` standalone (adds mining/ to path)
_MINING_ROOT = Path(__file__).resolve().parents[2]
if str(_MINING_ROOT) not in sys.path:
    sys.path.insert(0, str(_MINING_ROOT))

from shared.strategy.base import Action, Bar  # noqa: E402
from shared.strategy.momentum_trailing import MomentumTrailing  # noqa: E402


@dataclass
class Trade:
    entry_ts:   str
    entry:      float
    exit_ts:    str
    exit:       float
    qty:        float
    reason:     str

    @property
    def pnl(self) -> float:
        return (self.exit - self.entry) * self.qty

    @property
    def pnl_pct(self) -> float:
        return (self.exit - self.entry) / self.entry * 100.0 if self.entry else 0.0


@dataclass
class BacktestResult:
    trades:        list[Trade] = field(default_factory=list)
    equity_curve:  list[float] = field(default_factory=list)
    start_equity:  float = 10_000.0

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> list[Trade]:
        return [t for t in self.trades if t.pnl > 0]

    @property
    def losses(self) -> list[Trade]:
        return [t for t in self.trades if t.pnl <= 0]

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades)

    @property
    def win_rate(self) -> float:
        return (len(self.wins) / self.n_trades * 100.0) if self.n_trades else 0.0

    @property
    def profit_factor(self) -> float:
        gross_win  = sum(t.pnl for t in self.wins)
        gross_loss = abs(sum(t.pnl for t in self.losses))
        return (gross_win / gross_loss) if gross_loss else float("inf")

    @property
    def max_drawdown_pct(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for eq in self.equity_curve:
            peak = max(peak, eq)
            dd = (peak - eq) / peak * 100.0 if peak else 0.0
            max_dd = max(max_dd, dd)
        return max_dd

    def summary(self) -> str:
        return (
            f"trades={self.n_trades}  win_rate={self.win_rate:.1f}%  "
            f"PnL=${self.total_pnl:.2f}  PF={self.profit_factor:.2f}  "
            f"maxDD={self.max_drawdown_pct:.1f}%  "
            f"end_equity=${self.start_equity + self.total_pnl:.2f}"
        )


def run_backtest(
    bars: list[Bar],
    ticker: str = "TEST",
    start_equity: float = 10_000.0,
    risk_per_trade_pct: float = 0.10,   # 10% of equity per position (paper sizing)
) -> BacktestResult:
    """Replay `bars` through MomentumTrailing. One position at a time."""
    strat = MomentumTrailing(ticker)
    res = BacktestResult(start_equity=start_equity)
    equity = start_equity
    open_entry: float = 0.0
    open_ts: str = ""
    open_qty: float = 0.0

    for bar in bars:
        sig = strat.on_bar(bar)
        if sig.action == Action.BUY and strat.position is None:
            notional = equity * risk_per_trade_pct
            qty = round(notional / bar.close, 4) if bar.close else 0
            if qty > 0:
                strat.open_position(bar.close, qty)
                open_entry, open_ts, open_qty = bar.close, bar.ts, qty
        elif sig.action == Action.SELL and strat.position is not None:
            trade = Trade(open_ts, open_entry, bar.ts, bar.close, open_qty, sig.reason)
            res.trades.append(trade)
            equity += trade.pnl
            strat.close_position()
        res.equity_curve.append(equity + _unrealized(strat, bar.close))

    return res


def _unrealized(strat: MomentumTrailing, price: float) -> float:
    if strat.position is None:
        return 0.0
    return (price - strat.position.entry) * strat.position.qty


# ── Synthetic demo data (so the module runs with zero external deps) ─────────
def _synthetic_bars(n: int = 300, seed: int = 7) -> list[Bar]:
    """A trending-then-choppy series to exercise entries + trailing exits."""
    import math
    import random
    rng = random.Random(seed)
    bars: list[Bar] = []
    price = 100.0
    for i in range(n):
        # Regime: rally for first third, chop, then a pump+dump to trip trailing
        drift = 0.25 if i < n // 3 else (-0.05 if i < 2 * n // 3 else 0.4 * math.sin(i / 5))
        price = max(1.0, price * (1 + drift / 100 + rng.uniform(-0.4, 0.4) / 100))
        high  = price * (1 + abs(rng.uniform(0, 0.6)) / 100)
        low   = price * (1 - abs(rng.uniform(0, 0.6)) / 100)
        vol   = rng.uniform(800, 1200) * (2.0 if (i % 37 == 0) else 1.0)  # periodic spikes
        bars.append(Bar(ts=f"t{i}", open=price, high=high, low=low, close=price, volume=vol))
    return bars


if __name__ == "__main__":
    bars = _synthetic_bars()
    result = run_backtest(bars, ticker="DEMO")
    print(f"[backtest DEMO] {len(bars)} bars")
    print(result.summary())
    for t in result.trades[:10]:
        print(f"  {t.entry_ts}->{t.exit_ts}  {t.entry:.2f}->{t.exit:.2f}  "
              f"{t.pnl_pct:+.2f}%  ({t.reason})")

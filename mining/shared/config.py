"""Central config for the Mining cluster — single source of truth.

Every service imports SETTINGS. Risk defaults embed the backtest LESSONS:
size at 1-2%/trade (NOT 100% — gap survival), a daily-loss circuit breaker,
a per-day trade cap (PDT-aware), and a cooldown after losses (anti-overtrading).
Live trading is double-gated (see `live_enabled`).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _f(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _i(name: str, default: str) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class RiskLimits:
    max_daily_loss_pct:      float = _f("MINING_MAX_DAILY_LOSS_PCT", "3.0")   # halt the day if equity down this %
    max_trades_per_day:      int   = _i("MINING_MAX_TRADES_PER_DAY", "20")    # per ticker (PDT-aware)
    max_position_pct:        float = _f("MINING_MAX_POSITION_PCT", "20.0")    # % of equity in one ticker
    max_total_exposure_pct:  float = _f("MINING_MAX_EXPOSURE_PCT", "80.0")    # % across all tickers
    cooldown_min_after_loss: int   = _i("MINING_COOLDOWN_MIN", "15")          # no re-entry for N min after a loss
    risk_per_trade_pct:      float = _f("MINING_RISK_PER_TRADE_PCT", "2.0")   # sizing — NEVER 100% (findings §8)


@dataclass(frozen=True)
class StrategyParams:
    # Validated defaults (findings §1 / walk-forward §9 + §11c). Stop 1.5%, not 2%.
    initial_stop_pct: float = _f("MINING_INITIAL_STOP_PCT", "0.015")
    activate_tp_pct:  float = _f("MINING_ACTIVATE_TP_PCT", "0.03")
    trail_pct:        float = _f("MINING_TRAIL_PCT", "0.01")
    min_roc:          float = _f("MINING_MIN_ROC", "0.30")
    min_volume_ratio: float = _f("MINING_MIN_VOLUME_RATIO", "1.50")
    max_atr_pct:      float = _f("MINING_MAX_ATR_PCT", "5.0")


@dataclass(frozen=True)
class Settings:
    tickers:       tuple[str, ...] = tuple(
        t.strip().upper() for t in os.getenv("MINING_TICKERS", "ASML,TSLA,INTC,NVDA,AMD").split(",") if t.strip()
    )
    mode:          str = os.getenv("ALPACA_MODE", "paper").lower()          # paper | live
    live_ack:      bool = os.getenv("I_UNDERSTAND_LIVE_RISK", "no").lower() == "yes"
    redis_url:     str = os.getenv("MINING_REDIS_URL", "redis://localhost:6379/0")
    postgres_url:  str = os.getenv("MINING_POSTGRES_URL", "postgresql://mining:mining@localhost:5432/mining")
    ollama_url:    str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model:  str = os.getenv("MINING_OLLAMA_MODEL", "qwen3:14b")
    anthropic_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    alpaca_key:    str = os.getenv("ALPACA_API_KEY", "")
    alpaca_secret: str = os.getenv("ALPACA_API_SECRET", "")
    finnhub_key:   str = os.getenv("FINNHUB_API_KEY", "")
    risk:          RiskLimits = field(default_factory=RiskLimits)
    strategy:      StrategyParams = field(default_factory=StrategyParams)

    @property
    def live_enabled(self) -> bool:
        """Live requires BOTH the mode flag AND the explicit human ack."""
        return self.mode == "live" and self.live_ack


SETTINGS = Settings()

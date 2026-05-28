# MINING — Real-Time AI Trading System

Real-time AI trading cluster for Nexus9, connected to Alpaca. New planet
**MINING** + `/world/mining` dashboard. Full architecture in the BRAIN
vault: `03_Projects/Mining/mining-architecture.md`.

## ⚠️ SAFETY — read before running anything live

This system places orders automatically. It is **paper-trading by default**.
Live trading requires TWO explicit env flags:

```
ALPACA_MODE=live
I_UNDERSTAND_LIVE_RISK=yes
```

Without both, every order routes to the Alpaca **paper** endpoint (fake
money). Backtest results are NOT live results. Run paper for weeks before
even considering live. Not financial advice.

## Build status — phased

- [x] **Phase 1** — strategy + trailing stop + backtester + tests (this commit)
- [ ] Phase 2 — market-data (Alpaca WS → Redis) + 1 bot (NVDA) paper + risk-manager
- [ ] Phase 3 — dashboard-api + /world/mining + planet
- [ ] Phase 4 — 5 bots + sentiment (Ollama)
- [ ] Phase 5 — strategy-ai tuning + Telegram monitoring
- [ ] Phase 6 — live gate (only after weeks of clean paper)

## Phase 1 — what's here

```
mining/
├── shared/strategy/
│   ├── base.py               # Bar, Signal, Strategy interface
│   ├── indicators.py         # ROC, EMA, VolumeRatio, ATR, Trend (pure python)
│   └── momentum_trailing.py  # Position + trailing stop + entry signal  ← core IP
├── services/backtester/
│   └── backtester.py         # deterministic replay (same strategy as live)
└── tests/                    # 10 tests, trailing-stop math + backtester
```

The live bots (Phase 2+) and the backtester import the SAME
`shared/strategy/` module — the cardinal rule of trustworthy algo trading:
the code that decides trades in backtest is byte-for-byte the live code.

## Run Phase 1

```pwsh
# From repo root, using the backend venv:
cd mining

# Backtest demo on synthetic data:
C:\OpenJarvisNexus\backend\.venv\Scripts\python.exe services\backtester\backtester.py

# Tests:
C:\OpenJarvisNexus\backend\.venv\Scripts\python.exe -m pytest tests\ -q
```

## Trailing stop rules (the core)

```
entry 100  → stop 99.00      (initial -1%)
price 102  → stop 100.98     (+2% activates trailing : 102×0.99)
price 105  → stop 103.95     (ratchet : 105×0.99, never moves down)
price < trailing stop → SELL
```

Exhaustively tested in `tests/test_trailing_stop.py`.

## Stack (Phase 2+)

Python · FastAPI · Redis (pub/sub ticks + order stream) · PostgreSQL
(orders/fills/PnL/audit) · Alpaca API · WebSockets · Docker. AI on Ollama
(qwen3:14b) for sentiment + param tuning — ~$0, no Claude needed.

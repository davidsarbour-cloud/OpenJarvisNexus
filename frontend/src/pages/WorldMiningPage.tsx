/**
 * Nexus9 — World · Mining (AI trading).
 *
 * Thin wrapper around <WorldShell>. The gold mining accent + the
 * trading card mix is declared here; the dashboard mechanics live in
 * the shell. See backend/mining + the brain note
 * 03_Projects/Mining/mining-backtest-findings.md for the strategy.
 *
 * NOTE: cards are placeholders. The momentum+trailing strategy is
 * validated on backtest data only (yfinance). No live broker link is
 * wired and per the findings nothing should go live before a regime
 * filter + bear-market test + months of paper trading.
 */
import {
  Activity, Bot, CandlestickChart, Coins, Gauge, LineChart,
  Newspaper, ShieldAlert, TrendingDown, Wallet,
} from 'lucide-react';
import { NamedSatellite } from '../components/CommandCenter/FunctionalSatellites';
import { WorldShell, type CardDef, type PlacedCard } from '../components/WorldShell/WorldShell';

const TradingBots   = () => <NamedSatellite title="TRADING BOTS"   colorKey="mining" />;
const OpenPositions = () => <NamedSatellite title="OPEN POSITIONS" colorKey="mining" />;
const DailyPnl      = () => <NamedSatellite title="DAILY P&L"      colorKey="mining" />;
const TrailingStop  = () => <NamedSatellite title="TRAILING STOP"  colorKey="mining" />;
const Backtest      = () => <NamedSatellite title="BACKTEST"       colorKey="mining" />;
const AlpacaLink    = () => <NamedSatellite title="ALPACA LINK"    colorKey="mining" />;
const RiskGuard     = () => <NamedSatellite title="RISK GUARD"     colorKey="mining" />;
const Watchlist     = () => <NamedSatellite title="WATCHLIST"      colorKey="mining" />;
const WalkForward   = () => <NamedSatellite title="WALK-FORWARD"   colorKey="mining" />;
const Sentiment     = () => <NamedSatellite title="SENTIMENT"      colorKey="mining" />;

type CardType =
  | 'bots' | 'positions' | 'pnl' | 'trailingstop' | 'backtest'
  | 'alpaca' | 'risk' | 'watchlist' | 'walkforward' | 'sentiment';

const CARD_REGISTRY: Record<CardType, CardDef> = {
  bots:         { label: 'TRADING BOTS',  sub: '5 ticker bots',              icon: Bot,              Card: TradingBots   },
  positions:    { label: 'OPEN POSITIONS',sub: 'Live positions + exposure',  icon: Wallet,           Card: OpenPositions },
  pnl:          { label: 'DAILY P&L',     sub: 'Realized + unrealized',      icon: LineChart,        Card: DailyPnl      },
  trailingstop: { label: 'TRAILING STOP', sub: 'Validated stop params',      icon: TrendingDown,     Card: TrailingStop  },
  backtest:     { label: 'BACKTEST',      sub: 'Historical performance',     icon: CandlestickChart, Card: Backtest      },
  alpaca:       { label: 'ALPACA LINK',   sub: 'Broker connection',          icon: Activity,         Card: AlpacaLink    },
  risk:         { label: 'RISK GUARD',    sub: 'Position sizing',            icon: ShieldAlert,      Card: RiskGuard     },
  watchlist:    { label: 'WATCHLIST',     sub: 'Tracked instruments',        icon: Coins,            Card: Watchlist     },
  walkforward:  { label: 'WALK-FORWARD',  sub: 'OOS robustness',             icon: Gauge,            Card: WalkForward   },
  sentiment:    { label: 'SENTIMENT',     sub: 'News / Reddit / X',          icon: Newspaper,        Card: Sentiment     },
};

// First-visit layout: backtest + config on the left, live/paper telemetry
// on the right. User can rearrange; persisted to localStorage afterwards.
const DEFAULT_SEEDS: PlacedCard<CardType>[] = [
  { id: 'seed-backtest',  type: 'backtest',     side: 'left',  height: 240 },
  { id: 'seed-trail',     type: 'trailingstop', side: 'left',  height: 240 },
  { id: 'seed-watchlist', type: 'watchlist',    side: 'left',  height: 200 },
  { id: 'seed-bots',      type: 'bots',         side: 'right', height: 240 },
  { id: 'seed-positions', type: 'positions',    side: 'right', height: 200 },
  { id: 'seed-pnl',       type: 'pnl',          side: 'right', height: 200 },
];

export function WorldMiningPage() {
  return (
    <WorldShell
      colorKey="mining"
      imageCandidates={['/world/mining.webp', '/world/mining.png', '/world/mining.jpg']}
      imageAlt="Mining — AI Trading & Markets"
      storageKey="nexus9.world-mining.layout"
      cardRegistry={CARD_REGISTRY}
      defaultSeeds={DEFAULT_SEEDS}
      worldLabel="Mining"
    />
  );
}

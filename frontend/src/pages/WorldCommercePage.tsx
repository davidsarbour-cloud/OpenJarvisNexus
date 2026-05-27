/**
 * Nexus9 — World · Commerce.
 *
 * Thin wrapper around <WorldShell>. Declares the commerce-specific
 * card registry and image candidates; the dashboard mechanics
 * (docking, resize, flip, layout persistence) live in the shell.
 */
import { CheckCircle, DollarSign, Package, PieChart, ShoppingCart, TrendingUp } from 'lucide-react';
import { BudgetCard } from '../components/CommandCenter/BudgetCard';
import { NamedSatellite, LiveSatellite } from '../components/CommandCenter/FunctionalSatellites';
import { WorldShell, type CardDef } from '../components/WorldShell/WorldShell';

const CommerceTracker    = () => <NamedSatellite title="COMMERCE TRACKER"     colorKey="commerce" />;
const AnalyticsProbe     = () => <NamedSatellite title="ANALYTICS PROBE"      colorKey="commerce" />;
const EtsyOrders         = () => <NamedSatellite title="ETSY ORDERS"          colorKey="commerce" />;
const ApprovalQueue      = () => <LiveSatellite  title="APPROVAL QUEUE"       colorKey="commerce" snapshotKey="approval_queue" />;
const ListingPerformance = () => <NamedSatellite title="LISTING PERFORMANCE"  colorKey="commerce" />;
const TokenBudget        = () => <LiveSatellite  title="TOKEN BUDGET"         colorKey="commerce" snapshotKey="token_budget" />;

type CardType =
  | 'budget' | 'tracker' | 'analytics' | 'orders' | 'approval' | 'listing' | 'tokens';

const CARD_REGISTRY: Record<CardType, CardDef> = {
  budget:    { label: 'BUDGET FLOW',         sub: 'Token spend',            icon: DollarSign,   Card: BudgetCard          },
  tracker:   { label: 'COMMERCE TRACKER',    sub: 'Etsy / Shopify sales',   icon: ShoppingCart, Card: CommerceTracker     },
  analytics: { label: 'ANALYTICS PROBE',     sub: 'Module stats',           icon: PieChart,     Card: AnalyticsProbe      },
  orders:    { label: 'ETSY ORDERS',         sub: "Today's orders + $",     icon: Package,      Card: EtsyOrders          },
  approval:  { label: 'APPROVAL QUEUE',      sub: 'Awaiting human OK',      icon: CheckCircle,  Card: ApprovalQueue       },
  listing:   { label: 'LISTING PERFORMANCE', sub: 'Views · favs · convert', icon: TrendingUp,   Card: ListingPerformance  },
  tokens:    { label: 'TOKEN BUDGET',        sub: 'Anthropic $ today',      icon: DollarSign,   Card: TokenBudget         },
};

export function WorldCommercePage() {
  return (
    <WorldShell
      colorKey="commerce"
      imageCandidates={['/world/commerce.webp', '/world/commerce.png', '/world/commerce.jpg']}
      imageAlt="Commerce — Marketplace Operations"
      storageKey="nexus9.world-commerce.layout"
      cardRegistry={CARD_REGISTRY}
      worldLabel="Commerce"
    />
  );
}

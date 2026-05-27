import { motion } from 'motion/react';
import {
  CloudUpload, Activity, ShoppingCart, Bell, PieChart, Network,
  Settings, Layers, Brain, FileText, Megaphone, Wrench,
  // Extra-card icons
  Sparkles, Box, Printer, Package, CheckCircle, TrendingUp,
  Thermometer, AlertTriangle, Gauge, BookOpen, Unlink, Sun,
  HardDrive, Terminal, MessageSquare, GitFork, DollarSign,
} from 'lucide-react';
import { cssVar, MODULE_COLORS, type ModuleKey } from '../../lib/colors';

type IconType = React.ComponentType<{ size?: number; style?: React.CSSProperties }>;

interface Satellite {
  title: string;
  desc: string;
  colorKey: ModuleKey;
  icon: IconType;
  status: 'active' | 'standby';
  metrics: [{ label: string; value: string }, { label: string; value: string }];
}

const SATELLITES: Satellite[] = [
  { title: 'BACKUP', desc: 'Automatically triggers pipeline or file backups', colorKey: 'jarvis', icon: CloudUpload, status: 'active',
    metrics: [{ label: 'LAST RUN', value: '10:15 AM' }, { label: 'NEXT RUN', value: '11:00 AM' }] },
  { title: 'PIPELINE MONITOR', desc: 'Shows real-time pipeline status', colorKey: 'vault', icon: Activity, status: 'active',
    metrics: [{ label: 'PIPELINES', value: '12' }, { label: 'FAILURES', value: '0' }] },
  { title: 'COMMERCE TRACKER', desc: 'Tracks Shopify / Etsy sales', colorKey: 'forge', icon: ShoppingCart, status: 'active',
    metrics: [{ label: "TODAY'S SALES", value: '$12,540' }, { label: 'ORDERS', value: '156' }] },
  { title: 'NOTIFICATION BEACON', desc: 'Alerts / system messages', colorKey: 'cyberdeck', icon: Bell, status: 'active',
    metrics: [{ label: 'UNREAD', value: '4' }, { label: 'SENT TODAY', value: '32' }] },
  { title: 'ANALYTICS PROBE', desc: 'Collects stats for modules', colorKey: 'jarvis', icon: PieChart, status: 'active',
    metrics: [{ label: 'DATA POINTS', value: '8.42K' }, { label: 'ACCURACY', value: '99.1%' }] },
  { title: 'TEST DRONE', desc: 'Runs automated STL / code checks', colorKey: 'commerce', icon: Network, status: 'active',
    metrics: [{ label: 'TESTS RUN', value: '45' }, { label: 'PASSED', value: '44' }] },
  { title: 'OPTIMIZER DRONE', desc: 'Tweak pipelines / STL orientation / parameters', colorKey: 'forge', icon: Settings, status: 'active',
    metrics: [{ label: 'OPTIMIZATIONS', value: '23' }, { label: 'IMPROVEMENT', value: '18%' }] },
  { title: 'CACHE RELAY', desc: 'Speeds up access to frequently used assets', colorKey: 'docker', icon: Layers, status: 'active',
    metrics: [{ label: 'HIT RATE', value: '92.4%' }, { label: 'SAVED', value: '3.2GB' }] },
  { title: 'AI RESEARCH PROBE', desc: 'Collects suggestions / improvements for ULTRON & Cortana', colorKey: 'cortex', icon: Brain, status: 'active',
    metrics: [{ label: 'SUGGESTIONS', value: '128' }, { label: 'IMPLEMENTED', value: '17' }] },
  { title: 'EVENT LOGGER', desc: 'Captures logs of all actions across system', colorKey: 'jarvis', icon: FileText, status: 'active',
    metrics: [{ label: 'LOGS TODAY', value: '18,732' }, { label: 'ERRORS', value: '2' }] },
  { title: 'NOTIFICATION AMPLIFIER', desc: 'Highlights priority alerts / critical events', colorKey: 'security', icon: Megaphone, status: 'standby',
    metrics: [{ label: 'PRIORITY', value: 'HIGH' }, { label: 'FILTERS', value: '7' }] },
  { title: 'MAINTENANCE DRONE', desc: 'Checks system health / resource usage / errors', colorKey: 'docker', icon: Wrench, status: 'active',
    metrics: [{ label: 'SYSTEM HEALTH', value: '98.7%' }, { label: 'ISSUES', value: '0' }] },

  // ── Forge extras ─────────────────────────────────────────────────────────
  { title: 'MESHY CREDITS', desc: 'Meshy AI API quota — generation tokens left', colorKey: 'forge', icon: Sparkles, status: 'active',
    metrics: [{ label: 'CREDITS', value: '847' }, { label: 'DAYS LEFT', value: '~14' }] },
  { title: 'STL OUTPUT', desc: 'Recent STL files exported from the Forge pipeline', colorKey: 'forge', icon: Box, status: 'active',
    metrics: [{ label: 'TODAY', value: '4' }, { label: 'SUCCESS', value: '92%' }] },
  { title: 'BAMBU QUEUE', desc: 'Bambu Lab printer status + current print ETA', colorKey: 'forge', icon: Printer, status: 'standby',
    metrics: [{ label: 'STATUS', value: 'IDLE' }, { label: 'LAST PRINT', value: '2h ago' }] },

  // ── Commerce extras ──────────────────────────────────────────────────────
  { title: 'ETSY ORDERS', desc: "Today's Etsy orders + revenue + top product", colorKey: 'commerce', icon: Package, status: 'active',
    metrics: [{ label: 'ORDERS', value: '12' }, { label: 'REVENUE', value: '$387' }] },
  { title: 'APPROVAL QUEUE', desc: 'Commerce pipelines waiting for human approval', colorKey: 'commerce', icon: CheckCircle, status: 'active',
    metrics: [{ label: 'PENDING', value: '3' }, { label: 'OLDEST', value: '47m' }] },
  { title: 'LISTING PERFORMANCE', desc: 'Top listings — views, favs, conversion rate', colorKey: 'commerce', icon: TrendingUp, status: 'active',
    metrics: [{ label: 'TOP VIEWS', value: '482' }, { label: 'CONV', value: '4.2%' }] },
  { title: 'TOKEN BUDGET', desc: 'Anthropic API spend today + monthly projection', colorKey: 'commerce', icon: DollarSign, status: 'active',
    metrics: [{ label: 'SPENT', value: '$4.27' }, { label: 'BUDGET', value: '30%' }] },

  // ── Cyberdeck extras ─────────────────────────────────────────────────────
  { title: 'GPU TEMP', desc: 'RTX 4070 Super temperature + utilization', colorKey: 'cyberdeck', icon: Thermometer, status: 'active',
    metrics: [{ label: 'TEMP', value: '62°C' }, { label: 'UTIL', value: '78%' }] },
  { title: 'ERROR LOG TAIL', desc: 'Last backend errors — click to open log file', colorKey: 'cyberdeck', icon: AlertTriangle, status: 'active',
    metrics: [{ label: '24H', value: '4' }, { label: 'LAST', value: '47m' }] },
  { title: 'API RATE LIMITS', desc: 'Remaining quota: Anthropic · Meshy · Etsy', colorKey: 'cyberdeck', icon: Gauge, status: 'active',
    metrics: [{ label: 'ANTHROPIC', value: '87%' }, { label: 'MESHY', value: '64%' }] },
  { title: 'TELEGRAM ACTIVITY', desc: 'Last David ↔ JARVIS messages via Telegram bot', colorKey: 'cyberdeck', icon: MessageSquare, status: 'active',
    metrics: [{ label: 'MESSAGES', value: '31' }, { label: 'LAST', value: '12m' }] },
  { title: 'MODEL ROUTING', desc: 'Which agents handled which queries today', colorKey: 'cyberdeck', icon: GitFork, status: 'active',
    metrics: [{ label: 'ROUTED', value: '142' }, { label: 'CLAUDE', value: '56%' }] },

  // ── Vault extras ─────────────────────────────────────────────────────────
  { title: 'VAULT GROWTH', desc: 'Notes added today / week — total Obsidian count', colorKey: 'vault', icon: BookOpen, status: 'active',
    metrics: [{ label: 'TODAY', value: '12' }, { label: 'TOTAL', value: '1.4K' }] },
  { title: 'ORPHAN ALERT', desc: 'Notes with no [[backlinks]] — auto-fix dimanche 02:30', colorKey: 'vault', icon: Unlink, status: 'active',
    metrics: [{ label: 'ORPHANS', value: '7' }, { label: 'LAST FIX', value: '5d' }] },
  { title: 'MORNING BRIEF', desc: 'Daily brief auto-generated at 07:30 in BRAIN/02_Daily', colorKey: 'vault', icon: Sun, status: 'active',
    metrics: [{ label: 'GENERATED', value: '07:30' }, { label: 'ITEMS', value: '8' }] },

  // ── Docker extras ────────────────────────────────────────────────────────
  { title: 'DISK USAGE', desc: 'Drive C: free space + output folder sizes', colorKey: 'docker', icon: HardDrive, status: 'active',
    metrics: [{ label: 'FREE', value: '218GB' }, { label: 'USED', value: '47%' }] },
  { title: 'CONTAINER LOGS', desc: 'Live tail — last N lines from selected container', colorKey: 'docker', icon: Terminal, status: 'active',
    metrics: [{ label: 'ACTIVE', value: '13' }, { label: 'ERRORS', value: '0' }] },

  // ── Global digest (Command Center) ───────────────────────────────────────
  { title: 'DAILY DIGEST', desc: 'Top-line cross-world summary — STL · Notes · Errors', colorKey: 'jarvis', icon: PieChart, status: 'active',
    metrics: [{ label: 'STL · NOTES', value: '0 · 0' }, { label: 'ERRORS 24H', value: '0' }] },
];

function hexA(hex: string, a: number): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

const VALUE_COLOR = '#e3edfa';

function SatelliteCard({ sat }: { sat: Satellite }) {
  const c = cssVar(sat.colorKey);
  const mc = MODULE_COLORS[sat.colorKey];
  const Icon = sat.icon;
  // Healthy = world accent (passed via sat.colorKey from NamedSatellite),
  // standby/offline = solid black.
  const isHealthy = sat.status === 'active';
  const statusColor = isHealthy ? c : '#000000';
  const statusGlow  = isHealthy ? mc.glow : 'rgba(0,0,0,0.8)';
  const statusTitle = isHealthy ? 'Active' : 'Standby';

  return (
    <motion.div
      className="flex flex-col p-3 relative overflow-hidden"
      style={{
        background: `radial-gradient(130% 80% at 50% 0%, ${mc.subtle}, transparent 62%), var(--hud-bg-elev)`,
        border: `1px solid ${hexA(mc.hex, 0.28)}`,
        boxShadow: 'inset 0 0 24px rgba(0,0,0,0.45)',
        minHeight: 152,
      }}
      whileHover={{
        scale: 1.02,
        boxShadow: `inset 0 0 24px rgba(0,0,0,0.45), 0 0 22px -6px ${mc.glow}`,
      }}
      transition={{ type: 'spring', stiffness: 320, damping: 22 }}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <Icon size={16} style={{ color: c }} />
        <span className="text-[11px] font-bold tracking-[0.16em]" style={{ color: c }}>
          {sat.title}
        </span>
      </div>

      {/* Description */}
      <div className="text-[9px] leading-snug mt-1" style={{ color: 'var(--hud-text-dim)', minHeight: 24 }}>
        {sat.desc}
      </div>

      <div className="flex-1" />

      {/* Status dot — top-right, tiny, room-coloured (or black if standby) */}
      <span
        aria-label={statusTitle}
        title={statusTitle}
        className="absolute"
        style={{
          top: 8, right: 8,
          width: 7, height: 7, borderRadius: '50%',
          background: statusColor,
          boxShadow: `0 0 6px ${statusGlow}`,
          border: isHealthy ? 'none' : '1px solid var(--hud-border)',
        }}
      />

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--hud-border)' }} className="mb-2" />

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-2">
        {sat.metrics.map((m, i) => (
          <div key={i} className="flex flex-col min-w-0">
            <span className="text-[8px] tracking-[0.14em] truncate" style={{ color: 'var(--hud-text-dim)' }}>
              {m.label}
            </span>
            <span className="text-[15px] font-bold tabular-nums truncate" style={{ color: VALUE_COLOR, lineHeight: 1.25 }}>
              {m.value}
            </span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

/**
 * SatelliteCards — Command Center system module cards (backup, monitors,
 * drones, probes) as bare grid items, so they share the same grid as the
 * live service cards. Static showcase data for now.
 */
export function SatelliteCards() {
  return (
    <>
      {SATELLITES.map((sat) => (
        <SatelliteCard key={sat.title} sat={sat} />
      ))}
    </>
  );
}

/**
 * NamedSatellite — render a single satellite by its title.
 *   - `colorKey`     overrides the default tint (re-theme per world)
 *   - `status`       overrides the static status (live wrappers feed it)
 *   - `liveMetrics`  overrides the 2 static metrics with fetched values
 */
export function NamedSatellite({
  title, colorKey, status, liveMetrics,
}: {
  title:        string;
  colorKey?:    ModuleKey;
  status?:      'active' | 'standby';
  liveMetrics?: [{ label: string; value: string }, { label: string; value: string }] | { label: string; value: string }[];
}) {
  const sat = SATELLITES.find((s) => s.title === title);
  if (!sat) return null;
  const themed: Satellite = { ...sat };
  if (colorKey) themed.colorKey = colorKey;
  if (status)   themed.status   = status;
  if (liveMetrics && liveMetrics.length >= 2) {
    themed.metrics = [liveMetrics[0], liveMetrics[1]] as Satellite['metrics'];
  }
  return <SatelliteCard sat={themed} />;
}

/**
 * LiveSatellite — wraps NamedSatellite with a poll on the world-cards
 * snapshot endpoint. Falls back to the satellite's static metrics until
 * the first response arrives.
 */
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchWorldCardsSnapshot, type WorldCardsSnapshotData } from '../../lib/apiLive';

export function LiveSatellite({
  title, colorKey, snapshotKey,
}: {
  title:       string;
  colorKey:    ModuleKey;
  snapshotKey: keyof Omit<WorldCardsSnapshotData, 'generated_at'>;
}) {
  const { data } = useLiveMetric(fetchWorldCardsSnapshot, { intervalMs: 30000, wsTopic: 'snapshot/world-cards' });
  const card = data?.[snapshotKey];
  return (
    <NamedSatellite
      title={title}
      colorKey={colorKey}
      status={card?.status}
      liveMetrics={card?.metrics}
    />
  );
}

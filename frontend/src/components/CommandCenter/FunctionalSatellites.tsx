import { motion } from 'motion/react';
import {
  CloudUpload, Activity, ShoppingCart, Bell, PieChart, Network,
  Settings, Layers, Brain, FileText, Megaphone, Wrench,
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
  const statusColor = sat.status === 'active' ? 'var(--color-docker)' : 'var(--color-security)';
  const statusLabel = sat.status === 'active' ? 'ACTIVE' : 'STANDBY';

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

      {/* Status */}
      <div className="flex items-center gap-1.5 mb-2">
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0"
          style={{ background: statusColor, boxShadow: `0 0 6px ${statusColor}` }}
        />
        <span className="text-[9px] font-bold tracking-[0.2em]" style={{ color: statusColor }}>
          {statusLabel}
        </span>
      </div>

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

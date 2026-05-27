import { useContext, type ReactNode } from 'react';
import { motion } from 'motion/react';
import type { ModuleKey } from '../../lib/colors';
import { cssVar, MODULE_COLORS } from '../../lib/colors';
import { CardAccentContext } from './cardAccentContext';

export type { ModuleKey };
export { CardAccentContext };
export type CardStatus = 'live' | 'demo' | 'warn' | 'down' | 'loading';

// Healthy statuses use the world's accent (forge orange, vault violet,
// commerce teal, cyberdeck red, docker green, jarvis cyan — see
// CardAccentContext). Down/warn = solid black to read as "offline".
const HEALTHY: Record<CardStatus, boolean> = {
  live:    true,
  demo:    true,
  loading: true,
  warn:    false,
  down:    false,
};

const DOT_LABEL: Record<CardStatus, string> = {
  live:    'live',
  demo:    'demo',
  loading: 'loading',
  warn:    'warning',
  down:    'offline',
};

/**
 * HudCard — shared chrome for every Command Center card.
 * Phase 6: animated hover (Framer Motion) with scale + module-tinted glow.
 * Phase 7: status badge replaced by a small green/red dot; colorKey can
 * be overridden by an ancestor via CardAccentContext (world re-theming).
 */
export function HudCard({
  title, subtitle, colorKey, icon: Icon, status, children,
}: {
  title: string;
  subtitle?: string;
  colorKey: ModuleKey;
  icon: React.ComponentType<{ size?: number; style?: React.CSSProperties }>;
  status: CardStatus;
  children: ReactNode;
}) {
  const ctxAccent = useContext(CardAccentContext);
  const effectiveKey: ModuleKey = ctxAccent ?? colorKey;
  const c = cssVar(effectiveKey);
  const glow = MODULE_COLORS[effectiveKey].glow;
  const isHealthy = HEALTHY[status];
  const dot = isHealthy ? c : '#000000';
  const dotGlow = isHealthy ? glow : 'rgba(0,0,0,0.8)';
  const dotBorder = isHealthy ? 'none' : '1px solid var(--hud-border)';

  return (
    <motion.div
      className="flex flex-col p-3 relative"
      style={{
        background: 'var(--hud-bg-elev)',
        border: '1px solid var(--hud-border)',
        borderTop: `2px solid ${c}`,
        boxShadow: 'inset 0 0 24px rgba(0,0,0,0.4)',
        minHeight: 140,
      }}
      whileHover={{
        scale: 1.015,
        boxShadow: `inset 0 0 24px rgba(0,0,0,0.4), 0 0 20px -4px ${glow}`,
      }}
      transition={{ type: 'spring', stiffness: 320, damping: 22 }}
    >
      {/* Status dot — tiny, top-right. Healthy = room colour, down = black */}
      <span
        aria-label={`Card status: ${DOT_LABEL[status]}`}
        title={DOT_LABEL[status]}
        className="absolute"
        style={{
          top: 8,
          right: 8,
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: dot,
          boxShadow: `0 0 6px ${dotGlow}`,
          border: dotBorder,
        }}
      />

      <div className="flex items-center gap-2 mb-0.5">
        <Icon size={14} style={{ color: c }} />
        <span className="text-[10px] font-bold tracking-[0.22em]" style={{ color: c }}>
          {title.toUpperCase()}
        </span>
      </div>
      {subtitle && (
        <div className="text-[9px] tracking-wider mb-2" style={{ color: 'var(--hud-text-dim)' }}>
          {subtitle}
        </div>
      )}

      <div className="flex-1 flex flex-col justify-end">
        {children}
      </div>
    </motion.div>
  );
}

/** Big numeric value, used by most cards. */
export function CardValue({
  value, unit, colorKey,
}: {
  value: string | number;
  unit?: string;
  colorKey: ModuleKey;
}) {
  const ctxAccent = useContext(CardAccentContext);
  const effectiveKey: ModuleKey = ctxAccent ?? colorKey;
  const c = cssVar(effectiveKey);
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-3xl font-bold tabular-nums" style={{ color: c, lineHeight: 1 }}>
        {value}
      </span>
      {unit && (
        <span className="text-[10px] tracking-wider" style={{ color: 'var(--hud-text-dim)' }}>
          {unit}
        </span>
      )}
    </div>
  );
}

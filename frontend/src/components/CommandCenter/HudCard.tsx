import type { ReactNode } from 'react';
import { motion } from 'motion/react';
import type { ModuleKey } from '../../lib/colors';
import { cssVar, MODULE_COLORS } from '../../lib/colors';

export type CardStatus = 'live' | 'demo' | 'warn' | 'down' | 'loading';

const STATUS_STYLE: Record<CardStatus, { label: string; color: string }> = {
  live:    { label: 'LIVE',    color: 'var(--color-docker)' },
  demo:    { label: 'DEMO',    color: 'var(--hud-text-dim)' },
  warn:    { label: 'WARN',    color: 'var(--color-security)' },
  down:    { label: 'DOWN',    color: 'var(--color-cyberdeck)' },
  loading: { label: '…',       color: 'var(--color-jarvis)' },
};

/**
 * HudCard — shared chrome for every Command Center card.
 * Phase 6: animated hover (Framer Motion) with scale + module-tinted glow.
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
  const c = cssVar(colorKey);
  const glow = MODULE_COLORS[colorKey].glow;
  const s = STATUS_STYLE[status];
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
      <span
        className="absolute top-1.5 right-1.5 text-[8px] font-bold tracking-[0.18em] px-1.5 py-0.5"
        style={{
          color: s.color,
          border: `1px solid ${s.color}`,
          background: 'rgba(0,0,0,0.3)',
          borderRadius: 1,
        }}
      >
        {s.label}
      </span>

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
  const c = cssVar(colorKey);
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

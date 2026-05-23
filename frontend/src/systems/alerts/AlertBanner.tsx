/**
 * Nexus9 — Tactical alert banner.
 *
 * Renders the *most recent unacknowledged* alert as a thin pulsing strip
 * across the top of the HUD. Click to acknowledge.
 *
 * Mount in HudLayout (or App.tsx) once.
 */
import { motion, AnimatePresence } from 'motion/react';
import { AlertTriangle, X } from 'lucide-react';
import { useNexusStore, useActiveAlerts } from '../nexusStore';
import { ALERT_STYLE } from './types';
import { getService } from '../serviceRegistry';

export function AlertBanner() {
  const alerts = useActiveAlerts();
  const ack = useNexusStore((s) => s.acknowledgeAlert);
  const top = alerts[0];

  return (
    <AnimatePresence>
      {top && (
        <motion.div
          key={top.id}
          initial={{ y: -32, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -32, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 320, damping: 26 }}
          className="fixed top-0 left-0 right-0 z-50 flex items-center gap-2 px-4 py-1.5"
          style={{
            background: 'rgba(0,0,0,0.85)',
            borderBottom: `1px solid ${ALERT_STYLE[top.level].cssVar}`,
            boxShadow: `0 0 24px -4px ${ALERT_STYLE[top.level].cssVar}`,
          }}
        >
          <motion.span
            animate={
              ALERT_STYLE[top.level].pulse
                ? { opacity: [1, 0.4, 1] }
                : { opacity: 1 }
            }
            transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
            style={{ color: ALERT_STYLE[top.level].cssVar }}
          >
            <AlertTriangle size={14} />
          </motion.span>

          <span
            className="text-[10px] font-bold tracking-[0.22em] px-1.5"
            style={{ color: ALERT_STYLE[top.level].cssVar }}
          >
            {ALERT_STYLE[top.level].label}
          </span>

          <span
            className="text-[10px] tracking-wider"
            style={{ color: 'var(--hud-text-dim)' }}
          >
            {(getService(top.source)?.label ?? top.source).toUpperCase()}
          </span>

          <span
            className="text-[11px] flex-1 truncate"
            style={{ color: 'var(--hud-text)' }}
          >
            {top.title}
          </span>

          {alerts.length > 1 && (
            <span
              className="text-[9px] tracking-wider px-1.5 py-0.5"
              style={{
                color: 'var(--hud-text-dim)',
                border: '1px solid var(--hud-border)',
              }}
            >
              +{alerts.length - 1} more
            </span>
          )}

          <button
            onClick={() => ack(top.id)}
            className="ml-1 p-1 hover:bg-white/5 rounded-sm"
            aria-label="Acknowledge alert"
            style={{ color: 'var(--hud-text-dim)' }}
          >
            <X size={12} />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

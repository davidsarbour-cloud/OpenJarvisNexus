/**
 * Nexus9 — Alert types (Phase 4 · Step 6)
 */

export type AlertLevel = 'info' | 'warning' | 'critical' | 'ai';

export interface Alert {
  id: string;
  /** Severity. */
  level: AlertLevel;
  /** Service that raised the alert (must match a ServiceDef.id). */
  source: string;
  /** Headline shown in banner / sidebar. */
  title: string;
  /** Optional longer detail. */
  detail?: string;
  /** Ms since epoch. */
  createdAt: number;
  /** When true, hidden from banner but still in history (until pruned). */
  acknowledged: boolean;
}

export const ALERT_STYLE: Record<
  AlertLevel,
  { label: string; cssVar: string; pulse: boolean }
> = {
  info:     { label: 'INFO',     cssVar: 'var(--color-jarvis)',    pulse: false },
  warning:  { label: 'WARN',     cssVar: 'var(--color-security)',  pulse: true  },
  critical: { label: 'CRITICAL', cssVar: 'var(--color-cyberdeck)', pulse: true  },
  ai:       { label: 'AI ALERT', cssVar: 'var(--color-cortex)',    pulse: true  },
};

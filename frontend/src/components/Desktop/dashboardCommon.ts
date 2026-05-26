/**
 * Shared palette + base styles for the Desktop dashboards
 * (EnergyDashboard, SavingsDashboard, …). Catppuccin-flavored.
 *
 * Each dashboard layers its own file-specific styles on top via
 * `{ ...dashboardStyles, customKey: { … } }`.
 */
import type React from 'react';

export const dashboardColors = {
  bg:           '#1e1e2e',
  surface:      '#282840',
  surfaceHover: '#313150',
  text:         '#cdd6f4',
  textMuted:    '#a6adc8',
  accent:       '#89b4fa',
  green:        '#a6e3a1',
  yellow:       '#f9e2af',
  red:          '#f38ba8',
  purple:       '#cba6f7',
  border:       '#45475a',
} as const;

const c = dashboardColors;

export const dashboardStyles: Record<string, React.CSSProperties> = {
  container: {
    background:  c.bg,
    color:       c.text,
    padding:     24,
    fontFamily:  "'Inter', 'Segoe UI', system-ui, sans-serif",
    height:      '100%',
    overflowY:   'auto',
    boxSizing:   'border-box',
  },
  header: {
    display:        'flex',
    justifyContent: 'space-between',
    alignItems:     'center',
    marginBottom:   24,
  },
  title: {
    fontSize:   22,
    fontWeight: 600,
    margin:     0,
    color:      c.text,
  },
  liveBadge: {
    display:      'inline-flex',
    alignItems:   'center',
    gap:          6,
    fontSize:     12,
    color:        c.green,
    background:   'rgba(166,227,161,0.1)',
    padding:      '4px 10px',
    borderRadius: 12,
    fontWeight:   500,
  },
  liveDot: {
    width:        6,
    height:       6,
    borderRadius: '50%',
    background:   c.green,
    animation:    'pulse 2s infinite',
  },
  statsGrid: {
    display:             'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap:                 16,
    marginBottom:        24,
  },
  statCard: {
    background:   c.surface,
    borderRadius: 10,
    padding:      16,
    border:       `1px solid ${c.border}`,
  },
  statLabel: {
    fontSize:       12,
    color:          c.textMuted,
    marginBottom:   6,
    textTransform:  'uppercase',
    letterSpacing:  '0.05em',
  },
  statValue: {
    fontSize:   26,
    fontWeight: 700,
    color:      c.accent,
    lineHeight: 1.1,
  },
  statUnit: {
    fontSize:   13,
    fontWeight: 400,
    color:      c.textMuted,
    marginLeft: 4,
  },
};

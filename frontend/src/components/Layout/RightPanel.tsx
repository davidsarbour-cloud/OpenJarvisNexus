import { AlertTriangle, Info, Zap, BookOpen } from 'lucide-react';
import { motion } from 'motion/react';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { useWsEvents } from '../../hooks/useWsEvents';
import { fetchLogs, fetchAgents, fetchCrewJobs, type LogEntry } from '../../lib/apiLive';
import type { WsEvent } from '../../lib/ws';

// ── Obsidian deep-link helper ──────────────────────────────────────────────

const OBSIDIAN_VAULT = 'BRAIN';

/** Build the obsidian://open URL and navigate. */
function openObsidian(notePath: string) {
  const url = `obsidian://open?vault=${encodeURIComponent(OBSIDIAN_VAULT)}&file=${encodeURIComponent(notePath)}`;
  window.open(url, '_self');
}

type Event = {
  id: string | number;
  ts: string;
  level: 'info' | 'warn' | 'alert';
  source: string;
  msg: string;
  /** Optional Obsidian note path (relative to BRAIN vault root). When
   *  present, the row becomes a clickable button that opens the note
   *  via obsidian://open. Used by completion events from scheduled
   *  skill jobs + manual skill activations. */
  note?: string;
};

// Single neutral placeholder used only when both WS and /v1/logs are empty
// (e.g. backend just restarted, no events emitted yet). Avoids the previous
// 5-item mock list that looked like real activity.
const SEED: Event[] = [
  { id: 's0', ts: '——:——:——', level: 'info', source: 'NEXUS', msg: 'awaiting events — scheduler will emit on next fire' },
];

/**
 * RightPanel — Phase 7: 3-tier event source.
 *   1. WebSocket  /ws/events    (real-time, preferred)
 *   2. HTTP poll  /v1/logs      (fallback, every 4s)
 *   3. Mock seed                (last resort if both empty)
 */
export function RightPanel() {
  const ws = useWsEvents(50);
  const { data: logsData } = useLiveMetric(fetchLogs,    { intervalMs: 4000 });
  const { data: agentsData } = useLiveMetric(fetchAgents, { intervalMs: 8000, wsTopic: 'snapshot/agents' });
  const { data: jobsData } = useLiveMetric(fetchCrewJobs, { intervalMs: 6000, wsTopic: 'snapshot/jobs' });

  const wsEvents = mapWs(ws.events);
  const httpEvents = mapLogs(logsData?.logs ?? []);

  let events: Event[];
  let badge: 'WS LIVE' | 'HTTP LIVE' | 'MOCK';
  if (ws.connected && wsEvents.length > 0) {
    events = wsEvents;
    badge = 'WS LIVE';
  } else if (httpEvents.length > 0) {
    events = httpEvents;
    badge = 'HTTP LIVE';
  } else {
    events = SEED;
    badge = 'MOCK';
  }

  const agents = agentsData?.agents ?? [];
  const onlineAgents = agents.filter(a => a.status === 'online').length;
  const jobs = jobsData?.jobs ?? [];
  const activeJobs = jobs.filter(j => String(j.status).toLowerCase() === 'running').length;
  const alerts = events.filter(e => e.level !== 'info').length;

  return (
    <aside
      className="flex flex-col shrink-0 overflow-hidden"
      style={{
        width: 280,
        background: 'var(--hud-bg-elev)',
        borderLeft: '1px solid var(--hud-border)',
      }}
    >
      <SectionHeader title="ALERTS & EVENTS" badge={badge} wsState={ws.state} />

      <div className="flex-1 overflow-y-auto px-2 py-2 flex flex-col gap-1">
        {events.map((e) => <EventRow key={e.id} event={e} />)}
        <div className="mt-2 text-[9px] tracking-[0.18em] text-center py-2" style={{ color: 'var(--hud-text-dim)' }}>
          [ {badge === 'WS LIVE' ? '/ws/events · realtime'
            : badge === 'HTTP LIVE' ? '/v1/logs · 4s poll'
            : 'mock seed (no source)'} ]
        </div>
      </div>

      <SectionHeader title="QUICK STATS" border="top" />
      <div className="grid grid-cols-2 gap-2 p-3">
        <StatBox label="MISSIONS"   value={String(jobs.length)}    colorKey="forge" />
        <StatBox label="AGENTS"     value={String(onlineAgents)}   colorKey="jarvis" />
        <StatBox label="ACTIVE JOB" value={String(activeJobs)}     colorKey="vault" />
        <StatBox label="ALERTS"     value={String(alerts)}         colorKey="cyberdeck" pulse={alerts > 0} />
      </div>
    </aside>
  );
}

function normalizeLevel(raw: unknown): Event['level'] {
  const s = String(raw ?? 'info').toLowerCase();
  if (s === 'error' || s === 'alert' || s === 'critical') return 'alert';
  if (s === 'warn'  || s === 'warning') return 'warn';
  return 'info';
}

function mapLogs(logs: LogEntry[]): Event[] {
  return logs.slice(0, 50).map((l, i) => ({
    id: `http-${i}`,
    ts: String(l.ts ?? '').slice(11, 19) || '——:——:——',
    level: normalizeLevel(l.level),
    source: String(l.source ?? 'NEXUS'),
    msg: String(l.msg ?? ''),
    note: typeof l.note === 'string' ? l.note : undefined,
  }));
}

function mapWs(events: WsEvent[]): Event[] {
  return events.slice(0, 50).map((e, i) => ({
    id: `ws-${i}-${e.ts ?? ''}`,
    ts: String(e.ts ?? '').slice(11, 19) || '——:——:——',
    level: normalizeLevel(e.level),
    source: String(e.source ?? 'NEXUS'),
    msg: String(e.msg ?? ''),
    note: typeof e.note === 'string' ? e.note : undefined,
  }));
}

function SectionHeader({
  title, badge, border = 'bottom', wsState,
}: {
  title: string;
  badge?: 'WS LIVE' | 'HTTP LIVE' | 'MOCK';
  border?: 'top' | 'bottom';
  wsState?: 'connecting' | 'open' | 'closed' | 'error';
}) {
  const palette: Record<string, string> = {
    'WS LIVE':   'var(--color-docker)',
    'HTTP LIVE': 'var(--color-jarvis)',
    'MOCK':      'var(--hud-text-dim)',
  };
  const c = badge ? palette[badge] : 'var(--hud-text-dim)';
  return (
    <div
      className="px-3 py-2 text-[9px] font-bold tracking-[0.25em] flex items-center gap-2"
      style={{
        color: 'var(--hud-text-dim)',
        background: 'rgba(0,0,0,0.2)',
        borderTop:    border === 'top'    ? '1px solid var(--hud-border)' : undefined,
        borderBottom: border === 'bottom' ? '1px solid var(--hud-border)' : undefined,
      }}
    >
      <span>── {title}</span>
      {badge && (
        <span
          className="ml-auto px-1.5 py-0.5 flex items-center gap-1"
          style={{ color: c, border: `1px solid ${c}`, fontSize: 8 }}
        >
          {wsState && wsState !== 'open' && badge === 'WS LIVE' && (
            <span className="w-1 h-1 rounded-full" style={{ background: 'var(--color-security)' }} />
          )}
          {badge}
        </span>
      )}
    </div>
  );
}

function EventRow({ event }: { event: Event }) {
  const palette = {
    info:  { c: 'var(--color-jarvis)',    Icon: Info },
    warn:  { c: 'var(--color-security)',  Icon: Zap },
    alert: { c: 'var(--color-cyberdeck)', Icon: AlertTriangle },
  } as const;
  const { c, Icon } = palette[event.level];
  const isAlert = event.level === 'alert';
  const hasNote = !!event.note;
  const handleClick = hasNote ? () => openObsidian(event.note!) : undefined;
  return (
    <motion.div
      className="flex items-start gap-2 px-2 py-1.5 text-[10px] leading-tight"
      style={{
        borderLeft: `2px solid ${c}`,
        background: 'rgba(0,0,0,0.18)',
        cursor: hasNote ? 'pointer' : 'default',
      }}
      initial={isAlert ? { boxShadow: `inset 0 0 0 0 transparent` } : false}
      animate={isAlert ? {
        boxShadow: [
          `inset 0 0 0 0 transparent`,
          `inset 0 0 12px 0 ${c}`,
          `inset 0 0 0 0 transparent`,
        ],
      } : undefined}
      transition={isAlert ? { duration: 2.5, repeat: Infinity, ease: 'easeInOut' } : undefined}
      onClick={handleClick}
      onKeyDown={hasNote ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick?.(); }
      } : undefined}
      role={hasNote ? 'button' : undefined}
      tabIndex={hasNote ? 0 : undefined}
      title={hasNote ? `Open note: ${event.note}` : undefined}
      onMouseEnter={hasNote ? (e) => { e.currentTarget.style.background = 'rgba(0,212,255,0.06)'; } : undefined}
      onMouseLeave={hasNote ? (e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.18)'; } : undefined}
    >
      <Icon size={11} style={{ color: c, marginTop: 1, flexShrink: 0 }} />
      <div className="flex-1 min-w-0">
        <div className="flex gap-2 items-baseline">
          <span style={{ color: 'var(--hud-text-dim)' }}>{event.ts}</span>
          <span style={{ color: c, fontWeight: 700, letterSpacing: '0.1em' }}>{event.source}</span>
        </div>
        <div style={{ color: 'var(--hud-text)' }}>{event.msg}</div>
      </div>
      {hasNote && (
        <BookOpen size={9} style={{ color: 'var(--hud-text-dim)', marginTop: 2, flexShrink: 0 }} aria-hidden />
      )}
    </motion.div>
  );
}

function StatBox({
  label, value, colorKey, pulse = false,
}: {
  label: string; value: string; colorKey: 'forge' | 'jarvis' | 'vault' | 'cyberdeck'; pulse?: boolean;
}) {
  const c = `var(--color-${colorKey})`;
  return (
    <motion.div
      className="flex flex-col items-start px-2 py-2"
      style={{ background: 'rgba(0,0,0,0.18)', border: `1px solid ${c}`, borderRadius: 2 }}
      animate={pulse ? {
        boxShadow: [`0 0 0 0 transparent`, `0 0 14px -2px ${c}`, `0 0 0 0 transparent`],
      } : undefined}
      transition={pulse ? { duration: 1.8, repeat: Infinity, ease: 'easeInOut' } : undefined}
    >
      <span className="text-[8px] tracking-[0.2em]" style={{ color: 'var(--hud-text-dim)' }}>{label}</span>
      <span className="text-lg font-bold tabular-nums" style={{ color: c, lineHeight: 1.1 }}>{value}</span>
    </motion.div>
  );
}

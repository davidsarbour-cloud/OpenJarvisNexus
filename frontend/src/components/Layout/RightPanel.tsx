import { AlertTriangle, Info, Zap, CalendarClock, Sparkles, BookOpen } from 'lucide-react';
import { motion } from 'motion/react';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { useWsEvents } from '../../hooks/useWsEvents';
import {
  fetchLogs, fetchAgents, fetchCrewJobs, fetchScheduledTasks,
  type LogEntry, type ScheduledJob,
} from '../../lib/apiLive';
import type { WsEvent } from '../../lib/ws';

// ── Obsidian wikilink helper ───────────────────────────────────────────────

const OBSIDIAN_VAULT = 'BRAIN';

/** Build the obsidian://open URL and navigate. */
function openObsidian(notePath: string) {
  const url = `obsidian://open?vault=${encodeURIComponent(OBSIDIAN_VAULT)}&file=${encodeURIComponent(notePath)}`;
  window.open(url, '_self');
}

// ── Skill catalog (kept in sync with JarvisSkillsSection) ──────────────────

interface SkillEntry {
  name:     string;
  schedule: 'daily' | 'weekly' | 'manual';
  /** Path under BRAIN/, no leading slash. */
  note:     string;
}

const SKILL_CATALOG: SkillEntry[] = [
  // TOML auto-exec (docker)
  { name: 'docker-health',            schedule: 'daily',   note: '05_Resources/Research/hermes.md' },
  { name: 'docker-logs-check',        schedule: 'manual',  note: '05_Resources/Research/hermes.md' },
  { name: 'docker-stats',             schedule: 'manual',  note: '05_Resources/Research/hermes.md' },
  { name: 'docker-restart-container', schedule: 'manual',  note: '05_Resources/Research/hermes.md' },
  // Hermes protocols
  { name: 'systematic-debugging',     schedule: 'manual',  note: '05_Resources/Research/hermes/systematic-debugging.md' },
  { name: 'humanizer',                schedule: 'manual',  note: '05_Resources/Research/hermes/humanizer.md' },
  { name: 'ideation',                 schedule: 'weekly',  note: '05_Resources/Research/hermes/ideation.md' },
  { name: 'plan',                     schedule: 'manual',  note: '05_Resources/Research/hermes/plan.md' },
  { name: 'codebase-inspection',      schedule: 'weekly',  note: '05_Resources/Research/hermes/codebase-inspection.md' },
  { name: 'obsidian',                 schedule: 'manual',  note: '05_Resources/Research/hermes/obsidian.md' },
  { name: 'blogwatcher',              schedule: 'daily',   note: '05_Resources/Research/hermes/blogwatcher.md' },
  { name: 'polymarket',               schedule: 'daily',   note: '05_Resources/Research/hermes/polymarket.md' },
  { name: 'comfyui',                  schedule: 'manual',  note: '05_Resources/Research/hermes/comfyui.md' },
];

// APScheduler job id → Obsidian note (mirror of ScheduledTasksCard.JOB_OBSIDIAN_PATHS)
const JOB_NOTE: Record<string, string> = {
  trend_hunt:                '07_Schemas/workflows/trend-hunt-schema.md',
  morning_briefing:          '07_Schemas/workflows/morning-briefing-schema.md',
  daily_stl_research:        '07_Schemas/workflows/stl-research-schema.md',
  brain_autolink:            '07_Schemas/workflows/brain-autolink-schema.md',
  skill_docker_health:       '05_Resources/Research/hermes.md',
  skill_blogwatcher:         '05_Resources/Research/hermes/blogwatcher.md',
  skill_polymarket:          '05_Resources/Research/hermes/polymarket.md',
  skill_codebase_inspection: '05_Resources/Research/hermes/codebase-inspection.md',
  skill_ideation:            '05_Resources/Research/hermes/ideation.md',
  skill_polymarket_digest:   '05_Resources/Research/hermes/polymarket.md',
};

type Event = {
  id: string | number;
  ts: string;
  level: 'info' | 'warn' | 'alert';
  source: string;
  msg: string;
};

const SEED: Event[] = [
  { id: 's1', ts: '14:02:11', level: 'info',  source: 'JARVIS',   msg: 'orchestrator ready' },
  { id: 's2', ts: '14:02:14', level: 'info',  source: 'OLLAMA',   msg: 'qwen3:14b loaded' },
  { id: 's3', ts: '14:02:30', level: 'warn',  source: 'FORGE',    msg: 'STL queue backlog (3)' },
  { id: 's4', ts: '14:02:58', level: 'alert', source: 'SECURITY', msg: 'unusual port scan 10.0.0.5' },
  { id: 's5', ts: '14:03:12', level: 'info',  source: 'DOCKER',   msg: 'sonarqube healthy' },
];

/**
 * RightPanel — Phase 7: 3-tier event source.
 *   1. WebSocket  /ws/events    (real-time, preferred)
 *   2. HTTP poll  /v1/logs      (fallback, every 4s)
 *   3. Mock seed                (last resort if both empty)
 */
export function RightPanel() {
  const ws = useWsEvents(50);
  const { data: logsData } = useLiveMetric(fetchLogs,           { intervalMs: 4000 });
  const { data: agentsData } = useLiveMetric(fetchAgents,        { intervalMs: 8000 });
  const { data: jobsData } = useLiveMetric(fetchCrewJobs,        { intervalMs: 6000 });
  const { data: schedData } = useLiveMetric(fetchScheduledTasks, { intervalMs: 60_000 });

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
  const scheduledJobs = schedData?.jobs ?? [];

  return (
    <aside
      className="flex flex-col shrink-0 overflow-hidden"
      style={{
        width: 280,
        background: 'var(--hud-bg-elev)',
        borderLeft: '1px solid var(--hud-border)',
      }}
    >
      {/* ── Runtime alerts + events (WS / HTTP / seed) ─── */}
      <SectionHeader title="ALERTS & EVENTS" badge={badge} wsState={ws.state} />
      <div className="overflow-y-auto px-2 py-2 flex flex-col gap-1" style={{ maxHeight: '30vh' }}>
        {events.slice(0, 15).map((e) => <EventRow key={e.id} event={e} />)}
        <div className="text-[8px] tracking-[0.18em] text-center py-1"
             style={{ color: 'var(--hud-text-dim)' }}>
          [ {badge === 'WS LIVE' ? '/ws/events · realtime'
            : badge === 'HTTP LIVE' ? '/v1/logs · 4s poll'
            : 'mock seed'} ]
        </div>
      </div>

      {/* ── Upcoming scheduled jobs (clickable → schema note) ─── */}
      <SectionHeader title={`SCHEDULE · ${scheduledJobs.length}`} border="top" />
      <div className="overflow-y-auto px-2 py-2 flex flex-col gap-1" style={{ maxHeight: '24vh' }}>
        {scheduledJobs.length === 0 ? (
          <EmptyRow text="aucun job actif" />
        ) : (
          scheduledJobs.map((j) => <ScheduleRow key={j.id} job={j} />)
        )}
      </div>

      {/* ── Skill catalog (clickable → hermes note) ─── */}
      <SectionHeader title={`SKILLS · ${SKILL_CATALOG.length}`} border="top" />
      <div className="overflow-y-auto px-2 py-2 flex flex-col gap-1" style={{ maxHeight: '24vh' }}>
        {SKILL_CATALOG.map((s) => <SkillRow key={s.name} skill={s} />)}
      </div>

      {/* ── Quick stats footer ─── */}
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
  }));
}

function mapWs(events: WsEvent[]): Event[] {
  return events.slice(0, 50).map((e, i) => ({
    id: `ws-${i}-${e.ts ?? ''}`,
    ts: String(e.ts ?? '').slice(11, 19) || '——:——:——',
    level: normalizeLevel(e.level),
    source: String(e.source ?? 'NEXUS'),
    msg: String(e.msg ?? ''),
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
  return (
    <motion.div
      className="flex items-start gap-2 px-2 py-1.5 text-[10px] leading-tight"
      style={{ borderLeft: `2px solid ${c}`, background: 'rgba(0,0,0,0.18)' }}
      initial={isAlert ? { boxShadow: `inset 0 0 0 0 transparent` } : false}
      animate={isAlert ? {
        boxShadow: [
          `inset 0 0 0 0 transparent`,
          `inset 0 0 12px 0 ${c}`,
          `inset 0 0 0 0 transparent`,
        ],
      } : undefined}
      transition={isAlert ? { duration: 2.5, repeat: Infinity, ease: 'easeInOut' } : undefined}
    >
      <Icon size={11} style={{ color: c, marginTop: 1, flexShrink: 0 }} />
      <div className="flex-1 min-w-0">
        <div className="flex gap-2 items-baseline">
          <span style={{ color: 'var(--hud-text-dim)' }}>{event.ts}</span>
          <span style={{ color: c, fontWeight: 700, letterSpacing: '0.1em' }}>{event.source}</span>
        </div>
        <div style={{ color: 'var(--hud-text)' }}>{event.msg}</div>
      </div>
    </motion.div>
  );
}

// ── Schedule row (clickable → opens schema note in Obsidian) ────────────────

function ScheduleRow({ job }: { job: ScheduledJob }) {
  const cadence = bucketize(job.name);
  const cadenceColor =
    cadence === 'daily'   ? 'var(--color-docker)'
  : cadence === 'weekly'  ? 'var(--color-vault)'
  : cadence === 'monthly' ? 'var(--color-jarvis)'
  : 'var(--hud-text-dim)';

  const notePath = JOB_NOTE[job.id];
  const clickable = !!notePath;

  // Strip the "Daily: " / "Weekly: " prefix and parenthetical time for display
  const display = job.name.replace(/^(daily|weekly|monthly):\s*/i, '').replace(/\s*\([^)]*\)\s*$/, '');

  return (
    <button
      type="button"
      onClick={clickable ? () => openObsidian(notePath) : undefined}
      disabled={!clickable}
      className="flex items-center gap-2 px-2 py-1.5 text-[10px] text-left transition-colors"
      style={{
        borderLeft: `2px solid ${cadenceColor}`,
        background: 'rgba(0,0,0,0.18)',
        cursor: clickable ? 'pointer' : 'default',
        opacity: clickable ? 1 : 0.65,
      }}
      onMouseEnter={(e) => { if (clickable) e.currentTarget.style.background = 'rgba(0,212,255,0.06)'; }}
      onMouseLeave={(e) => { if (clickable) e.currentTarget.style.background = 'rgba(0,0,0,0.18)'; }}
      title={clickable ? `Open note: ${notePath}` : 'No schema note linked'}
    >
      <CalendarClock size={11} style={{ color: cadenceColor, flexShrink: 0 }} />
      <span className="flex-1 truncate" style={{ color: 'var(--hud-text)' }}>{display}</span>
      {clickable && <BookOpen size={9} style={{ color: 'var(--hud-text-dim)', flexShrink: 0 }} />}
    </button>
  );
}

function bucketize(name: string): 'daily' | 'weekly' | 'monthly' | null {
  const l = name.toLowerCase();
  if (l.startsWith('daily:'))   return 'daily';
  if (l.startsWith('weekly:'))  return 'weekly';
  if (l.startsWith('monthly:')) return 'monthly';
  return null;
}

// ── Skill row (clickable → opens Hermes note in Obsidian) ───────────────────

function SkillRow({ skill }: { skill: SkillEntry }) {
  const cadenceColor =
    skill.schedule === 'daily'  ? 'var(--color-docker)'
  : skill.schedule === 'weekly' ? 'var(--color-vault)'
  : 'var(--color-jarvis)';

  return (
    <button
      type="button"
      onClick={() => openObsidian(skill.note)}
      className="flex items-center gap-2 px-2 py-1.5 text-[10px] text-left transition-colors"
      style={{
        borderLeft: `2px solid ${cadenceColor}`,
        background: 'rgba(0,0,0,0.18)',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0,212,255,0.06)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.18)'; }}
      title={`Open note: ${skill.note}`}
    >
      <Sparkles size={11} style={{ color: cadenceColor, flexShrink: 0 }} />
      <span className="flex-1 truncate" style={{ color: 'var(--hud-text)' }}>{skill.name}</span>
      <span
        className="px-1 text-[7.5px] tracking-[0.18em] shrink-0"
        style={{ color: cadenceColor, border: `1px solid ${cadenceColor}`, borderRadius: 2 }}
      >
        {skill.schedule === 'manual' ? '⚡' : skill.schedule.toUpperCase()}
      </span>
      <BookOpen size={9} style={{ color: 'var(--hud-text-dim)', flexShrink: 0 }} />
    </button>
  );
}

function EmptyRow({ text }: { text: string }) {
  return (
    <div className="text-[9px] tracking-[0.18em] text-center py-2"
         style={{ color: 'var(--hud-text-dim)', opacity: 0.6 }}>
      — {text} —
    </div>
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

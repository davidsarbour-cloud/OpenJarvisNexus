/**
 * Nexus9 — Automation schedule card.
 *
 * Big card spanning the Command Center grid. Lists every APScheduler job
 * grouped by frequency (daily / weekly / monthly) with a live countdown
 * to the next run. Alert dot turns yellow at <1 h, orange at <10 min,
 * red when overdue.
 */
import { useEffect, useMemo, useState } from 'react';
import { CalendarClock, BookOpen } from 'lucide-react';
import { HudCard } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchScheduledTasks, type ScheduledJob } from '../../lib/apiLive';
// urgencyFor + URGENCY_COLOR are no longer used in the rendered output —
// the visual treatment is uniform white now. Imports/types kept tree-
// shaken to nothing.

type Bucket = 'daily' | 'weekly' | 'monthly';

function parseNextRun(raw: string): Date | null {
  if (!raw || raw === 'None' || raw === 'null') return null;
  // Backend emits "2026-05-26 03:00:00-04:00" — JS Date needs the 'T' separator.
  const iso = raw.includes('T') ? raw : raw.replace(' ', 'T');
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

function fmtDuration(ms: number): string {
  const abs = Math.abs(ms);
  const s = Math.floor(abs / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);
  if (d > 0) return `${d}d ${h % 24}h`;
  if (h > 0) return `${h}h ${m % 60}m`;
  if (m > 0) return `${m}m ${s % 60}s`;
  return `${s}s`;
}

function bucketize(name: string): Bucket | null {
  const lower = name.toLowerCase();
  if (lower.startsWith('daily:')) return 'daily';
  if (lower.startsWith('weekly:')) return 'weekly';
  if (lower.startsWith('monthly:')) return 'monthly';
  return null;
}

function stripPrefix(name: string): string {
  return name.replace(/^(daily|weekly|monthly):\s*/i, '');
}

const BUCKET_LABEL: Record<Bucket, string> = {
  daily: 'DAILY',
  weekly: 'WEEKLY',
  monthly: 'MONTHLY',
};

// Each scheduled job optionally points to its schema note in the Obsidian
// vault. Clicking the row's 📖 icon opens that note in Obsidian via
// the custom URI protocol — same pattern as the Pipeline Hub cards.
const OBSIDIAN_VAULT = 'BRAIN';
const JOB_OBSIDIAN_PATHS: Record<string, string> = {
  trend_hunt:                '07_Schemas/workflows/trend-hunt-schema.md',
  morning_briefing:          '07_Schemas/workflows/morning-briefing-schema.md',
  daily_stl_research:        '07_Schemas/workflows/stl-research-schema.md',
  brain_autolink:            '07_Schemas/workflows/brain-autolink-schema.md',
  // Skill-driven cron jobs → Hermes reference notes
  skill_docker_health:       '05_Resources/Research/hermes.md',
  skill_blogwatcher:         '05_Resources/Research/hermes/blogwatcher.md',
  skill_polymarket:          '05_Resources/Research/hermes/polymarket.md',
  skill_codebase_inspection: '05_Resources/Research/hermes/codebase-inspection.md',
  skill_ideation:            '05_Resources/Research/hermes/ideation.md',
  skill_polymarket_digest:   '05_Resources/Research/hermes/polymarket.md',
  // Generated reports — open the most recent run under 02_Daily/<today>/
  // via a relative path; if Obsidian fails to resolve it falls back to
  // the user's home / search. The report itself is timestamped per-run
  // so we point at the hermes index page that links them.
  weekly_vault_growth:       '02_Daily/index.md',
  daily_brain_stubs_check:   '02_Daily/index.md',
  monthly_repo_audit:        '02_Daily/index.md',
  monthly_brain_snapshot:    '02_Daily/index.md',
};

// Auto-Factory lines live in their own dedicated Factory hub (/factory), so
// they're excluded from this general automation schedule to avoid duplication.
const isFactoryJob = (id: string) => id.startsWith('auto_factory');

function openObsidian(path: string) {
  const url = `obsidian://open?vault=${encodeURIComponent(OBSIDIAN_VAULT)}&file=${encodeURIComponent(path)}`;
  window.open(url, '_self');
}

// Refresh policy:
//   • Backend list (job names + next_run_time) is fetched every 30 min — APScheduler
//     schedules don't change often, no need to hammer the endpoint.
//   • Client `now` ticks every 1 s so the countdown stays minute-accurate visually
//     (and second-accurate when a job is imminent).
const FETCH_INTERVAL_MS = 30 * 60 * 1000;
const TICK_INTERVAL_MS = 1000;

export function ScheduledTasksCard({
  buckets = ['daily', 'weekly', 'monthly'],
  title = 'Automation Schedule',
  columns,
}: {
  /** Which frequency buckets to display (default: all). Lets the card be
   *  split across docks — e.g. daily on the left, weekly+monthly on the
   *  right — each copy showing only its own buckets. */
  buckets?: Bucket[];
  title?: string;
  /** Grid columns for the bucket sections. Defaults to one per bucket
   *  (side by side); pass 1 to stack them vertically in a narrow dock. */
  columns?: number;
} = {}) {
  const { data, error, loading } = useLiveMetric(fetchScheduledTasks, { intervalMs: FETCH_INTERVAL_MS, wsTopic: 'snapshot/scheduled' });
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), TICK_INTERVAL_MS);
    return () => clearInterval(t);
  }, []);

  const grouped = useMemo(() => {
    const out: Record<Bucket, ScheduledJob[]> = { daily: [], weekly: [], monthly: [] };
    (data?.jobs ?? []).forEach((j) => {
      if (isFactoryJob(j.id)) return;
      const b = bucketize(j.name);
      if (b) out[b].push(j);
    });
    (Object.keys(out) as Bucket[]).forEach((k) =>
      out[k].sort((a, b) => {
        const da = parseNextRun(a.next_run)?.getTime() ?? Infinity;
        const db = parseNextRun(b.next_run)?.getTime() ?? Infinity;
        return da - db;
      }),
    );
    return out;
  }, [data]);

  // Headline + count are scoped to the buckets THIS card shows, so a split
  // card reports its own next-fire / job total (not the global one).
  const shownJobs = useMemo(
    () =>
      (data?.jobs ?? []).filter((j) => {
        if (isFactoryJob(j.id)) return false;
        const b = bucketize(j.name);
        return b !== null && buckets.includes(b);
      }),
    [data, buckets],
  );
  const jobCount = shownJobs.length;
  const nextOverall = useMemo<{ name: string; at: Date } | null>(() => {
    let best: { name: string; at: Date } | null = null;
    for (const j of shownJobs) {
      const at = parseNextRun(j.next_run);
      if (!at) continue;
      if (best === null || at < best.at) {
        best = { name: stripPrefix(j.name), at };
      }
    }
    return best;
  }, [shownJobs]);

  const status = error ? 'down' : loading ? 'loading' : 'live';

  const nextDelta = nextOverall ? nextOverall.at.getTime() - now : null;

  return (
    <HudCard
      title={title}
      subtitle="countdown to next fire"
      colorKey="jarvis"
      icon={CalendarClock}
      status={status}
    >
      {/* Headline: next job firing */}
      <div
        className="mb-3 px-3 py-2 flex items-center gap-3"
        style={{
          background: 'rgba(0,0,0,0.3)',
          border: '1px solid var(--hud-border)',
        }}
      >
        <span className="text-[10px] tracking-[0.22em]" style={{ color: '#ffffff' }}>
          NEXT
        </span>
        <span className="text-[11px] font-bold" style={{ color: '#ffffff' }}>
          {nextOverall ? nextOverall.name : '—'}
        </span>
        <span className="ml-auto text-[14px] font-bold tabular-nums" style={{ color: '#ffffff' }}>
          {nextDelta === null
            ? '—'
            : nextDelta < 0
              ? `OVERDUE ${fmtDuration(nextDelta)}`
              : `in ${fmtDuration(nextDelta)}`}
        </span>
        <span className="text-[9px] tracking-wider" style={{ color: '#ffffff' }}>
          {jobCount} JOBS
        </span>
      </div>

      {/* One column per shown bucket (daily | weekly | monthly) */}
      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: `repeat(${columns ?? buckets.length}, minmax(0, 1fr))` }}
      >
        {buckets.map((bucket) => {
          const jobs = grouped[bucket];
          return (
            <div key={bucket}>
              <div
                className="text-[9px] font-bold tracking-[0.3em] mb-1.5 pb-1"
                style={{
                  color: '#ffffff',
                  borderBottom: '1px solid var(--hud-border)',
                }}
              >
                {BUCKET_LABEL[bucket]} ({jobs.length})
              </div>
              {jobs.length === 0 ? (
                <div className="text-[9px] py-1" style={{ color: '#ffffff', opacity: 0.5 }}>
                  none scheduled
                </div>
              ) : (
                <div className="flex flex-col gap-0.5">
                  {jobs.map((j) => {
                    const at = parseNextRun(j.next_run);
                    const delta = at ? at.getTime() - now : null;
                    const obsidianPath = JOB_OBSIDIAN_PATHS[j.id];
                    return (
                      <div
                        key={j.id}
                        className="flex items-center gap-2 text-[10px] py-0.5 px-1"
                        style={{ borderRadius: 1 }}
                      >
                        <span
                          className="truncate"
                          style={{ color: '#ffffff', flex: 1 }}
                          title={j.id}
                        >
                          {stripPrefix(j.name)}
                        </span>
                        {obsidianPath && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openObsidian(obsidianPath);
                            }}
                            title={`Open in Obsidian → ${obsidianPath}`}
                            className="shrink-0"
                            style={{
                              padding: 0,
                              margin: 0,
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--hud-text-dim)',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              transition: 'color 0.15s',
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-vault)')}
                            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
                          >
                            <BookOpen size={10} />
                          </button>
                        )}
                        <span className="tabular-nums shrink-0" style={{ color: '#ffffff' }}>
                          {delta === null
                            ? '—'
                            : delta < 0
                              ? `−${fmtDuration(delta)}`
                              : fmtDuration(delta)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {error && (
        <div className="mt-2 text-[9px]" style={{ color: 'var(--color-cyberdeck)' }}>
          {error}
        </div>
      )}
    </HudCard>
  );
}

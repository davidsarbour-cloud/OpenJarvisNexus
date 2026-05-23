import { Hammer } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchCrewJobs } from '../../lib/apiLive';

export function ForgePipelinesCard() {
  const { data, error, loading } = useLiveMetric(fetchCrewJobs, { intervalMs: 6000 });
  const jobs = data?.jobs ?? [];
  const running = jobs.filter((j) => String(j.status).toLowerCase() === 'running').length;
  const done    = jobs.filter((j) => String(j.status).toLowerCase() === 'done').length;
  const failed  = jobs.filter((j) => String(j.status).toLowerCase() === 'failed').length;
  const status = error ? 'down' : loading ? 'loading' : 'live';

  return (
    <HudCard
      title="Forge Pipelines"
      subtitle="STL · 3D · crew jobs (/v1/crew/jobs)"
      colorKey="forge"
      icon={Hammer}
      status={status}
    >
      <CardValue value={jobs.length || '—'} unit="total" colorKey="forge" />
      <div className="mt-2 grid grid-cols-3 gap-1 text-[10px]">
        <Box c="var(--color-jarvis)"    label="RUN"  v={running} />
        <Box c="var(--color-docker)"    label="DONE" v={done} />
        <Box c="var(--color-cyberdeck)" label="FAIL" v={failed} />
      </div>
    </HudCard>
  );
}

function Box({ c, label, v }: { c: string; label: string; v: number }) {
  return (
    <div
      className="flex flex-col items-center py-1"
      style={{ border: `1px solid ${c}`, background: 'rgba(0,0,0,0.18)' }}
    >
      <span className="tabular-nums text-base font-bold" style={{ color: c, lineHeight: 1 }}>{v}</span>
      <span className="text-[8px] tracking-[0.18em]" style={{ color: 'var(--hud-text-dim)' }}>{label}</span>
    </div>
  );
}

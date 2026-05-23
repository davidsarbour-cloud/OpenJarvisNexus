import { LineChart } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchPrometheusTargets } from '../../lib/apiLive';

export function PrometheusLiveCard() {
  const { data, error, loading } = useLiveMetric(fetchPrometheusTargets, { intervalMs: 10000 });
  const available = data?.available ?? false;
  const status = error || !available ? 'down' : loading ? 'loading' : 'live';
  const up = data?.up ?? 0;
  const down = data?.down ?? 0;
  const total = data?.total ?? 0;

  return (
    <HudCard
      title="Prometheus"
      subtitle="scrape targets (/v1/prometheus/targets)"
      colorKey="forge"
      icon={LineChart}
      status={status}
    >
      <CardValue value={total || '—'} unit="targets" colorKey="forge" />
      <div className="mt-2 grid grid-cols-2 gap-1 text-[10px]">
        <Mini c="var(--color-docker)"    label="UP"   v={up} />
        <Mini c="var(--color-cyberdeck)" label="DOWN" v={down} />
      </div>
      <a
        href="http://localhost:9090"
        target="_blank"
        rel="noopener noreferrer"
        className="text-[9px] tracking-[0.18em] mt-2 underline"
        style={{ color: 'var(--color-forge)' }}
      >
        Open Prometheus :9090 →
      </a>
    </HudCard>
  );
}

function Mini({ c, label, v }: { c: string; label: string; v: number }) {
  return (
    <div className="flex items-center gap-1.5 px-1.5 py-0.5" style={{ border: `1px solid ${c}`, background: 'rgba(0,0,0,0.18)' }}>
      <span style={{ color: 'var(--hud-text-dim)', fontSize: 8, letterSpacing: '0.15em' }}>{label}</span>
      <span className="ml-auto tabular-nums" style={{ color: c, fontWeight: 700 }}>{v}</span>
    </div>
  );
}

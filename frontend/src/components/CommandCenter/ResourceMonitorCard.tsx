import { useEffect, useState } from 'react';
import { LineChart } from 'lucide-react';
import { HudCard } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchSystemMetrics } from '../../lib/apiLive';

const MAX = 40; // samples kept per series

function Spark({ data, max }: { data: number[]; max?: number }) {
  const W = 240;
  const H = 34;
  if (data.length < 2) {
    return <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" />;
  }
  const peak = max ?? Math.max(...data, 1);
  const pts = data
    .map((v, i) => {
      const x = (i / (MAX - 1)) * W;
      const y = H - (Math.min(v, peak) / peak) * (H - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <polyline
        points={pts}
        fill="none"
        stroke="var(--color-jarvis)"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
        style={{ filter: 'drop-shadow(0 0 3px var(--color-jarvis))' }}
      />
    </svg>
  );
}

interface Hist {
  cpu: number[];
  ram: number[];
  vram: number[];
  net: number[];
}

// Push a value into a rolling window of size MAX, returning a *new*
// array (so React sees a state change). Pure — safe to call during
// render via useEffect's setter.
function push(arr: number[], v: number): number[] {
  const next = arr.length >= MAX ? arr.slice(1) : arr.slice();
  next.push(v);
  return next;
}

export function ResourceMonitorCard() {
  const { data, error, loading } = useLiveMetric(fetchSystemMetrics, { intervalMs: 2000, wsTopic: 'snapshot/system-metrics' });
  const status = error ? 'down' : loading ? 'loading' : 'live';
  const [hist, setHist] = useState<Hist>({ cpu: [], ram: [], vram: [], net: [] });

  useEffect(() => {
    if (!data) return;
    // History-accumulation pattern: every new poll appends to a rolling
    // window. React 19's set-state-in-effect lint flags this even though
    // it's the textbook React pattern for derived-time-series state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHist((prev) => ({
      cpu:  push(prev.cpu,  data.cpu),
      ram:  push(prev.ram,  data.ram),
      vram: push(prev.vram, data.vram ?? 0),
      net:  push(prev.net,  data.network_mbps),
    }));
  }, [data]);

  const rows = [
    { label: 'CPU',     val: data ? `${data.cpu}%` : '—',                    series: hist.cpu,  max: 100      },
    { label: 'RAM',     val: data ? `${data.ram}%` : '—',                    series: hist.ram,  max: 100      },
    { label: 'VRAM',    val: data?.vram != null ? `${data.vram}%` : '—',    series: hist.vram, max: 100      },
    { label: 'NETWORK', val: data ? `${data.network_mbps} MB/s` : '—',       series: hist.net,  max: undefined },
  ];

  return (
    <HudCard title="Resource Monitor" subtitle="live · 2s" colorKey="jarvis" icon={LineChart} status={status}>
      <div className="flex flex-col gap-3 pt-1">
        {rows.map((r) => (
          <div key={r.label} className="flex flex-col gap-0.5">
            <div className="flex justify-between text-[11px]">
              <span style={{ color: 'var(--hud-text-dim)', letterSpacing: 1 }}>{r.label}</span>
              <span style={{ color: 'var(--color-jarvis)' }}>{r.val}</span>
            </div>
            <Spark data={r.series} max={r.max} />
          </div>
        ))}
        {error && (
          <div className="text-[9px]" style={{ color: 'var(--color-cyberdeck)' }}>
            {error}
          </div>
        )}
      </div>
    </HudCard>
  );
}

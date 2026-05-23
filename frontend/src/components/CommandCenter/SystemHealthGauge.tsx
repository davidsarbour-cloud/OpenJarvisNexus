import { Activity } from 'lucide-react';
import { HudCard } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchSystemMetrics, type SystemMetrics } from '../../lib/apiLive';

const BARS: Array<{ key: keyof SystemMetrics; label: string }> = [
  { key: 'cpu', label: 'CPU' },
  { key: 'ram', label: 'RAM' },
  { key: 'vram', label: 'VRAM' },
  { key: 'storage', label: 'STORAGE' },
];

function Ring({ pct, label }: { pct: number; label: string }) {
  const R = 64;
  const C = 2 * Math.PI * R;
  const off = C * (1 - Math.max(0, Math.min(100, pct)) / 100);
  return (
    <svg width="170" height="170" viewBox="0 0 170 170">
      <circle cx="85" cy="85" r={R} fill="none" stroke="var(--hud-border)" strokeWidth="6" />
      <circle
        cx="85"
        cy="85"
        r={R}
        fill="none"
        stroke="var(--color-jarvis)"
        strokeWidth="6"
        strokeLinecap="round"
        strokeDasharray={C}
        strokeDashoffset={off}
        transform="rotate(-90 85 85)"
        style={{ filter: 'drop-shadow(0 0 6px var(--color-jarvis))', transition: 'stroke-dashoffset 0.6s ease' }}
      />
      <text x="85" y="82" textAnchor="middle" fontSize="36" fontWeight="700" fill="var(--color-jarvis)">
        {pct}%
      </text>
      <text x="85" y="104" textAnchor="middle" fontSize="11" letterSpacing="3" fill="var(--hud-text-dim)">
        {label}
      </text>
    </svg>
  );
}

function Bar({ label, pct }: { label: string; pct: number | null }) {
  const segs = 28;
  const filled = pct == null ? 0 : Math.round((Math.max(0, Math.min(100, pct)) / 100) * segs);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-[11px]">
        <span style={{ color: 'var(--hud-text-dim)', letterSpacing: 1 }}>{label}</span>
        <span style={{ color: 'var(--color-jarvis)' }}>{pct == null ? '—' : `${pct}%`}</span>
      </div>
      <div className="flex gap-[2px]">
        {Array.from({ length: segs }).map((_, i) => (
          <span
            key={i}
            style={{
              flex: 1,
              height: 6,
              borderRadius: 1,
              background: i < filled ? 'var(--color-jarvis)' : 'var(--hud-border)',
              boxShadow: i < filled ? '0 0 4px var(--color-jarvis)' : 'none',
              opacity: i < filled ? 1 : 0.35,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export function SystemHealthGauge() {
  const { data, error, loading } = useLiveMetric(fetchSystemMetrics, { intervalMs: 2000 });
  const status = error ? 'down' : loading ? 'loading' : 'live';
  const score = data?.health_score ?? 0;
  const label = data?.health_label ?? '—';

  return (
    <HudCard
      title="System Health"
      subtitle="hardware live (/v1/system/metrics)"
      colorKey="jarvis"
      icon={Activity}
      status={status}
    >
      <div className="flex flex-col items-center gap-4 pt-2">
        <Ring pct={score} label={label} />
        <div className="w-full flex flex-col gap-3">
          {BARS.map((b) => (
            <Bar key={b.key} label={b.label} pct={(data?.[b.key] as number | null) ?? null} />
          ))}
        </div>
        {error && (
          <div className="text-[9px] self-start" style={{ color: 'var(--color-cyberdeck)' }}>
            {error}
          </div>
        )}
      </div>
    </HudCard>
  );
}

import { HeartPulse } from 'lucide-react';
import { useLiveMetric } from '../hooks/useLiveMetric';
import { fetchHealthAll, fetchSystemMetrics } from '../lib/apiLive';

/**
 * HealthPage — route `/health`.
 * One-shot health board: overall status + per-service up/down from
 * /v1/health/all, plus live CPU/RAM/VRAM/storage bars from
 * /v1/system/metrics. Auto-polls (no manual refresh needed).
 */

const STATUS_COLOR: Record<string, string> = {
  up:        'var(--color-docker)',
  healthy:   'var(--color-docker)',
  warn:      'var(--color-security)',
  degraded:  'var(--color-security)',
  down:      'var(--color-cyberdeck)',
};

const SERVICE_LABEL: Record<string, string> = {
  claude_api: 'Claude API',
  ollama:     'Ollama',
  forge_room: 'Forge Room',
  meshy_api:  'Meshy API',
  docker:     'Docker',
  chromadb:   'ChromaDB',
};

function detailText(d: unknown): string {
  if (d == null) return '';
  if (typeof d === 'string') return d;
  if (typeof d === 'object') {
    const o = d as Record<string, unknown>;
    if (typeof o.count === 'number') return `${o.count} collections`;
    if (typeof o.running === 'number') return `${o.running} running`;
    if ('available' in o) return o.available ? 'available' : 'unavailable';
    return JSON.stringify(d).slice(0, 80);
  }
  return String(d);
}

function metricColor(v: number | null): string {
  if (v == null) return 'var(--hud-text-dim)';
  if (v > 90) return 'var(--color-cyberdeck)';
  if (v > 75) return 'var(--color-security)';
  return 'var(--color-docker)';
}

export function HealthPage() {
  const { data: health, loading } = useLiveMetric(fetchHealthAll, { intervalMs: 10000 });
  const { data: metrics } = useLiveMetric(fetchSystemMetrics, { intervalMs: 4000 });

  const overall = health?.overall;
  const overallColor = STATUS_COLOR[overall ?? ''] ?? 'var(--hud-text-dim)';
  const services = health ? Object.entries(health.services) : [];

  const bars: { label: string; value: number | null }[] = [
    { label: 'CPU',     value: metrics?.cpu ?? null },
    { label: 'RAM',     value: metrics?.ram ?? null },
    { label: 'VRAM',    value: metrics?.vram ?? null },
    { label: 'STORAGE', value: metrics?.storage ?? null },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5" style={{ background: 'var(--hud-bg)' }}>
      <div className="flex items-center gap-3 text-[10px] font-bold tracking-[0.3em]" style={{ color: 'var(--hud-text-dim)' }}>
        <HeartPulse size={13} style={{ color: 'var(--color-docker)' }} />
        HEALTH CHECKS
        <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
        <span style={{ color: overallColor, border: `1px solid ${overallColor}`, padding: '2px 8px', fontSize: 9 }}>
          {(overall ?? (loading ? '…' : 'UNKNOWN')).toString().toUpperCase()}
        </span>
        {health?.ts && <span style={{ color: 'var(--hud-text-dim)' }}>{health.ts.slice(11, 19)}</span>}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {services.length === 0 ? (
          <div className="text-[10px]" style={{ color: 'var(--hud-text-dim)' }}>
            {loading ? 'checking services…' : 'no data — backend offline?'}
          </div>
        ) : (
          services.map(([key, svc]) => {
            const c = STATUS_COLOR[svc.status] ?? 'var(--hud-text-dim)';
            return (
              <div
                key={key}
                style={{
                  background: 'var(--hud-bg-elev)',
                  border: '1px solid var(--hud-border)',
                  borderLeft: `2px solid ${c}`,
                  padding: '10px 12px',
                }}
              >
                <div className="flex items-center gap-2">
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, boxShadow: `0 0 6px ${c}`, flexShrink: 0 }} />
                  <span className="text-[11px] font-bold tracking-[0.14em]" style={{ color: c }}>
                    {SERVICE_LABEL[key] ?? key}
                  </span>
                  <span className="ml-auto text-[9px] tracking-[0.2em]" style={{ color: c }}>
                    {svc.status.toUpperCase()}
                  </span>
                </div>
                <div className="text-[9px] mt-1 truncate" style={{ color: 'var(--hud-text-dim)' }} title={detailText(svc.detail)}>
                  {detailText(svc.detail)}
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="flex items-center gap-3 text-[10px] font-bold tracking-[0.3em] mt-2" style={{ color: 'var(--hud-text-dim)' }}>
        <span style={{ color: 'var(--color-jarvis)' }}>◆</span>
        SYSTEM
        <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
        {metrics && (
          <span style={{ color: 'var(--hud-text-dim)' }}>
            {metrics.health_label} · {metrics.health_score}/100
          </span>
        )}
      </div>
      <div className="flex flex-col gap-2 max-w-2xl">
        {bars.map((b) => (
          <div key={b.label} className="flex items-center gap-3">
            <span className="text-[9px] tracking-[0.2em]" style={{ color: 'var(--hud-text-dim)', width: 64 }}>{b.label}</span>
            <div className="flex-1" style={{ height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{ width: `${b.value ?? 0}%`, height: '100%', background: metricColor(b.value), transition: 'width 0.4s' }} />
            </div>
            <span className="text-[10px] tabular-nums text-right" style={{ color: metricColor(b.value), width: 40 }}>
              {b.value == null ? '—' : `${b.value}%`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

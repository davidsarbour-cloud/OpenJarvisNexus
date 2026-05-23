import { BarChart3 } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchGrafanaHealth } from '../../lib/apiLive';

export function GrafanaLiveCard() {
  const { data, error, loading } = useLiveMetric(fetchGrafanaHealth, { intervalMs: 30000 });

  // Même logique prudente que DockerLiveCard :
  // erreur réseau → 'warn', backend explicit available:false → 'down'
  const available  = data?.available;
  const backendDown = available === false;
  const netError   = !!error && available !== false;

  const status = loading && data === null
    ? 'loading'
    : backendDown
    ? 'down'
    : netError
    ? 'warn'
    : 'live';

  const dashboards = data?.dashboards ?? 0;
  const version    = data?.version ?? '';

  return (
    <HudCard
      title="Grafana"
      subtitle="observability (/v1/grafana/health)"
      colorKey="security"
      icon={BarChart3}
      status={status}
    >
      <CardValue value={dashboards || '—'} unit="dashboards" colorKey="security" />
      {version && (
        <div className="text-[9px] tracking-wider mt-1" style={{ color: 'var(--hud-text-dim)' }}>
          v{version}
        </div>
      )}
      {(error || data?.error) && (
        <div className="text-[9px] mt-1 truncate" style={{ color: 'var(--color-security)' }}>
          {error || data?.error}
        </div>
      )}
      <a
        href="http://localhost:3001"
        target="_blank"
        rel="noopener noreferrer"
        className="text-[9px] tracking-[0.18em] mt-2 underline"
        style={{ color: 'var(--color-security)' }}
      >
        Open Grafana :3001 →
      </a>
    </HudCard>
  );
}

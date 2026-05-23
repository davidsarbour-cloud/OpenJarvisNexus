import { Bug } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchSonarIssues } from '../../lib/apiLive';

const SEV_COLORS: Record<string, string> = {
  BLOCKER:  'var(--color-cyberdeck)',
  CRITICAL: 'var(--color-cyberdeck)',
  MAJOR:    'var(--color-security)',
  MINOR:    'var(--color-jarvis)',
  INFO:     'var(--hud-text-dim)',
};

export function SonarqubeLiveCard() {
  const { data, error, loading } = useLiveMetric(fetchSonarIssues, { intervalMs: 20000 });
  const available = data?.available ?? false;
  const status = error || !available ? 'down' : loading ? 'loading' : 'live';
  const total = data?.total ?? 0;
  const facets = data?.facets ?? {};

  return (
    <HudCard
      title="SonarQube"
      subtitle="code issues (/v1/sonarqube/issues)"
      colorKey="cyberdeck"
      icon={Bug}
      status={status}
    >
      <CardValue value={total || '—'} unit="issues" colorKey="cyberdeck" />
      <div className="mt-2 flex flex-wrap gap-1 text-[9px]">
        {Object.entries(facets).map(([sev, count]) => (
          <span
            key={sev}
            className="px-1.5 py-0.5 tracking-wider"
            style={{
              color: SEV_COLORS[sev] ?? 'var(--hud-text)',
              border: `1px solid ${SEV_COLORS[sev] ?? 'var(--hud-border)'}`,
              background: 'rgba(0,0,0,0.18)',
            }}
          >
            {sev} {count}
          </span>
        ))}
      </div>
      <a
        href="http://localhost:9000"
        target="_blank"
        rel="noopener noreferrer"
        className="text-[9px] tracking-[0.18em] mt-2 underline"
        style={{ color: 'var(--color-cyberdeck)' }}
      >
        Open SonarQube :9000 →
      </a>
    </HudCard>
  );
}

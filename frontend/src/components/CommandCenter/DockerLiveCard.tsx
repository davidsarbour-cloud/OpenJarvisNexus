import { Container } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchDockerContainers } from '../../lib/apiLive';
import { useServiceAlert } from '../../systems/alerts';

export function DockerLiveCard() {
  const { data, error, loading } = useLiveMetric(fetchDockerContainers, { intervalMs: 8000 });

  // "available" vient du backend (available:false = Docker engine inaccessible).
  // Une erreur réseau (timeout, fetch throw) indique seulement que le proxy est
  // temporairement injoignable — on affiche 'warn', pas 'down', pour éviter le
  // faux CRITICAL banner permanent qui se déclenche au moindre timeout réseau.
  const available = data?.available;          // undefined tant qu'aucune réponse
  const backendDown = available === false;    // backend a explicitement dit "non dispo"
  const netError   = !!error && available !== false; // erreur réseau, dernière valeur connue ok

  const status = loading && data === null
    ? 'loading'
    : backendDown
    ? 'down'
    : netError
    ? 'warn'
    : 'live';

  const count  = data?.count ?? data?.containers?.length ?? 0;
  const source = data?.source ?? 'docker.sock';
  const sample = (data?.containers ?? []).slice(0, 3).map(c => c.name).join(' · ');

  useServiceAlert(
    'docker',
    status,
    backendDown ? 'Docker engine unreachable' : 'Docker monitor temporarily unreachable',
    error ?? data?.error,
  );

  return (
    <HudCard
      title="Docker Infra"
      subtitle={`via ${source} (/v1/docker/containers)`}
      colorKey="docker"
      icon={Container}
      status={status}
    >
      <CardValue value={count || '—'} unit="containers" colorKey="docker" />
      {sample && (
        <div className="text-[9px] tracking-wider mt-2 truncate" style={{ color: 'var(--hud-text-dim)' }} title={sample}>
          {sample}
        </div>
      )}
      {(error || data?.error) && (
        <div className="text-[9px] mt-1" style={{ color: 'var(--color-cyberdeck)' }}>
          {error || data?.error}
        </div>
      )}
    </HudCard>
  );
}

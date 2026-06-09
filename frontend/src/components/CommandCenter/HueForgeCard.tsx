import { Palette } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchHueForgeJobs } from '../../lib/apiLive';

/**
 * HueForgeCard — état live du pipeline de préparation d'images HueForge.
 * Backed by GET /v1/hueforge/jobs. Mirror of ForgePipelinesCard.
 * "down" si le backend est injoignable, sinon "live".
 */
export function HueForgeCard() {
  const { data, error, loading } = useLiveMetric(() => fetchHueForgeJobs(), {
    intervalMs: 6000,
    wsTopic: 'snapshot/hueforge',
  });

  const total = data?.total ?? 0;
  const running = data?.running ?? 0;
  const done = data?.done ?? 0;
  const failed = data?.failed ?? 0;
  const variants = data?.variants ?? 0;
  const printPrep = data?.print ?? 0;
  const status = error ? 'down' : loading ? 'loading' : 'live';

  return (
    <HudCard
      title="HueForge"
      subtitle="Prep images · /v1/hueforge"
      colorKey="valkyrie"
      icon={Palette}
      status={status}
    >
      <CardValue value={total} unit="missions" colorKey="valkyrie" />
      <div className="mt-2 grid grid-cols-3 gap-1 text-[10px]">
        <div
          className="flex flex-col items-center py-1"
          style={{ border: '1px solid var(--color-jarvis)' }}
        >
          <span className="font-bold tabular-nums" style={{ color: 'var(--color-jarvis)' }}>{running}</span>
          <span style={{ color: 'var(--hud-text-dim)', fontSize: 8 }}>RUN</span>
        </div>
        <div
          className="flex flex-col items-center py-1"
          style={{ border: '1px solid var(--color-docker)' }}
        >
          <span className="font-bold tabular-nums" style={{ color: 'var(--color-docker)' }}>{done}</span>
          <span style={{ color: 'var(--hud-text-dim)', fontSize: 8 }}>DONE</span>
        </div>
        <div
          className="flex flex-col items-center py-1"
          style={{ border: '1px solid var(--color-cyberdeck)' }}
        >
          <span className="font-bold tabular-nums" style={{ color: 'var(--color-cyberdeck)' }}>{failed}</span>
          <span style={{ color: 'var(--hud-text-dim)', fontSize: 8 }}>FAIL</span>
        </div>
      </div>
      <div className="mt-2 flex justify-between text-[9px]" style={{ color: 'var(--hud-text-dim)' }}>
        <span>VARIANTS <span className="tabular-nums" style={{ color: 'var(--color-valkyrie)' }}>{variants}</span></span>
        <span>PRINT PREP <span className="tabular-nums" style={{ color: 'var(--color-valkyrie)' }}>{printPrep}</span></span>
      </div>
    </HudCard>
  );
}

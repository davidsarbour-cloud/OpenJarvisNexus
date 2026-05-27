import { Database } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchChromaStats } from '../../lib/apiLive';

export function ChromaDbLiveCard() {
  const { data, error, loading } = useLiveMetric(fetchChromaStats, { intervalMs: 12000, wsTopic: 'snapshot/chromadb' });
  const available = data?.available ?? false;
  const status = error || !available ? 'down' : loading ? 'loading' : 'live';
  const cols = data?.collections;

  return (
    <HudCard
      title="ChromaDB"
      subtitle="vector store (/v1/chromadb/stats)"
      colorKey="vault"
      icon={Database}
      status={status}
    >
      <CardValue
        value={cols === null || cols === undefined ? '—' : String(cols)}
        unit="collections"
        colorKey="vault"
      />
      <div className="mt-2 text-[10px] flex flex-col gap-0.5">
        <Row label="HEARTBEAT" value={available ? 'OK' : 'KO'} c={available ? 'var(--color-docker)' : 'var(--color-cyberdeck)'} />
        <Row label="ENDPOINT"  value=":8001"                  c="var(--color-vault)" />
      </div>
      {(error || data?.error) && (
        <div className="text-[9px] mt-1 truncate" style={{ color: 'var(--color-cyberdeck)' }}>
          {error || data?.error}
        </div>
      )}
    </HudCard>
  );
}

function Row({ label, value, c }: { label: string; value: string; c: string }) {
  return (
    <div className="flex justify-between">
      <span style={{ color: 'var(--hud-text-dim)', letterSpacing: '0.15em' }}>{label}</span>
      <span className="tabular-nums" style={{ color: c }}>{value}</span>
    </div>
  );
}

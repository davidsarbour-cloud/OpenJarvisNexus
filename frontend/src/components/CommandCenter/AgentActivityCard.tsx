import { Bot } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchAgents } from '../../lib/apiLive';

export function AgentActivityCard() {
  const { data, error, loading } = useLiveMetric(fetchAgents, { intervalMs: 8000, wsTopic: 'snapshot/agents' });
  const agents = data?.agents ?? [];
  const online = agents.filter((a) => a.status === 'online').length;
  const offline = agents.filter((a) => a.status === 'offline').length;
  const status = error ? 'down' : loading ? 'loading' : 'live';

  return (
    <HudCard
      title="AI Agents"
      subtitle="hierarchy & status (/v1/agents)"
      colorKey="jarvis"
      icon={Bot}
      status={status}
    >
      <CardValue value={agents.length || '—'} unit="declared" colorKey="jarvis" />
      <div className="mt-2 flex flex-col gap-0.5 text-[10px]">
        <Line c="var(--color-docker)"    label="ONLINE"  value={online} />
        <Line c="var(--hud-text-dim)"    label="IDLE"    value={agents.length - online - offline} />
        <Line c="var(--color-cyberdeck)" label="OFFLINE" value={offline} />
      </div>
    </HudCard>
  );
}

function Line({ c, label, value }: { c: string; label: string; value: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: c, boxShadow: `0 0 4px ${c}` }} />
      <span style={{ color: 'var(--hud-text-dim)', minWidth: 60 }}>{label}</span>
      <span className="tabular-nums" style={{ color: c, fontWeight: 700 }}>
        {Number.isFinite(value) ? value : 0}
      </span>
    </div>
  );
}

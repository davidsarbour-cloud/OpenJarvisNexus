import { Activity } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchBudget } from '../../lib/apiLive';

export function BudgetCard() {
  const { data, error, loading } = useLiveMetric(fetchBudget, { intervalMs: 8000 });
  const status = error ? 'down' : loading ? 'loading' : 'live';

  const cost   = data?.session?.cost_usd ?? 0;
  const calls  = (data?.session?.calls_claude ?? 0) + (data?.session?.calls_ollama ?? 0);
  const max    = data?.budget_max ?? 0;
  const rem    = data?.budget_remaining ?? 0;
  const pct    = max > 0 ? Math.min(100, Math.max(0, (cost / max) * 100)) : 0;

  return (
    <HudCard
      title="Budget Session"
      subtitle="claude / ollama spend (/v1/budget)"
      colorKey="security"
      icon={Activity}
      status={status}
    >
      <CardValue value={`$${cost.toFixed(4)}`} unit={`/ $${max.toFixed(2)}`} colorKey="security" />
      <div className="mt-2 text-[10px] flex flex-col gap-1">
        <div className="flex justify-between">
          <span style={{ color: 'var(--hud-text-dim)' }}>CALLS</span>
          <span className="tabular-nums" style={{ color: 'var(--color-jarvis)' }}>{calls}</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: 'var(--hud-text-dim)' }}>REMAINING</span>
          <span className="tabular-nums" style={{ color: 'var(--color-docker)' }}>${rem.toFixed(4)}</span>
        </div>
        <div
          className="mt-1 h-1.5 w-full overflow-hidden"
          style={{ background: 'rgba(0,0,0,0.35)', border: '1px solid var(--hud-border)' }}
        >
          <div
            className="h-full transition-all"
            style={{
              width: `${pct}%`,
              background: pct > 80 ? 'var(--color-cyberdeck)' : pct > 50 ? 'var(--color-security)' : 'var(--color-docker)',
              boxShadow: '0 0 6px currentColor',
            }}
          />
        </div>
      </div>
    </HudCard>
  );
}

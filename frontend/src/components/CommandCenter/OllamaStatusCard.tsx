import { Server } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchModels } from '../../lib/apiLive';
import { useServiceAlert } from '../../systems/alerts';

export function OllamaStatusCard() {
  const { data, error, loading } = useLiveMetric(fetchModels, { intervalMs: 15000, wsTopic: 'snapshot/models' });
  const models = data?.models ?? [];
  const ollamaCount = models.filter((m) => m.provider === 'ollama').length;
  const cloudCount = models.length - ollamaCount;
  const status = error ? 'down' : loading ? 'loading' : 'live';
  useServiceAlert('ollama', status, 'Ollama unreachable', error ?? undefined);

  return (
    <HudCard
      title="Ollama Models"
      subtitle="local LLM runtime (/v1/models)"
      colorKey="forge"
      icon={Server}
      status={status}
    >
      <CardValue value={ollamaCount || '—'} unit="local" colorKey="forge" />
      <div className="mt-2 flex flex-col gap-0.5 text-[10px]">
        <div className="flex justify-between">
          <span style={{ color: 'var(--hud-text-dim)' }}>CLOUD MODELS</span>
          <span className="tabular-nums" style={{ color: 'var(--color-jarvis)' }}>{cloudCount}</span>
        </div>
        <div
          className="text-[9px] truncate mt-1"
          style={{ color: 'var(--hud-text-dim)' }}
          title={models.slice(0, 6).map(m => m.id).join(', ')}
        >
          {models.slice(0, 2).map(m => m.id.split(':')[0]).join(' · ') || '—'}
        </div>
      </div>
    </HudCard>
  );
}

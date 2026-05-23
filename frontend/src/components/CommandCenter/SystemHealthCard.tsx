import { Cpu } from 'lucide-react';
import { HudCard } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchHealthDeep, type HealthDeep } from '../../lib/apiLive';

const SERVICES: Array<{ key: keyof HealthDeep; label: string }> = [
  { key: 'backend',    label: 'BACKEND'    },
  { key: 'claude_api', label: 'CLAUDE API' },
  { key: 'ollama',     label: 'OLLAMA'     },
  { key: 'forge_room', label: 'FORGE'      },
  { key: 'meshy_api',  label: 'MESHY'      },
];

export function SystemHealthCard() {
  const { data, error, loading } = useLiveMetric(fetchHealthDeep, { intervalMs: 10000 });
  const status = error ? 'down' : loading ? 'loading' : 'live';

  return (
    <HudCard
      title="Service Status"
      subtitle="services deep-check (/v1/health/deep)"
      colorKey="jarvis"
      icon={Cpu}
      status={status}
    >
      <div className="flex flex-col gap-0.5">
        {SERVICES.map((s) => {
          const raw = (data?.[s.key] as string | undefined) ?? '';
          const dot = colorFor(raw);
          return (
            <div key={s.key} className="flex items-center gap-2 text-[10px]">
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: dot, boxShadow: `0 0 4px ${dot}` }}
              />
              <span style={{ color: 'var(--hud-text-dim)', minWidth: 75 }}>{s.label}</span>
              <span
                className="truncate"
                style={{ color: 'var(--hud-text)', flex: 1 }}
                title={raw}
              >
                {raw || '—'}
              </span>
            </div>
          );
        })}
        {error && (
          <div className="mt-1 text-[9px]" style={{ color: 'var(--color-cyberdeck)' }}>
            {error}
          </div>
        )}
      </div>
    </HudCard>
  );
}

function colorFor(raw: string): string {
  if (raw === 'ok') return 'var(--color-docker)';
  if (raw === 'not_configured') return 'var(--hud-text-dim)';
  if (raw === 'timeout' || raw === 'offline') return 'var(--color-security)';
  if (raw.startsWith('error')) return 'var(--color-cyberdeck)';
  return 'var(--hud-text-dim)';
}

import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import { HudCard } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchBootInfo } from '../../lib/apiLive';

function fmtUptime(ms: number): string {
  const s = Math.floor(ms / 1000);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

/**
 * UptimeCard — how long the Nexus9 backend has been online.
 *
 * Reads /v1/boot/info (refetched every 60s so a restart → new boot/start
 * time is picked up) and ticks a local clock every second so the counter
 * stays live without hammering the endpoint.
 */
export function UptimeCard() {
  const { data, error, loading } = useLiveMetric(fetchBootInfo, { intervalMs: 60000 });
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const startMs = data?.started_at ? new Date(data.started_at).getTime() : NaN;
  const hasStart = !Number.isNaN(startMs);
  const uptimeMs = hasStart ? Math.max(0, now - startMs) : null;
  const status = error ? 'down' : loading ? 'loading' : 'live';

  return (
    <HudCard
      title="Uptime"
      subtitle="backend online since boot"
      colorKey="jarvis"
      icon={Activity}
      status={status}
    >
      <div
        className="text-2xl font-bold tabular-nums"
        style={{ color: 'var(--color-jarvis)', lineHeight: 1.1 }}
      >
        {uptimeMs === null ? '—' : fmtUptime(uptimeMs)}
      </div>
      <div className="text-[9px] tracking-wider mt-1" style={{ color: 'var(--hud-text-dim)' }}>
        {hasStart ? `since ${new Date(startMs).toLocaleString()}` : 'waiting for /v1/boot/info'}
      </div>
    </HudCard>
  );
}

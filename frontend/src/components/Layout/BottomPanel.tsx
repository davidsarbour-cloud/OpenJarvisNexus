import { useEffect, useMemo, useState } from 'react';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchBudget } from '../../lib/apiLive';

/**
 * BottomPanel — Hardware resource monitor.
 *
 * Shows CPU / RAM / VRAM / NETWORK as animated HUD progress bars.
 * CPU & RAM try the real `/v1/system/metrics` endpoint; if unavailable
 * (404 / network error) they fall back to a demo sine-wave so the bar
 * is never empty.
 *
 * BUDGET is shown as a small badge on the right to keep financial
 * awareness visible without dominating the strip.
 */

interface SystemMetrics {
  cpu_pct:    number;
  ram_pct:    number;
  vram_pct:   number;
  net_mb_s:   number;
}

// Attempt to fetch real OS metrics from backend
async function fetchSystemMetrics(): Promise<SystemMetrics> {
  const r = await fetch('/v1/system/metrics', { signal: AbortSignal.timeout(3000) });
  if (!r.ok) throw new Error('not available');
  return r.json() as Promise<SystemMetrics>;
}

export function BottomPanel() {
  const [tick, setTick] = useState(0);

  // Tick every 2s for smooth demo animation
  useEffect(() => {
    const id = setInterval(() => setTick(x => x + 1), 2000);
    return () => clearInterval(id);
  }, []);

  // Try live system metrics — fall back to demo if missing
  const sysMetrics = useLiveMetric(fetchSystemMetrics, { intervalMs: 2000 });

  const cpu  = sysMetrics.data?.cpu_pct  ?? demoVal(tick, 45, 28, 0.55);
  const ram  = sysMetrics.data?.ram_pct  ?? demoVal(tick, 58, 18, 0.30);
  const vram = sysMetrics.data?.vram_pct ?? demoVal(tick, 34, 20, 0.42);
  const net  = sysMetrics.data?.net_mb_s ?? Math.abs(demoVal(tick, 20, 18, 0.70));
  const live = !sysMetrics.error;

  // Budget badge (real)
  const budget = useLiveMetric(fetchBudget, { intervalMs: 5000 });
  const cost = budget.data?.session?.cost_usd ?? 0;

  return (
    <footer
      className="shrink-0 flex items-stretch gap-px"
      style={{
        height: 52,
        background: 'var(--hud-border)',
        borderTop: '1px solid var(--hud-border)',
      }}
    >
      <HwBar label="CPU"     value={cpu}  unit="%"    max={100} colorKey="jarvis"    live={live} tick={tick} />
      <HwBar label="RAM"     value={ram}  unit="%"    max={100} colorKey="forge"     live={live} tick={tick} />
      <HwBar label="VRAM"    value={vram} unit="%"    max={100} colorKey="vault"     live={live} tick={tick} />
      <HwBar label="NETWORK" value={net}  unit="MB/s" max={100} colorKey="docker"   live={live} tick={tick} />

      {/* Budget badge */}
      <div
        className="flex flex-col items-center justify-center px-4 shrink-0"
        style={{ background: 'var(--hud-bg-elev)', minWidth: 110 }}
      >
        <span className="text-[8px] tracking-[0.2em]" style={{ color: 'var(--hud-text-dim)' }}>BUDGET</span>
        <span
          className="text-[15px] font-bold tabular-nums"
          style={{ color: 'var(--color-security)', lineHeight: 1.1 }}
        >
          ${cost.toFixed(4)}
        </span>
        <span className="text-[8px] tracking-wider" style={{ color: 'var(--hud-text-dim)' }}>USD</span>
      </div>
    </footer>
  );
}

// ─── Single hardware bar ────────────────────────────────────────────────────

type ColorKey = 'jarvis' | 'forge' | 'vault' | 'docker' | 'security' | 'cyberdeck';

function HwBar({
  label, value, unit, max, colorKey, live, tick,
}: {
  label: string;
  value: number;
  unit: string;
  max: number;
  colorKey: ColorKey;
  live: boolean;
  tick: number;
}) {
  const c   = `var(--color-${colorKey})`;
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  // Danger threshold colour override (>85%)
  const barColor = pct > 85
    ? 'var(--color-cyberdeck)'
    : pct > 65
    ? 'var(--color-security)'
    : c;

  return (
    <div
      className="flex-1 flex flex-col justify-center px-3 py-1.5 gap-1 min-w-0"
      style={{ background: 'var(--hud-bg-elev)' }}
    >
      {/* Header row */}
      <div className="flex items-center gap-1.5">
        <span className="text-[8px] font-bold tracking-[0.2em]" style={{ color: 'var(--hud-text-dim)' }}>
          {label}
        </span>
        <span
          className="text-[7px] px-1"
          style={{
            color:  live ? 'var(--color-docker)' : 'var(--hud-text-dim)',
            border: `1px solid ${live ? 'var(--color-docker)' : 'var(--hud-border)'}`,
          }}
        >
          {live ? 'LIVE' : 'DEMO'}
        </span>
        <span
          className="ml-auto text-[10px] font-bold tabular-nums"
          style={{ color: barColor }}
        >
          {unit === '%' ? `${Math.round(value)}%` : `${value.toFixed(1)} ${unit}`}
        </span>
      </div>

      {/* Progress bar track */}
      <div
        className="relative w-full overflow-hidden"
        style={{
          height: 5,
          background: 'rgba(0,0,0,0.5)',
          border: `1px solid rgba(0,212,255,0.12)`,
        }}
      >
        {/* Animated fill */}
        <div
          style={{
            position: 'absolute',
            top: 0, left: 0,
            height: '100%',
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${barColor}88, ${barColor})`,
            boxShadow: `0 0 6px ${barColor}`,
            transition: 'width 1.8s ease-out',
          }}
        />
        {/* Scanline shimmer */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.08) 50%, transparent 100%)',
            backgroundSize: '200% 100%',
            animation: `hud-sweep ${1.8 + (tick % 3) * 0.4}s linear infinite`,
          }}
        />
      </div>
    </div>
  );
}

// ─── Demo sine-wave ─────────────────────────────────────────────────────────

function demoVal(seed: number, base: number, amp: number, phase: number): number {
  return base + Math.sin(seed * phase) * amp + (Math.random() - 0.5) * amp * 0.15;
}

import { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, Bot, Cpu, Zap } from 'lucide-react';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchBudget, fetchAgents } from '../../lib/apiLive';

type ColorKey = 'jarvis' | 'forge' | 'vault' | 'docker' | 'security';

interface Point {
  t: number;
  v: number;
}

const RING = 24; // 24 data points = ~2 min at 5s interval

/**
 * BottomPanel — 4 mini metric cards with sparkline.
 * - Budget    (LIVE  · /v1/budget)
 * - Agents    (LIVE  · /v1/agents online count)
 * - CPU/RAM   (DEMO  · sine wave until /v1/health/deep returns metrics)
 * - Energy    (DEMO  · backend stub returns 0)
 */
export function BottomPanel() {
  // ── LIVE series ─────────────────────────────────────
  const budget = useLiveMetric(fetchBudget, { intervalMs: 5000 });
  const agents = useLiveMetric(fetchAgents, { intervalMs: 5000 });
  const budgetSeries = useRing(budget.data?.session?.cost_usd ?? 0, 5000);
  const onlineAgents = agents.data?.agents.filter(a => a.status === 'online').length ?? 0;
  const agentsSeries = useRing(onlineAgents, 5000);

  // ── DEMO series (until Phase 4 adds OS metrics) ─────
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick(x => x + 1), 5000);
    return () => clearInterval(t);
  }, []);
  const cpuSeries    = useMemo(() => synthSeries(tick, 40, 30, 0.55), [tick]);
  const energySeries = useMemo(() => synthSeries(tick, 70, 25, 0.30), [tick]);

  return (
    <footer
      className="shrink-0 grid grid-cols-4 gap-px"
      style={{ height: 100, background: 'var(--hud-border)', borderTop: '1px solid var(--hud-border)' }}
    >
      <MetricCard
        icon={Activity}
        label="BUDGET"
        live={!budget.error && !budget.loading}
        value={budget.data ? `$${(budget.data.session?.cost_usd ?? 0).toFixed(4)}` : '—'}
        unit="USD"
        colorKey="security"
        series={budgetSeries}
      />
      <MetricCard
        icon={Bot}
        label="AGENTS ONLINE"
        live={!agents.error && !agents.loading}
        value={String(onlineAgents)}
        unit="active"
        colorKey="jarvis"
        series={agentsSeries}
      />
      <MetricCard
        icon={Cpu}
        label="CPU LOAD"
        live={false}
        value="—"
        unit="%"
        colorKey="forge"
        series={cpuSeries}
      />
      <MetricCard
        icon={Zap}
        label="ENERGY"
        live={false}
        value="—"
        unit="W"
        colorKey="docker"
        series={energySeries}
      />
    </footer>
  );
}

function MetricCard({
  icon: Icon, label, live, value, unit, colorKey, series,
}: {
  icon: React.ComponentType<{ size?: number; style?: React.CSSProperties }>;
  label: string; live: boolean; value: string; unit: string; colorKey: ColorKey; series: Point[];
}) {
  const c = `var(--color-${colorKey})`;
  const grad = `grad-${colorKey}`;
  return (
    <div className="flex flex-col px-3 py-2 relative" style={{ background: 'var(--hud-bg-elev)' }}>
      <div className="flex items-center gap-2 mb-1">
        <Icon size={12} style={{ color: c }} />
        <span className="text-[9px] tracking-[0.22em]" style={{ color: 'var(--hud-text-dim)' }}>{label}</span>
        <span
          className="ml-auto text-[8px] tracking-wider px-1"
          style={{
            color: live ? 'var(--color-docker)' : 'var(--hud-text-dim)',
            border: `1px solid ${live ? 'var(--color-docker)' : 'var(--hud-border)'}`,
          }}
        >
          {live ? 'LIVE' : 'DEMO'}
        </span>
      </div>

      {/* Sparkline */}
      {/* hauteur fixe (40px) + minWidth=0 + debounce 50ms : evite le warning
          recharts "width(-1) height(-1)" qui apparait quand le parent flex
          n'a pas encore calcule ses dimensions au premier paint. */}
      <div className="-mx-2" style={{ height: 40, flexShrink: 0, flexGrow: 1 }}>
        <ResponsiveContainer width="100%" height="100%" minWidth={0} debounce={50}>
          <AreaChart data={series} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={grad} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor={c} stopOpacity={0.6} />
                <stop offset="100%" stopColor={c} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="v"
              stroke={c}
              strokeWidth={1.5}
              fill={`url(#${grad})`}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-baseline justify-between">
        <span className="text-[15px] font-bold tabular-nums" style={{ color: c, lineHeight: 1 }}>
          {value}
        </span>
        <span className="text-[9px] tracking-wider" style={{ color: 'var(--hud-text-dim)' }}>
          {unit}
        </span>
      </div>
    </div>
  );
}

/** Ring buffer: keeps the last N samples of `value` updated at `intervalMs`. */
function useRing(value: number, intervalMs: number): Point[] {
  const [series, setSeries] = useState<Point[]>(() =>
    Array.from({ length: RING }, (_, i) => ({ t: i, v: 0 })),
  );
  const valRef = useRef(value);
  valRef.current = value;
  useEffect(() => {
    const t = setInterval(() => {
      setSeries(prev => {
        const next = prev.slice(1);
        const lastT = prev[prev.length - 1]?.t ?? 0;
        next.push({ t: lastT + 1, v: Number(valRef.current) || 0 });
        return next;
      });
    }, intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return series;
}

function synthSeries(seed: number, base: number, amp: number, phase: number): Point[] {
  return Array.from({ length: RING }, (_, i) => ({
    t: i,
    v: base + Math.sin((seed + i) * phase) * amp + (Math.random() - 0.5) * amp * 0.3,
  }));
}

import { useState } from 'react';
import { Gauge, Play, Loader2, CheckCircle, AlertTriangle } from 'lucide-react';

/**
 * BenchmarkPage — route `/benchmark`.
 * Client-side latency benchmark of the backend's read endpoints: each is
 * fetched RUNS times (after one warm-up) and timed with performance.now().
 * Reports min/avg/max + ok/fail per endpoint, progressively. Self-contained
 * (no backend changes) — measures real API responsiveness through the proxy.
 */

// Fast read endpoints only — deliberately NOT /v1/health/all or /v1/agents,
// which do live external pings (Claude / Meshy / Ollama) with multi-second
// timeouts and would dominate the numbers + make the run crawl.
const ENDPOINTS: { path: string; label: string }[] = [
  { path: '/v1/boot/info',            label: 'Boot info' },
  { path: '/v1/budget',               label: 'Budget' },
  { path: '/v1/daily/status',         label: 'Scheduler' },
  { path: '/v1/system/metrics',       label: 'System metrics' },
  { path: '/v1/logs',                 label: 'Logs' },
  { path: '/v1/world/cards/snapshot', label: 'World cards' },
];
const RUNS = 6;

interface Result {
  path: string;
  label: string;
  min: number;
  avg: number;
  max: number;
  ok: number;
  fail: number;
}

async function timeOne(path: string): Promise<{ ms: number; ok: boolean }> {
  const t0 = performance.now();
  try {
    const r = await fetch(path, { cache: 'no-store' });
    await r.text();
    return { ms: performance.now() - t0, ok: r.ok };
  } catch {
    return { ms: performance.now() - t0, ok: false };
  }
}

const barColor = (ms: number) =>
  ms > 500 ? 'var(--color-cyberdeck)' : ms > 200 ? 'var(--color-security)' : 'var(--color-docker)';

export function BenchmarkPage() {
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<Result[]>([]);
  const [ranAt, setRanAt] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setResults([]);
    setRanAt(null);
    const out: Result[] = [];
    for (const ep of ENDPOINTS) {
      await timeOne(ep.path); // warm-up (not counted)
      const times: number[] = [];
      let ok = 0;
      let fail = 0;
      for (let i = 0; i < RUNS; i++) {
        const { ms, ok: good } = await timeOne(ep.path);
        times.push(ms);
        if (good) ok += 1;
        else fail += 1;
      }
      out.push({
        path: ep.path,
        label: ep.label,
        min: Math.min(...times),
        max: Math.max(...times),
        avg: times.reduce((a, b) => a + b, 0) / times.length,
        ok,
        fail,
      });
      setResults([...out]); // progressive update
    }
    setRanAt(new Date().toLocaleTimeString());
    setRunning(false);
  };

  const maxAvg = results.length ? Math.max(...results.map((r) => r.avg)) : 1;
  const overallAvg = results.length
    ? results.reduce((a, r) => a + r.avg, 0) / results.length
    : 0;

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5" style={{ background: 'var(--hud-bg)' }}>
      <div className="flex items-center gap-3 text-[10px] font-bold tracking-[0.3em]" style={{ color: 'var(--hud-text-dim)' }}>
        <Gauge size={13} style={{ color: 'var(--color-security)' }} />
        BENCHMARK · API LATENCY
        <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
        {ranAt && <span style={{ color: 'var(--hud-text-dim)' }}>last run {ranAt}</span>}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={run}
          disabled={running}
          className="flex items-center gap-2 px-4 py-2 text-[11px] font-bold tracking-[0.2em]"
          style={{
            background: running ? 'rgba(255,255,255,0.05)' : 'var(--color-security)',
            color: running ? 'var(--color-security)' : '#000',
            border: '1px solid var(--color-security)',
            cursor: running ? 'not-allowed' : 'pointer',
          }}
        >
          {running ? (
            <><Loader2 size={12} className="animate-spin" /> RUNNING…</>
          ) : (
            <><Play size={12} /> RUN BENCHMARK</>
          )}
        </button>
        <span className="text-[9px] tracking-wider" style={{ color: 'var(--hud-text-dim)' }}>
          {RUNS} runs/endpoint · {ENDPOINTS.length} endpoints · 1 warm-up
        </span>
        {results.length > 0 && (
          <span className="ml-auto text-[11px] font-bold tabular-nums" style={{ color: 'var(--color-security)' }}>
            avg {overallAvg.toFixed(0)} ms
          </span>
        )}
      </div>

      <div className="flex flex-col gap-2">
        {results.length === 0 && !running && (
          <div className="text-[10px]" style={{ color: 'var(--hud-text-dim)' }}>
            Click RUN to benchmark backend endpoint latency (client-side fetch timing).
          </div>
        )}
        {results.map((r) => (
          <div key={r.path} style={{ background: 'var(--hud-bg-elev)', border: '1px solid var(--hud-border)', padding: '8px 12px' }}>
            <div className="flex items-center gap-2 text-[10px]">
              {r.fail === 0 ? (
                <CheckCircle size={11} style={{ color: 'var(--color-docker)' }} />
              ) : (
                <AlertTriangle size={11} style={{ color: 'var(--color-cyberdeck)' }} />
              )}
              <span className="font-bold tracking-[0.14em]" style={{ color: 'var(--hud-text)' }}>{r.label}</span>
              <span className="truncate" style={{ color: 'var(--hud-text-dim)' }}>{r.path}</span>
              <span className="ml-auto tabular-nums" style={{ color: barColor(r.avg) }}>avg {r.avg.toFixed(0)} ms</span>
            </div>
            <div className="mt-1.5" style={{ height: 5, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{ width: `${Math.min(100, (r.avg / maxAvg) * 100)}%`, height: '100%', background: barColor(r.avg), transition: 'width 0.3s' }} />
            </div>
            <div className="flex gap-4 mt-1 text-[8.5px] tabular-nums" style={{ color: 'var(--hud-text-dim)' }}>
              <span>min {r.min.toFixed(0)}</span>
              <span>max {r.max.toFixed(0)}</span>
              <span>ok {r.ok}/{r.ok + r.fail}</span>
              {r.fail > 0 && <span style={{ color: 'var(--color-cyberdeck)' }}>fail {r.fail}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

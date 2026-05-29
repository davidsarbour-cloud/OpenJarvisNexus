import { useState } from 'react';
import { motion } from 'motion/react';
import { Power, Activity } from 'lucide-react';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchMiningHealth, fetchMiningPositions, haltMining } from '../../lib/apiLive';

/**
 * MiningControlCard — the live control panel for the Mining cluster.
 *
 * Polls /v1/mining/health + /positions (proxied to the orchestrator :8090).
 * The cluster is normally OFFLINE (docker-compose.mining not running) → the
 * card shows a clean offline state. The big button flips the global circuit
 * breaker via /v1/mining/halt (HALT when running, RESUME when halted).
 */
export function MiningControlCard() {
  const { data: health } = useLiveMetric(fetchMiningHealth, { intervalMs: 5000 });
  const { data: positions } = useLiveMetric(fetchMiningPositions, { intervalMs: 6000 });
  const [busy, setBusy] = useState(false);

  const online = health?.cluster === 'online';
  const hd = health?.data ?? null;
  const halted = !!hd?.halted;
  const mode = hd?.mode ?? '—';
  const tickers = hd?.tickers ?? [];
  const posData = positions?.data ?? null;
  const posCount = posData ? Object.values(posData).filter(Boolean).length : 0;

  const gold = 'var(--color-mining)';
  const red = 'var(--color-cyberdeck)';
  const green = 'var(--color-docker)';

  const doHalt = async (on: boolean) => {
    setBusy(true);
    try { await haltMining(on); } catch { /* offline — ignore */ } finally { setBusy(false); }
  };

  return (
    <div
      className="flex flex-col p-3 relative overflow-hidden h-full"
      style={{
        background: `radial-gradient(130% 80% at 50% 0%, rgba(255,214,10,0.08), transparent 62%), var(--hud-bg-elev)`,
        border: `1px solid rgba(255,214,10,0.28)`,
        boxShadow: 'inset 0 0 24px rgba(0,0,0,0.45)',
        minHeight: 200,
      }}
    >
      <div className="flex items-center gap-2">
        <Activity size={16} style={{ color: gold }} />
        <span className="text-[11px] font-bold tracking-[0.16em]" style={{ color: gold }}>
          MINING CONTROL
        </span>
        <span
          className="ml-auto w-2 h-2 rounded-full"
          title={online ? 'cluster online' : 'cluster offline'}
          style={{
            background: online ? green : '#000',
            boxShadow: online ? `0 0 8px ${green}` : 'none',
            border: online ? 'none' : '1px solid var(--hud-border)',
          }}
        />
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 mt-3 text-[10px]">
        <Stat label="CLUSTER" value={online ? 'ONLINE' : 'OFFLINE'} c={online ? green : 'var(--hud-text-dim)'} />
        <Stat label="MODE" value={String(mode).toUpperCase()} c={mode === 'live' ? red : gold} />
        <Stat label="BOTS" value={String(tickers.length || 5)} c={gold} />
        <Stat label="POSITIONS" value={online ? String(posCount) : '—'} c={gold} />
      </div>

      <div className="flex-1" />

      {halted && (
        <div className="text-[9px] tracking-[0.18em] mb-2 text-center" style={{ color: red }}>
          ⚠ CIRCUIT BREAKER ACTIVE
        </div>
      )}

      <motion.button
        onClick={() => doHalt(!halted)}
        disabled={busy || !online}
        whileTap={{ scale: 0.97 }}
        className="flex items-center justify-center gap-2 px-3 py-2.5 text-[11px] font-bold tracking-[0.2em] cursor-pointer"
        style={{
          color: !online ? 'var(--hud-text-dim)' : '#000',
          background: !online ? 'transparent' : halted ? green : red,
          border: `1px solid ${!online ? 'var(--hud-border)' : halted ? green : red}`,
          opacity: busy || !online ? 0.55 : 1,
          cursor: busy || !online ? 'not-allowed' : 'pointer',
        }}
        title={!online ? 'Mining cluster offline' : halted ? 'Resume trading' : 'Halt all bots'}
      >
        <Power size={13} />
        {!online ? 'CLUSTER OFFLINE' : busy ? '…' : halted ? 'RESUME' : 'HALT ALL'}
      </motion.button>
    </div>
  );
}

function Stat({ label, value, c }: { label: string; value: string; c: string }) {
  return (
    <div className="flex flex-col min-w-0">
      <span className="text-[8px] tracking-[0.14em]" style={{ color: 'var(--hud-text-dim)' }}>{label}</span>
      <span className="text-[14px] font-bold tabular-nums truncate" style={{ color: c, lineHeight: 1.25 }}>{value}</span>
    </div>
  );
}

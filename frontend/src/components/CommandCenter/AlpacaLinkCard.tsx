import { Activity } from 'lucide-react';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchTradingSummary } from '../../lib/apiLive';

/**
 * AlpacaLinkCard — the live broker link for the Mining world.
 *
 * Polls /v1/trading/summary (Alpaca account, paper by default). Three states:
 *  - error            → backend unreachable (red dot)
 *  - !connected       → reachable but no API key pair in .env (gold "LINK REQUIRED")
 *  - connected        → equity / buying power / today's P&L from the account
 *
 * Mirrors MiningControlCard's gold HUD styling. No trading actions here — this
 * is a read-only status card; orders go through the bots / dedicated panels.
 */
export function AlpacaLinkCard() {
  const { data, error } = useLiveMetric(fetchTradingSummary, { intervalMs: 8000 });

  const gold = 'var(--color-mining)';
  const red = 'var(--color-cyberdeck)';
  const green = 'var(--color-docker)';

  const connected = !!data?.connected;
  const paper = data?.paper ?? true;
  const cur = data?.currency ?? 'USD';
  const sym = cur === 'EUR' ? '€' : '$';
  const pnl = data?.pnl_today ?? 0;
  const pnlPct = data?.pnl_today_pct ?? 0;
  const pnlUp = pnl >= 0;

  const dotColor = error ? red : connected ? green : '#000';

  const fmt = (n: number) =>
    `${sym}${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

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
          ALPACA LINK
        </span>
        {connected && (
          <span
            className="text-[8px] font-bold tracking-[0.14em] px-1.5 py-0.5 rounded"
            style={{
              color: paper ? gold : red,
              border: `1px solid ${paper ? gold : red}`,
            }}
          >
            {paper ? 'PAPER' : 'LIVE'}
          </span>
        )}
        <span
          className="ml-auto w-2 h-2 rounded-full"
          title={error ? 'backend offline' : connected ? 'broker connected' : 'not linked'}
          style={{
            background: dotColor,
            boxShadow: connected && !error ? `0 0 8px ${green}` : 'none',
            border: dotColor === '#000' ? '1px solid var(--hud-border)' : 'none',
          }}
        />
      </div>

      {connected ? (
        <>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 mt-3 text-[10px]">
            <Stat label="EQUITY" value={fmt(data?.equity ?? 0)} c={gold} />
            <Stat
              label="P&L TODAY"
              value={`${pnlUp ? '+' : ''}${fmt(pnl)} (${pnlUp ? '+' : ''}${pnlPct.toFixed(2)}%)`}
              c={pnlUp ? green : red}
            />
            <Stat label="BUYING POWER" value={fmt(data?.buying_power ?? 0)} c={gold} />
            <Stat label="CASH" value={fmt(data?.cash ?? 0)} c={gold} />
          </div>
          <div className="flex-1" />
          <div className="text-[8px] tracking-[0.16em] mt-2" style={{ color: 'var(--hud-text-dim)' }}>
            STATUS · {String(data?.status ?? '—').toUpperCase()}
          </div>
        </>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-center gap-1.5">
          <span className="text-[12px] font-bold tracking-[0.12em]" style={{ color: error ? red : gold }}>
            {error ? 'BACKEND OFFLINE' : 'LINK REQUIRED'}
          </span>
          <span className="text-[9px] leading-snug px-2" style={{ color: 'var(--hud-text-dim)' }}>
            {error
              ? 'trading API unreachable'
              : 'Add ALPACA_API_KEY_ID + secret to backend/.env (paper)'}
          </span>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, c }: { label: string; value: string; c: string }) {
  return (
    <div className="flex flex-col min-w-0">
      <span className="text-[8px] tracking-[0.14em]" style={{ color: 'var(--hud-text-dim)' }}>{label}</span>
      <span className="text-[13px] font-bold tabular-nums truncate" style={{ color: c, lineHeight: 1.25 }}>{value}</span>
    </div>
  );
}

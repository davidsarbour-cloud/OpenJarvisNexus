import { DollarSign } from 'lucide-react';
import { HudCard, CardValue } from './HudCard';
import { useLiveMetric } from '../../hooks/useLiveMetric';
import { fetchEtsyRevenue } from '../../lib/apiLive';

/**
 * RevenueCard — Etsy D3Dprintix sales over the last 30 days.
 * Sits under the Daily Report card in the Command Center left dock.
 * Backed by GET /v1/commerce/revenue (paid receipts). Shows "warn" (not "down")
 * when the backend is reachable but Etsy isn't connected yet.
 */
export function RevenueCard() {
  // Revenue moves slowly — poll every 5 min, no WS topic needed.
  const { data, error, loading } = useLiveMetric(() => fetchEtsyRevenue(30), { intervalMs: 300_000 });
  const connected = !!data?.connected;
  const status = error ? 'down' : loading ? 'loading' : connected ? 'live' : 'warn';

  const cur = data?.currency ?? 'USD';
  const sym = cur === 'EUR' ? '€' : '$';
  const total = data?.total ?? 0;
  const today = data?.today ?? 0;
  const orders = data?.orders ?? 0;

  return (
    <HudCard
      title="Revenus Etsy"
      subtitle="D3Dprintix · 30 j (/v1/commerce/revenue)"
      colorKey="commerce"
      icon={DollarSign}
      status={status}
    >
      {connected ? (
        <>
          <CardValue value={`${sym}${total.toFixed(2)}`} unit={`/ 30j · ${cur}`} colorKey="commerce" />
          <div className="mt-2 text-[10px] flex flex-col gap-1">
            <div className="flex justify-between">
              <span style={{ color: 'var(--hud-text-dim)' }}>AUJOURD'HUI</span>
              <span className="tabular-nums" style={{ color: 'var(--color-docker)' }}>{sym}{today.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: 'var(--hud-text-dim)' }}>COMMANDES</span>
              <span className="tabular-nums" style={{ color: 'var(--color-jarvis)' }}>{orders}</span>
            </div>
            {data?.last_order && (
              <div className="flex justify-between">
                <span style={{ color: 'var(--hud-text-dim)' }}>DERNIÈRE</span>
                <span
                  className="truncate ml-2 tabular-nums"
                  style={{ color: 'var(--hud-text)', maxWidth: 150 }}
                  title={data.last_order.name}
                >
                  {sym}{data.last_order.amount.toFixed(2)}
                </span>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="text-[10px] leading-relaxed" style={{ color: 'var(--hud-text-dim)' }}>
          {error
            ? 'Backend injoignable.'
            : 'Etsy non connecté — configure ETSY_ACCESS_TOKEN + ETSY_SHOP_ID dans .env, puis ouvre /v1/etsy/auth.'}
        </div>
      )}
    </HudCard>
  );
}

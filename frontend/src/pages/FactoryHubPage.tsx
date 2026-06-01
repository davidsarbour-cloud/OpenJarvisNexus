/**
 * Nexus9 — Factory Hub.
 *
 * One page for the autonomous Auto-Factory production lines:
 *   STL automated · Icon pack automated · PoD textile automated · Daytrading.
 * The three production lines read /v1/factory (config + catalog + rotation
 * state) and show schedule, rotation progress and the next item up. Daytrading
 * is READ-ONLY — it surfaces the existing Mining orchestrator (/v1/mining),
 * no order execution lives here.
 */
import { useCallback, useEffect, useState } from 'react';
import { Bot, Boxes, CandlestickChart, Gamepad2, Hammer, LayoutDashboard, Play, Shirt, ShoppingCart } from 'lucide-react';
import { toast } from 'sonner';
import { HudCard, type CardStatus } from '../components/CommandCenter/HudCard';
import { cssVar, type ModuleKey } from '../lib/colors';
import {
  fetchFactoryCatalog,
  fetchFactoryConfig,
  fetchMiningHealth,
  fetchMiningPositions,
  postFactoryDryRun,
  type FactoryCatalogItem,
  type FactoryConfigResponse,
  type FactoryCatalogResponse,
  type FactoryLineState,
  type MiningEnvelope,
  type MiningHealth,
} from '../lib/apiLive';

const TIER_RANK: Record<string, number> = { S: 0, A: 1, B: 2 };

/** Mirror the backend tier-rotation pick so the card shows what's next. */
function nextUp(catalog: FactoryCatalogItem[], done: string[]): FactoryCatalogItem | null {
  const doneSet = new Set(done);
  let remaining = catalog.filter((i) => !doneSet.has(i.key));
  if (remaining.length === 0) remaining = [...catalog];
  remaining = [...remaining].sort(
    (a, b) =>
      (TIER_RANK[a.tier] ?? 9) - (TIER_RANK[b.tier] ?? 9) ||
      catalog.indexOf(a) - catalog.indexOf(b),
  );
  return remaining[0] ?? null;
}

const pad = (n: number) => String(n).padStart(2, '0');

function Row({ k, v, color }: { k: string; v: string; color?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 text-[10px] py-0.5">
      <span style={{ color: 'var(--hud-text-dim)' }}>{k}</span>
      <span className="tabular-nums font-bold truncate" style={{ color: color ?? '#ffffff' }}>{v}</span>
    </div>
  );
}

function ProductionLineCard({
  title, sub, icon, colorKey, enabled, time, total, state, catalog,
}: {
  title: string;
  sub: string;
  icon: React.ComponentType<{ size?: number; style?: React.CSSProperties }>;
  colorKey: ModuleKey;
  enabled: boolean;
  time: string;
  total: number;
  state: FactoryLineState | undefined;
  catalog: FactoryCatalogItem[];
}) {
  const done = state?.done ?? [];
  const cycle = state?.cycle ?? 1;
  const next = catalog.length ? nextUp(catalog, done) : null;
  const status: CardStatus = enabled ? 'live' : 'warn';
  return (
    <HudCard title={title} subtitle={sub} colorKey={colorKey} icon={icon} status={status}>
      <Row k="ÉTAT" v={enabled ? 'ACTIF' : 'désactivé'} color={enabled ? cssVar(colorKey) : 'var(--color-security)'} />
      <Row k="DÉCLENCHE" v={`tous les jours ${time}`} />
      <Row k="ROTATION" v={`${done.length}/${total} · cycle ${cycle}`} />
      <Row k="PROCHAIN" v={next ? `${next.label} [${next.tier}]` : '—'} color={cssVar(colorKey)} />
    </HudCard>
  );
}

function DaytradingCard({
  health, positions,
}: {
  health: MiningEnvelope<MiningHealth> | null;
  positions: MiningEnvelope<Record<string, unknown>> | null;
}) {
  const online = health?.cluster === 'online' && !!health?.data;
  const h = health?.data;
  const posCount = positions?.data ? Object.keys(positions.data).length : 0;
  const status: CardStatus = online ? 'live' : 'down';
  return (
    <HudCard title="Daytrading automated" subtitle="signaux — lecture seule"
             colorKey="mining" icon={CandlestickChart} status={status}>
      {online && h ? (
        <>
          <Row k="MODE" v={(h.mode || '?').toUpperCase()} color={cssVar('mining')} />
          <Row k="LIVE" v={h.live_enabled ? 'activé' : 'paper'} />
          <Row k="HALT" v={h.halted ? 'STOPPÉ' : 'actif'} color={h.halted ? 'var(--color-cyberdeck)' : undefined} />
          <Row k="TICKERS" v={(h.tickers || []).join(' ') || '—'} />
          <Row k="POSITIONS" v={String(posCount)} />
        </>
      ) : (
        <div className="text-[10px] py-1" style={{ color: 'var(--hud-text-dim)' }}>
          Cluster Mining hors ligne (:8090). Aucune exécution d'ordre ici — vue
          signaux uniquement. Démarre la stack Mining pour voir les positions.
        </div>
      )}
    </HudCard>
  );
}

export function FactoryHubPage() {
  const [cfg, setCfg] = useState<FactoryConfigResponse | null>(null);
  const [cat, setCat] = useState<FactoryCatalogResponse | null>(null);
  const [mHealth, setMHealth] = useState<MiningEnvelope<MiningHealth> | null>(null);
  const [mPos, setMPos] = useState<MiningEnvelope<Record<string, unknown>> | null>(null);
  const [running, setRunning] = useState(false);

  const refresh = useCallback(() => {
    fetchFactoryConfig().then(setCfg).catch(() => setCfg(null));
    fetchFactoryCatalog().then(setCat).catch(() => setCat(null));
    fetchMiningHealth().then(setMHealth).catch(() => setMHealth(null));
    fetchMiningPositions().then(setMPos).catch(() => setMPos(null));
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, [refresh]);

  const dryRun = useCallback(async () => {
    setRunning(true);
    try {
      const r = await postFactoryDryRun();
      const lines = Object.values(r.detail ?? {}).map((d) => `${d.label} (${d.reason})`);
      toast.success('Aperçu envoyé sur Telegram', {
        description: lines.length ? lines.join(' · ') : 'Aucune ligne sélectionnée.',
      });
    } catch {
      toast.error('Dry run échoué — backend injoignable ?');
    } finally {
      setRunning(false);
    }
  }, []);

  const c = cfg?.config;
  const h = c?.schedule_hour ?? 8;
  const m = c?.schedule_minute ?? 0;
  const products = c?.products ?? [];
  const on = (k: string) => !!c?.enabled && products.includes(k);
  const t = (addMin: number) => `${pad((h + Math.floor((m + addMin) / 60)) % 24)}:${pad((m + addMin) % 60)}`;

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="text-[14px] font-bold tracking-[0.25em]" style={{ color: cssVar('factory') }}>
          FACTORY
        </div>
        <span className="text-[10px] tracking-[0.18em]" style={{ color: 'var(--hud-text-dim)' }}>
          lignes de production autonomes
        </span>
        <button
          onClick={dryRun}
          disabled={running}
          className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-[10px] tracking-wider cursor-pointer"
          style={{
            color: '#000',
            background: cssVar('factory'),
            opacity: running ? 0.5 : 1,
            border: `1px solid ${cssVar('factory')}`,
          }}
        >
          <Play size={11} /> {running ? 'APERÇU…' : 'APERÇU (DRY → TELEGRAM)'}
        </button>
      </div>

      {/* 2×2 grid of lines */}
      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
        <ProductionLineCard
          title="STL automated" sub="figurines & déco 3D → Meshy" icon={Hammer}
          colorKey="forge" enabled={on('stl')} time={t(0)}
          total={cfg?.stl_niches ?? 0} state={cfg?.state.stl} catalog={cat?.stl_niches ?? []}
        />
        <ProductionLineCard
          title="Icon pack automated" sub="packs d'icônes iOS → FLUX" icon={Boxes}
          colorKey="cortex" enabled={on('icons')} time={t(15)}
          total={cfg?.icon_themes ?? 0} state={cfg?.state.icons} catalog={cat?.icon_themes ?? []}
        />
        <ProductionLineCard
          title="PoD textile automated" sub="designs apparel → Printify" icon={Shirt}
          colorKey="commerce" enabled={on('pod')} time={t(30)}
          total={cfg?.pod_designs ?? 0} state={cfg?.state.pod} catalog={cat?.pod_designs ?? []}
        />
        <ProductionLineCard
          title="Game Assets 2D automated" sub="packs d'assets jeu → itch.io" icon={Gamepad2}
          colorKey="security" enabled={on('game2d')} time={t(45)}
          total={cfg?.game2d_packs ?? 0} state={cfg?.state.game2d} catalog={cat?.game2d_packs ?? []}
        />
        <ProductionLineCard
          title="UI Kits jeux automated" sub="kits d'interface jeu → itch.io" icon={LayoutDashboard}
          colorKey="vault" enabled={on('uikit')} time={t(60)}
          total={cfg?.uikit_kits ?? 0} state={cfg?.state.uikit} catalog={cat?.uikit_kits ?? []}
        />
        <ProductionLineCard
          title="AI Packs automated" sub="prompts/workflows (Ollama, brouillon)" icon={Bot}
          colorKey="jarvis" enabled={on('aipack')} time={t(75)}
          total={cfg?.aipack_packs ?? 0} state={cfg?.state.aipack} catalog={cat?.aipack_packs ?? []}
        />
        <ProductionLineCard
          title="Shopify templates automated" sub="sections Liquid (Ollama, brouillon)" icon={ShoppingCart}
          colorKey="docker" enabled={on('shopify')} time={t(90)}
          total={cfg?.shopify_templates ?? 0} state={cfg?.state.shopify} catalog={cat?.shopify_templates ?? []}
        />
        <DaytradingCard health={mHealth} positions={mPos} />
      </div>

      {cfg === null && (
        <div className="mt-3 text-[10px]" style={{ color: 'var(--color-cyberdeck)' }}>
          Backend injoignable — démarre python main.py pour piloter l'usine.
        </div>
      )}
    </div>
  );
}

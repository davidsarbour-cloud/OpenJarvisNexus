import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import ForceGraph2D from 'react-force-graph-2d';
import { useVaultGraph, type VaultGraphNode, type VaultGraphData } from '../components/VaultGraph';
import { groupColor, topGroup } from './brainHubUtils';

// ── Palette constellation ─────────────────────────────────────────────────────

const BG           = 'rgba(2, 4, 12, 0.0)'; // transparent — starfield canvas underneath
const VAULT_ACCENT = '#a855f7';
const VAULT_GLOW   = 'rgba(168,85,247,0.6)';

/**
 * Each top-level group gets a fixed angular slot on a big ring.
 * Constellation centers are placed at radius 420 in graph coordinates.
 * Orphans get an outer ring far from the action so they don't pollute the view.
 */
// Default spread — overridable via the +/- buttons (1..50). Spread maps to the
// d3-force repulsion + link length, like Obsidian's force-graph: a plain
// force-directed layout, no imposed ring/cluster anchors.
const SPREAD_DEFAULT = 36;
const spreadToCharge   = (s: number) => -(60 + s * 12);  // s=36 → -492, s=50 → -660
const spreadToLinkDist = (s: number) => 30 + s * 3.5;    // s=36 → 156, s=50 → 205

// ── Types ─────────────────────────────────────────────────────────────────────

interface DecoratedNode extends VaultGraphNode {
  degree: number;
}

// react-force-graph mutates link.source/target from an id string to the node
// object after the first tick, so read the id either way.
const linkEndId = (e: unknown): string =>
  typeof e === 'object' && e !== null ? (e as { id: string }).id : (e as string);

function decorateGraph(g: VaultGraphData | null) {
  if (!g) return { nodes: [] as DecoratedNode[], links: [] as { source: string; target: string }[] };
  // Drop dangling links — the vault graph can emit links to something that
  // isn't a node (a scheduled-job id like `skill-brain-stubs-check`, or a
  // relative path). d3's link force throws "node not found" / "cannot set vx
  // on string" on those, which crashes the whole graph. Obsidian does the same.
  const ids = new Set(g.nodes.map((n) => n.id));
  const links = g.links.filter(
    (l) => ids.has(linkEndId(l.source)) && ids.has(linkEndId(l.target)),
  );
  const degree = new Map<string, number>();
  for (const l of links) {
    const s = linkEndId(l.source);
    const t = linkEndId(l.target);
    degree.set(s, (degree.get(s) ?? 0) + 1);
    degree.set(t, (degree.get(t) ?? 0) + 1);
  }
  return {
    nodes: g.nodes.map((n) => ({ ...n, degree: degree.get(n.id) ?? 0 })),
    links,
  };
}

// ── Starfield ─────────────────────────────────────────────────────────────────

interface Star { x: number; y: number; r: number; a: number; twinkle: number }

function useStarfield(canvasRef: React.RefObject<HTMLCanvasElement | null>) {
  const starsRef = useRef<Star[]>([]);
  const rafRef   = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      // regenerate stars on resize
      starsRef.current = Array.from({ length: 220 }, () => ({
        x:       Math.random() * canvas.width,
        y:       Math.random() * canvas.height,
        r:       Math.random() * 1.2 + 0.2,
        a:       Math.random(),
        twinkle: Math.random() * Math.PI * 2,
      }));
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    let t = 0;
    const draw = () => {
      t += 0.008;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // deep space gradient
      const grad = ctx.createRadialGradient(
        canvas.width * 0.5, canvas.height * 0.5, 0,
        canvas.width * 0.5, canvas.height * 0.5, Math.max(canvas.width, canvas.height) * 0.75,
      );
      grad.addColorStop(0,   'rgba(8, 6, 28, 1)');
      grad.addColorStop(0.5, 'rgba(4, 4, 18, 1)');
      grad.addColorStop(1,   'rgba(2, 2, 10, 1)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // nebula blobs
      const nebulae = [
        { x: canvas.width * 0.2,  y: canvas.height * 0.3, r: 280, color: 'rgba(168,85,247,0.045)' },
        { x: canvas.width * 0.8,  y: canvas.height * 0.7, r: 220, color: 'rgba(34,211,238,0.035)' },
        { x: canvas.width * 0.55, y: canvas.height * 0.2, r: 180, color: 'rgba(251,191,36,0.025)' },
      ];
      for (const nb of nebulae) {
        const g2 = ctx.createRadialGradient(nb.x, nb.y, 0, nb.x, nb.y, nb.r);
        g2.addColorStop(0,   nb.color);
        g2.addColorStop(1,   'transparent');
        ctx.fillStyle = g2;
        ctx.beginPath();
        ctx.arc(nb.x, nb.y, nb.r, 0, Math.PI * 2);
        ctx.fill();
      }

      // stars
      for (const s of starsRef.current) {
        const alpha = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(t * 0.9 + s.twinkle));
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${(alpha * s.a).toFixed(3)})`;
        ctx.fill();
      }

      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, [canvasRef]);
}

// ── Component ─────────────────────────────────────────────────────────────────

export function BrainHubPage() {
  const navigate = useNavigate();
  const { graph, state, error } = useVaultGraph({ enabled: true });
  const [hoverId, setHoverId]   = useState<string | null>(null);
  const [size, setSize]         = useState({ width: 0, height: 0 });
  const [spread, setSpread]     = useState<number>(SPREAD_DEFAULT);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef        = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const starCanvasRef= useRef<HTMLCanvasElement>(null);

  useStarfield(starCanvasRef);

  // Measure container
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() =>
      setSize({ width: el.clientWidth, height: el.clientHeight })
    );
    ro.observe(el);
    setSize({ width: el.clientWidth, height: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  const decorated = useMemo(() => decorateGraph(graph), [graph]);

  // Plain force-directed layout (Obsidian Graph-view style): nodes repel,
  // links pull, and the built-in centre force keeps everything on screen — no
  // imposed ring/cluster anchors. The spread (+/- buttons) scales repulsion +
  // link length; re-fit after each change so the graph stays framed.
  useEffect(() => {
    const fg = fgRef.current;
    if (!graph || !fg) return;
    const charge = fg.d3Force('charge');
    if (charge) charge.strength(spreadToCharge(spread)).distanceMax(800);
    const link = fg.d3Force('link');
    if (link) link.distance(spreadToLinkDist(spread));

    // Gentle group cohesion: nudge each note toward the LIVE centroid of its
    // 00/01/02… folder so same-folder notes cluster into visible groups, while
    // charge keeps the whole map spread. Organic — no fixed anchors. Meta nodes
    // (tags/orphans) are left free so they don't collapse into one giant blob.
    type SimNode = DecoratedNode & { x?: number; y?: number; vx?: number; vy?: number };
    let simNodes: SimNode[] = [];
    const groupForce = (alpha: number) => {
      const k = 0.12 * alpha;
      const acc = new Map<string, { x: number; y: number; n: number }>();
      for (const nd of simNodes) {
        if (nd.x === undefined || nd.y === undefined) continue;
        const g = topGroup(nd.group);
        if (g === '_orphan') continue;
        const e = acc.get(g) ?? { x: 0, y: 0, n: 0 };
        e.x += nd.x; e.y += nd.y; e.n += 1;
        acc.set(g, e);
      }
      for (const nd of simNodes) {
        if (nd.x === undefined || nd.y === undefined) continue;
        const e = acc.get(topGroup(nd.group));
        if (!e) continue;
        nd.vx = (nd.vx ?? 0) + (e.x / e.n - nd.x) * k;
        nd.vy = (nd.vy ?? 0) + (e.y / e.n - nd.y) * k;
      }
    };
    (groupForce as unknown as { initialize: (n: SimNode[]) => void }).initialize = (n) => {
      simNodes = n;
    };
    fg.d3Force('group', groupForce);

    fg.d3ReheatSimulation?.();
    const t = window.setTimeout(() => fg.zoomToFit(700, 60), 1400);
    return () => window.clearTimeout(t);
  }, [graph, spread]);

  // ── Node painter (constellation style) ──────────────────────────────────────
  const paintNode = useCallback(
    (raw: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = raw as DecoratedNode & { x?: number; y?: number };
      if (n.x === undefined || n.y === undefined) return;

      const isHover  = hoverId === n.id;
      const isOrphan = n.group === '_orphan';
      const isTag    = typeof n.group === 'string' && n.group.startsWith('_tag');
      const isMeta   = isOrphan || isTag;
      const color    = isMeta ? 'rgba(200,210,235,0.55)' : groupColor(n.group);

      // Flat dot — Obsidian Graph-view style: no halo/glow. Size scales gently
      // with the number of links; colour = folder group.
      const r = isHover
        ? 4
        : isMeta
          ? 1.6
          : Math.min(7, 2.4 + Math.sqrt(n.degree) * 0.9);
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Label only on hover — otherwise it stays "just dots + links".
      if (isHover) {
        const fontSize = Math.max(10 / globalScale, 3);
        ctx.font = `${fontSize}px 'IBM Plex Mono', ui-monospace, monospace`;
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'top';
        const label  = n.id.length > 28 ? n.id.slice(0, 26) + '…' : n.id;
        const labelY = n.y + r + 2;
        ctx.fillStyle = 'rgba(2,4,12,0.8)';
        ctx.fillText(label, n.x + 0.5, labelY + 0.5);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, n.x, labelY);
      }
    },
    [hoverId],
  );

  // ── Status bar ───────────────────────────────────────────────────────────────
  const statusLabel: Record<typeof state, string> = {
    connecting: 'CONNECTING',
    open:       'LIVE',
    closed:     'OFFLINE',
    error:      'ERROR',
  };
  const statusColor =
    state === 'open'    ? VAULT_ACCENT
    : state === 'error' ? '#ff2d55'
    : 'rgba(255,255,255,0.45)';

  // Group legend
  const activeGroups = useMemo(() => {
    if (!graph) return [];
    const seen = new Set<string>();
    for (const n of graph.nodes) if (n.group && n.group !== '_orphan') seen.add(n.group);
    return [...seen].sort();
  }, [graph]);

  return (
    <div
      ref={containerRef}
      className="relative overflow-hidden"
      style={{ width: '100%', height: '100%', fontFamily: "'IBM Plex Mono', ui-monospace, monospace" }}
    >
      {/* ── Starfield canvas (background layer) ── */}
      <canvas
        ref={starCanvasRef}
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 0 }}
      />

      {/* ── ForceGraph (constellation layer) ── */}
      {size.width > 0 && size.height > 0 && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
          <ForceGraph2D
            ref={fgRef}
            width={size.width}
            height={size.height}
            backgroundColor={BG}
            graphData={decorated}
            nodeRelSize={5}
            linkColor={() => 'rgba(165,180,220,0.4)'}
            linkWidth={1}
            cooldownTicks={600}
            warmupTicks={120}
            d3AlphaDecay={0.008}
            d3VelocityDecay={0.35}
            onNodeHover={(n) => setHoverId(n ? (n as VaultGraphNode).id : null)}
            nodeCanvasObject={paintNode}
            nodeCanvasObjectMode={() => 'replace'}
            nodePointerAreaPaint={(raw, color, ctx) => {
              const n = raw as DecoratedNode & { x?: number; y?: number };
              if (n.x === undefined || n.y === undefined) return;
              const r = 7; // small uniform hit area for the mini dots
              ctx.beginPath();
              ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
              ctx.fillStyle = color;
              ctx.fill();
            }}
          />
        </div>
      )}

      {/* ── HUD overlays (above graph) ── */}

      {/* ← Back button */}
      <button
        onClick={() => navigate('/')}
        title="Retour au Command Center"
        style={{
          position: 'absolute', top: 14, left: 16, zIndex: 10,
          padding: '5px 12px',
          border: '1px solid rgba(168,85,247,0.4)',
          background: 'rgba(2,4,12,0.82)',
          color: 'rgba(168,85,247,0.75)',
          fontSize: 9, letterSpacing: '0.25em',
          cursor: 'pointer', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', gap: 6,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = VAULT_ACCENT;
          e.currentTarget.style.color = VAULT_ACCENT;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'rgba(168,85,247,0.4)';
          e.currentTarget.style.color = 'rgba(168,85,247,0.75)';
        }}
      >
        ◀ BACK
      </button>

      {/* Header */}
      <div style={{
        position: 'absolute', top: 14, left: 110, zIndex: 10,
        padding: '5px 14px',
        border: `1px solid ${VAULT_ACCENT}`,
        background: 'rgba(2,4,12,0.82)',
        fontSize: 10, fontWeight: 700, letterSpacing: '0.3em',
        color: VAULT_ACCENT,
        textShadow: `0 0 10px ${VAULT_GLOW}`,
        pointerEvents: 'none',
      }}>
        ◆ BRAIN HUB · CONSTELLATION
      </div>

      {/* Status */}
      <div style={{
        position: 'absolute', top: 14, left: '50%', transform: 'translateX(-50%)', zIndex: 10,
        padding: '4px 12px',
        border: `1px solid ${statusColor}`,
        background: 'rgba(2,4,12,0.82)',
        fontSize: 9, letterSpacing: '0.3em',
        color: statusColor,
        pointerEvents: 'none',
        whiteSpace: 'nowrap',
      }}>
        ● {statusLabel[state]}
        {graph?.stats ? ` · ${graph.stats.files} NOTES · ${graph.stats.links} LINKS` : ''}
        {error ? ` · ${error}` : ''}
      </div>

      {/* Spread slider (vertical, dark purple) */}
      <div style={{
        position: 'absolute', right: 18, top: '50%', transform: 'translateY(-50%)', zIndex: 10,
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
        padding: '10px 8px',
        border: '1px solid rgba(168,85,247,0.4)',
        background: 'rgba(2,4,12,0.82)',
        fontFamily: 'inherit',
      }}>
        <div style={{
          fontSize: 8, letterSpacing: '0.25em',
          color: 'rgba(168,85,247,0.65)',
        }}>
          SPREAD
        </div>
        <div style={{
          fontSize: 13, fontWeight: 700, fontVariantNumeric: 'tabular-nums',
          color: VAULT_ACCENT, textShadow: `0 0 8px ${VAULT_GLOW}`,
          minWidth: 22, textAlign: 'center',
        }}>
          {spread}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <button
            type="button"
            onClick={() => setSpread((s) => Math.min(50, s + 3))}
            aria-label="Increase spread"
            style={{
              width: 32, height: 32,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(168,85,247,0.14)',
              border: `1px solid ${VAULT_ACCENT}`,
              color: VAULT_ACCENT,
              fontSize: 20, fontWeight: 700, lineHeight: 1,
              cursor: 'pointer', borderRadius: 4, fontFamily: 'inherit',
            }}
          >
            +
          </button>
          <button
            type="button"
            onClick={() => setSpread((s) => Math.max(1, s - 3))}
            aria-label="Decrease spread"
            style={{
              width: 32, height: 32,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(168,85,247,0.14)',
              border: `1px solid ${VAULT_ACCENT}`,
              color: VAULT_ACCENT,
              fontSize: 20, fontWeight: 700, lineHeight: 1,
              cursor: 'pointer', borderRadius: 4, fontFamily: 'inherit',
            }}
          >
            −
          </button>
        </div>
        <div style={{
          fontSize: 7, letterSpacing: '0.18em',
          color: 'rgba(168,85,247,0.45)',
        }}>
          1—50
        </div>
      </div>

      {/* Zoom to fit button */}
      <button
        onClick={() => fgRef.current?.zoomToFit(500, 80)}
        title="Recentrer la constellation"
        style={{
          position: 'absolute', top: 14, right: 16, zIndex: 10,
          padding: '5px 12px',
          border: '1px solid rgba(168,85,247,0.4)',
          background: 'rgba(2,4,12,0.82)',
          color: 'rgba(168,85,247,0.8)',
          fontSize: 9, letterSpacing: '0.25em',
          cursor: 'pointer', fontFamily: 'inherit',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.borderColor = VAULT_ACCENT)}
        onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(168,85,247,0.4)')}
      >
        ⊹ FIT
      </button>

      {/* Group legend (bottom-left) */}
      {activeGroups.length > 0 && (
        <div style={{
          position: 'absolute', bottom: 14, left: 16, zIndex: 10,
          display: 'flex', flexDirection: 'column', gap: 4,
          pointerEvents: 'none',
        }}>
          {activeGroups.map((g) => (
            <div key={g} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{
                width: 7, height: 7, borderRadius: '50%',
                background: groupColor(g),
                boxShadow: `0 0 6px ${groupColor(g)}`,
                flexShrink: 0,
              }} />
              <span style={{ fontSize: 8, letterSpacing: '0.2em', color: 'rgba(255,255,255,0.5)' }}>
                {g}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Hint (bottom-centre) */}
      <div style={{
        position: 'absolute', bottom: 14, left: '50%', transform: 'translateX(-50%)', zIndex: 10,
        padding: '4px 12px',
        border: '1px solid rgba(255,255,255,0.12)',
        background: 'rgba(2,4,12,0.75)',
        fontSize: 9, letterSpacing: '0.22em',
        color: 'rgba(255,255,255,0.35)',
        pointerEvents: 'none',
        whiteSpace: 'nowrap',
      }}>
        DRAG · SCROLL ZOOM · HOVER NODE · ⊹ FIT
      </div>

      {/* Empty state */}
      {state === 'open' && graph && graph.nodes.length === 0 && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 5,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          pointerEvents: 'none',
          color: 'rgba(255,255,255,0.35)', fontSize: 11, letterSpacing: '0.25em',
        }}>
          VAULT VIDE · AJOUTE DES NOTES .md DANS OBSIDIAN
        </div>
      )}

      {/* Connecting / Offline state */}
      {state !== 'open' && !graph && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 5,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16,
          pointerEvents: 'none',
        }}>
          {/* Pulsing orb */}
          <div style={{
            width: 48, height: 48, borderRadius: '50%',
            border: `2px solid ${VAULT_ACCENT}`,
            boxShadow: `0 0 24px ${VAULT_GLOW}, inset 0 0 12px ${VAULT_GLOW}`,
            animation: state === 'connecting' ? 'brain-pulse 1.6s ease-in-out infinite' : 'none',
          }} />
          <style>{`
            @keyframes brain-pulse {
              0%, 100% { opacity: 0.4; transform: scale(0.95); }
              50%       { opacity: 1.0; transform: scale(1.05); box-shadow: 0 0 40px ${VAULT_GLOW}; }
            }
          `}</style>
          <div style={{ color: VAULT_ACCENT, fontSize: 10, letterSpacing: '0.4em', fontWeight: 700 }}>
            {state === 'connecting' ? '● CONNEXION AU VAULT…' : '○ VAULT OFFLINE'}
          </div>
          {state !== 'connecting' && (
            <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 9, letterSpacing: '0.2em', textAlign: 'center' }}>
              Lance START_ALL.bat · vault_graph service sur :8084
            </div>
          )}
        </div>
      )}
    </div>
  );
}

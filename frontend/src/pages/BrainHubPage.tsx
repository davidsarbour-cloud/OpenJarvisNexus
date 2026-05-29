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
// Default constellation spread — overridable via the side slider (1..50).
const SPREAD_DEFAULT = 12;
const SPREAD_TO_RADIUS = (s: number) => 200 + (s / 50) * 1500; // 1→230, 25→950, 50→1700
const GROUP_ORDER = [
  '00_Core',
  '01_Inbox',
  '02_Daily',
  '03_Projects',
  '04_Areas',
  '05_Resources',
  '06_Agents',
  '07_Schemas',
  '08_Command-Center',
  '09_Archives',
] as const;

// Meta buckets (tags, orphans) get their own slots on an OUTER ring so they
// stay tidy clusters instead of scattering across the whole view by id-hash.
const META_ORDER = ['_tag', '_orphan'] as const;
const META_RADIUS_MULT = 1.9;

/**
 * Collapse a node's raw group to its layout bucket: either a Johnny-Decimal
 * top group (00_Core…09_Archives) or a meta bucket. `topGroup` already maps
 * everything uncategorised to '_orphan', so we split tags back out here.
 */
function layoutBucket(group: string | undefined): string {
  const top = topGroup(group);
  if (top !== '_orphan') return top;
  if (group && group.startsWith('_tag')) return '_tag';
  return '_orphan'; // true orphans + _root + imported + undefined
}

function constellationCenter(
  group: string | undefined,
  radius: number,
): { x: number; y: number } | null {
  const bucket = layoutBucket(group);

  // Real categories → inner ring.
  const idx = GROUP_ORDER.indexOf(bucket as typeof GROUP_ORDER[number]);
  if (idx >= 0) {
    const angle = (idx / GROUP_ORDER.length) * Math.PI * 2 - Math.PI / 2;
    return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
  }

  // Meta buckets (tags, orphans) → dedicated slots on an outer ring, offset a
  // half-step so they sit between the inner spokes rather than on top of them.
  const midx = META_ORDER.indexOf(bucket as typeof META_ORDER[number]);
  if (midx >= 0) {
    const r = radius * META_RADIUS_MULT;
    const angle =
      (midx / META_ORDER.length) * Math.PI * 2 - Math.PI / 2 + Math.PI / META_ORDER.length;
    return { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
  }

  return null;
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface DecoratedNode extends VaultGraphNode {
  degree: number;
}

function decorateGraph(g: VaultGraphData | null) {
  if (!g) return { nodes: [] as DecoratedNode[], links: [] as { source: string; target: string }[] };
  const degree = new Map<string, number>();
  for (const l of g.links) {
    degree.set(l.source, (degree.get(l.source) ?? 0) + 1);
    degree.set(l.target, (degree.get(l.target) ?? 0) + 1);
  }
  return {
    nodes: g.nodes.map((n) => ({ ...n, degree: degree.get(n.id) ?? 0 })),
    links: g.links,
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
  const radiusRef               = useRef<number>(SPREAD_TO_RADIUS(SPREAD_DEFAULT));
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

  // ── Tune the d3-force simulation to spread notes into constellations ──────
  // Configure after every new graph load so the forces apply to the fresh nodes.
  useEffect(() => {
    if (!graph || !fgRef.current) return;

    // 1. Local repulsion: push nodes apart but only at short range
    //    (distanceMax 220) — prevents one constellation pushing the next.
    const charge = fgRef.current.d3Force('charge');
    if (charge) charge.strength(-160).distanceMax(220);

    // 2. Link force = group-aware. Within-group links pull tight (form the
    //    constellation pattern); cross-group links are nearly massless so
    //    they don't drag two constellations into each other.
    type LinkEnd = string | { group?: string };
    const linkGroup = (end: LinkEnd): string => {
      if (typeof end === 'object' && end && 'group' in end) return topGroup(end.group);
      return '_orphan';
    };
    const linkForce = fgRef.current.d3Force('link');
    if (linkForce) {
      linkForce
        .distance((l: { source: LinkEnd; target: LinkEnd }) => {
          const same = linkGroup(l.source) === linkGroup(l.target);
          return same ? 32 : 480;
        })
        .strength((l: { source: LinkEnd; target: LinkEnd }) => {
          const same = linkGroup(l.source) === linkGroup(l.target);
          return same ? 0.7 : 0.015;
        });
    }

    // 3. Strong cluster force pulls each node toward its top-group anchor.
    //    With weakened cross-group links, this is what wins: each group
    //    becomes a distinct constellation around the ring.
    type SimNode = DecoratedNode & { x?: number; y?: number; vx?: number; vy?: number };
    let simNodes: SimNode[] = [];
    const orphanAngle = (id: string) => {
      let h = 0;
      for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
      return (h % 360) * (Math.PI / 180);
    };
    const clusterForce = (alpha: number) => {
      const k = 0.55 * alpha;
      // Read radius live from ref → slider changes reshape positions in real time.
      const r = radiusRef.current;
      const orphanR = r * 1.5;
      for (const n of simNodes) {
        if (n.x === undefined || n.y === undefined) continue;
        let cx: number, cy: number;
        const c = constellationCenter(n.group, r);
        if (c) {
          cx = c.x;
          cy = c.y;
        } else {
          const a = orphanAngle(n.id);
          cx = Math.cos(a) * orphanR;
          cy = Math.sin(a) * orphanR;
        }
        n.vx = (n.vx ?? 0) + (cx - n.x) * k;
        n.vy = (n.vy ?? 0) + (cy - n.y) * k;
      }
    };
    (clusterForce as unknown as { initialize: (n: SimNode[]) => void }).initialize = (n) => {
      simNodes = n;
    };
    fgRef.current.d3Force('cluster', clusterForce);

    // 4. Kill the default center force — it would re-pull everything to (0,0)
    //    and undo the constellation spread. Our cluster anchors are enough.
    fgRef.current.d3Force('center', null);

    // 5. Reheat so new forces actually shape the layout.
    fgRef.current.d3ReheatSimulation?.();
  }, [graph]);

  // Live update when the spread slider moves: push new radius into ref + reheat.
  useEffect(() => {
    radiusRef.current = SPREAD_TO_RADIUS(spread);
    if (fgRef.current && graph) {
      fgRef.current.d3ReheatSimulation?.();
    }
  }, [spread, graph]);

  // Auto-fit on the real constellations only (exclude the outer tag/orphan
  // rings) so the useful clusters fill the screen instead of being squished
  // by the far-flung meta nodes. The ⊹ FIT button still frames everything.
  useEffect(() => {
    if (!graph) return;
    // Wait longer — the new spread takes more ticks to settle.
    const t = window.setTimeout(
      () =>
        fgRef.current?.zoomToFit(800, 100, (n: object) =>
          (GROUP_ORDER as readonly string[]).includes(topGroup((n as VaultGraphNode).group)),
        ),
      1500,
    );
    return () => window.clearTimeout(t);
  }, [graph]);

  // ── Node painter (constellation style) ──────────────────────────────────────
  const paintNode = useCallback(
    (raw: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = raw as DecoratedNode & { x?: number; y?: number };
      if (n.x === undefined || n.y === undefined) return;

      const isHover  = hoverId === n.id;
      const isHub    = n.degree >= 5;
      const isOrphan = n.group === '_orphan';
      const color    = isOrphan ? 'rgba(255,255,255,0.25)' : groupColor(n.group);

      // Node radius — bigger than before, scales with connections
      const r = isOrphan
        ? 2
        : 3.5 + Math.sqrt(n.degree) * 2.2;

      // ── Outer nebula halo for hub nodes ──
      if (isHub || isHover) {
        const haloR = r + (isHover ? 14 : 10);
        const halo  = ctx.createRadialGradient(n.x, n.y, r * 0.5, n.x, n.y, haloR);
        // 88 hex alpha works for hex colors; orphan/rgba colors are used as-is.
        const haloColor = color.startsWith('#') ? `${color}88` : color;
        halo.addColorStop(0, isHover ? VAULT_GLOW : haloColor);
        halo.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.arc(n.x, n.y, haloR, 0, 2 * Math.PI);
        ctx.fillStyle = halo;
        ctx.fill();
      }

      // ── Core glow ring ──
      if (!isOrphan) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 2, 0, 2 * Math.PI);
        ctx.fillStyle = `${color}30`;
        ctx.fill();
      }

      // ── Main dot ──
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = isOrphan ? 'rgba(255,255,255,0.2)' : color;
      ctx.fill();

      // ── Inner bright core ──
      if (!isOrphan && r > 3) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r * 0.4, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(255,255,255,0.9)';
        ctx.fill();
      }

      // ── Label ── always visible for non-orphans, or on hover
      const showLabel = isHover || (!isOrphan && globalScale > 0.5) || (isOrphan && isHover);
      if (showLabel) {
        const minFs  = isHover ? 3.5 : 2.8;
        const fontSize = Math.max(11 / globalScale, minFs);
        ctx.font = `${isHub ? 'bold ' : ''}${fontSize}px 'IBM Plex Mono', ui-monospace, monospace`;
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'top';

        const label  = n.id.length > 24 ? n.id.slice(0, 22) + '…' : n.id;
        const labelY = n.y + r + 2.5;

        // Shadow for readability on dark background
        ctx.fillStyle = 'rgba(2,4,12,0.7)';
        ctx.fillText(label, n.x + 0.5, labelY + 0.5);

        ctx.fillStyle = isHover ? '#ffffff' : isHub ? color : 'rgba(255,255,255,0.75)';
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
            linkColor={() => 'rgba(168,85,247,0.35)'}
            linkWidth={0.8}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={1.5}
            linkDirectionalParticleColor={() => VAULT_ACCENT}
            linkDirectionalParticleSpeed={0.004}
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
              const r = 3.5 + Math.sqrt((n as DecoratedNode).degree) * 2.2 + 6;
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
        <div style={{
          width: 26, height: 200,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <input
            type="range"
            min={1}
            max={50}
            step={1}
            value={spread}
            onChange={(e) => setSpread(parseInt(e.target.value, 10))}
            aria-label="Constellation spread"
            className="brain-spread-slider"
            style={{
              width: 200, // horizontal width; rotated into a vertical track
              transform: 'rotate(-90deg)',
              accentColor: VAULT_ACCENT,
              cursor: 'pointer',
              background: 'transparent',
            }}
          />
        </div>
        <style>{`
          input.brain-spread-slider {
            -webkit-appearance: none;
            appearance: none;
            background: transparent;
            height: 6px;
            outline: none;
          }
          input.brain-spread-slider::-webkit-slider-runnable-track {
            background: linear-gradient(to right,
              rgba(168,85,247,0.15) 0%,
              rgba(168,85,247,0.45) 50%,
              rgba(168,85,247,0.85) 100%);
            height: 4px;
            border-radius: 2px;
          }
          input.brain-spread-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            margin-top: -5px;
            width: 14px; height: 14px;
            background: #6b21a8;
            border: 1px solid ${VAULT_ACCENT};
            box-shadow: 0 0 8px ${VAULT_GLOW};
            border-radius: 50%;
            cursor: pointer;
          }
          input.brain-spread-slider::-moz-range-track {
            background: linear-gradient(to right,
              rgba(168,85,247,0.15) 0%,
              rgba(168,85,247,0.45) 50%,
              rgba(168,85,247,0.85) 100%);
            height: 4px;
            border-radius: 2px;
            border: none;
          }
          input.brain-spread-slider::-moz-range-thumb {
            width: 14px; height: 14px;
            background: #6b21a8;
            border: 1px solid ${VAULT_ACCENT};
            box-shadow: 0 0 8px ${VAULT_GLOW};
            border-radius: 50%;
            cursor: pointer;
          }
        `}</style>
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

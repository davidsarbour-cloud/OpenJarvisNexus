import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useVaultGraph, type VaultGraphNode, type VaultGraphData } from '../components/VaultGraph';

// ── Palette constellation ─────────────────────────────────────────────────────

const BG           = 'rgba(2, 4, 12, 0.0)'; // transparent — starfield canvas underneath
const VAULT_ACCENT = '#a855f7';
const VAULT_GLOW   = 'rgba(168,85,247,0.6)';

/** Couleur par dossier Obsidian (Johnny Decimal prefix) */
const GROUP_COLORS: Record<string, string> = {
  '00_Core':            '#22d3ee', // cyan
  '01_Inbox':           '#fbbf24', // amber
  '02_Daily':           '#4ade80', // green
  '03_Projects':        '#fb923c', // orange
  '04_Areas':           '#60a5fa', // blue
  '05_Resources':       '#a78bfa', // violet
  '06_Agents':          '#f87171', // red
  '07_Schemas':         '#f472b6', // pink
  '08_Command-Center':  '#e879f9', // fuchsia
  '09_Archives':        '#94a3b8', // slate
  '_orphan':            'rgba(255,255,255,0.25)',
};

function groupColor(group: string | undefined): string {
  if (!group) return '#ffffff';
  // match prefix like "03_Projects"
  for (const [key, col] of Object.entries(GROUP_COLORS)) {
    if (group.startsWith(key) || group === key) return col;
  }
  return '#ffffff';
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
  const { graph, state, error } = useVaultGraph({ enabled: true });
  const [hoverId, setHoverId]   = useState<string | null>(null);
  const [size, setSize]         = useState({ width: 0, height: 0 });
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

  // Auto-fit with generous padding so full constellation is visible
  useEffect(() => {
    if (!graph) return;
    const t = window.setTimeout(() => fgRef.current?.zoomToFit(600, 80), 300);
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
        halo.addColorStop(0, isHover ? VAULT_GLOW : `${color}88`);
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
            cooldownTicks={180}
            warmupTicks={60}
            d3AlphaDecay={0.018}
            d3VelocityDecay={0.28}
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

      {/* Header */}
      <div style={{
        position: 'absolute', top: 14, left: 16, zIndex: 10,
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

      {/* Offline state */}
      {state !== 'open' && !graph && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 5,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12,
          pointerEvents: 'none',
        }}>
          <div style={{ color: VAULT_ACCENT, fontSize: 28, textShadow: `0 0 20px ${VAULT_GLOW}` }}>◆</div>
          <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, letterSpacing: '0.25em' }}>
            {state === 'connecting'
              ? 'CONNEXION AU VAULT…'
              : 'VAULT OFFLINE · LANCE vault_graph SERVICE SUR :8084'}
          </div>
        </div>
      )}
    </div>
  );
}

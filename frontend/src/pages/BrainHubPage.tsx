import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useVaultGraph, type VaultGraphNode, type VaultGraphData } from '../components/VaultGraph';

const VAULT_ACCENT = '#a855f7';
const VAULT_GLOW   = 'rgba(168, 85, 247, 0.55)';
const BG           = 'rgba(2, 5, 11, 0.0)'; // transparent — parent already has HUD bg

interface DecoratedNode extends VaultGraphNode {
  degree: number;
}

function decorateGraph(g: VaultGraphData | null): {
  nodes: DecoratedNode[];
  links: { source: string; target: string }[];
} {
  if (!g) return { nodes: [], links: [] };
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

/**
 * BrainHubPage — route `/brain`.
 *
 * Full-page embedded Vault/Obsidian graph inside the HudLayout outlet.
 * Connects to the vault_graph sidecar (ws://localhost:8083).
 * No overlay — lives as a proper HUD page.
 */
export function BrainHubPage() {
  const { graph, state, error } = useVaultGraph({ enabled: true });
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Measure the container instead of the full window
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setSize({ width: el.clientWidth, height: el.clientHeight });
    });
    ro.observe(el);
    setSize({ width: el.clientWidth, height: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  const decorated = useMemo(() => decorateGraph(graph), [graph]);

  // Auto-fit on new graph
  useEffect(() => {
    if (!graph) return;
    const t = window.setTimeout(() => fgRef.current?.zoomToFit(400, 60), 250);
    return () => window.clearTimeout(t);
  }, [graph]);

  const paintNode = useCallback(
    (raw: object, ctx: CanvasRenderingContext2D, scale: number) => {
      const n = raw as DecoratedNode & { x?: number; y?: number };
      if (n.x === undefined || n.y === undefined) return;
      const r = 2 + Math.sqrt(n.degree) * 1.6;
      const isHover  = hoverId === n.id;
      const isOrphan = n.group === '_orphan';

      if (isHover || n.degree >= 6) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 6, 0, 2 * Math.PI);
        ctx.fillStyle = VAULT_GLOW;
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = isOrphan ? 'rgba(255,255,255,0.35)' : '#ffffff';
      ctx.fill();

      if (isHover || scale > 1.6) {
        const fontSize = Math.max(10 / scale, 3);
        ctx.font = `${fontSize}px 'IBM Plex Mono', ui-monospace, monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = isHover ? VAULT_ACCENT : 'rgba(255,255,255,0.75)';
        ctx.fillText(n.id, n.x, n.y + r + 2);
      }
    },
    [hoverId],
  );

  const statusLabel: Record<typeof state, string> = {
    connecting: 'CONNECTING',
    open:       'LIVE',
    closed:     'OFFLINE',
    error:      'ERROR',
  };
  const statusColor =
    state === 'open'  ? VAULT_ACCENT
    : state === 'error' ? '#ff2d55'
    : 'rgba(255,255,255,0.55)';

  return (
    <div
      ref={containerRef}
      className="flex-1 relative overflow-hidden"
      style={{ background: 'rgba(2,5,11,0.88)', fontFamily: "'IBM Plex Mono', ui-monospace, monospace" }}
    >
      {/* Header */}
      <div style={{
        position: 'absolute', top: 12, left: 16, zIndex: 10,
        padding: '5px 12px',
        border: `1px solid ${VAULT_ACCENT}`,
        background: 'rgba(2,5,11,0.75)',
        fontSize: 10, fontWeight: 700, letterSpacing: '0.3em',
        color: VAULT_ACCENT,
        textShadow: `0 0 8px ${VAULT_GLOW}`,
        pointerEvents: 'none',
      }}>
        ◆ BRAIN HUB · VAULT GRAPH
      </div>

      {/* Status */}
      <div style={{
        position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 10,
        padding: '4px 10px',
        border: `1px solid ${statusColor}`,
        background: 'rgba(2,5,11,0.75)',
        fontSize: 9, letterSpacing: '0.3em',
        color: statusColor,
        pointerEvents: 'none',
      }}>
        ● {statusLabel[state]}
        {graph?.stats ? ` · ${graph.stats.files} NOTES · ${graph.stats.links} LINKS` : ''}
        {error ? ` · ${error}` : ''}
      </div>

      {/* Hint */}
      <div style={{
        position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 10,
        padding: '4px 10px',
        border: '1px solid rgba(255,255,255,0.18)',
        background: 'rgba(2,5,11,0.7)',
        fontSize: 9, letterSpacing: '0.25em',
        color: 'rgba(255,255,255,0.45)',
        pointerEvents: 'none',
      }}>
        DRAG · SCROLL TO ZOOM · HOVER NODE
      </div>

      {/* Graph */}
      {size.width > 0 && size.height > 0 && (
        <ForceGraph2D
          ref={fgRef}
          width={size.width}
          height={size.height}
          backgroundColor={BG}
          graphData={decorated}
          nodeRelSize={4}
          linkColor={() => 'rgba(168,85,247,0.25)'}
          linkWidth={0.6}
          linkDirectionalParticles={0}
          cooldownTicks={120}
          warmupTicks={40}
          d3AlphaDecay={0.025}
          d3VelocityDecay={0.35}
          onNodeHover={(n) => setHoverId(n ? (n as VaultGraphNode).id : null)}
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={(raw, color, ctx) => {
            const n = raw as DecoratedNode & { x?: number; y?: number };
            if (n.x === undefined || n.y === undefined) return;
            const r = 2 + Math.sqrt(n.degree) * 1.6;
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 4, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
        />
      )}

      {/* Empty state */}
      {state === 'open' && graph && graph.nodes.length === 0 && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          pointerEvents: 'none',
          color: 'rgba(255,255,255,0.4)', fontSize: 11, letterSpacing: '0.25em',
        }}>
          VAULT EMPTY · ADD .md FILES TO YOUR OBSIDIAN VAULT
        </div>
      )}

      {/* Offline state */}
      {state !== 'open' && !graph && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          pointerEvents: 'none',
          color: 'rgba(255,255,255,0.4)', fontSize: 11, letterSpacing: '0.25em',
        }}>
          {state === 'connecting'
            ? 'CONNECTING TO VAULT…'
            : 'VAULT OFFLINE · START vault_graph SERVICE ON :8083'}
        </div>
      )}
    </div>
  );
}

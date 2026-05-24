import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import {
  useVaultGraph,
  type VaultGraphData,
  type VaultGraphNode,
} from './useVaultGraph';

/** Subset minimal de l'API imperative de ForceGraph2D dont on a besoin. */
interface ForceGraphHandle {
  zoomToFit(ms?: number, padding?: number): void;
}

/**
 * Nexus9 — VaultGraphOverlay
 *
 * Overlay plein ecran qui visualise le vault Obsidian comme un graphe.
 *
 * - Connecte au sidecar `services/vault_graph/` via WebSocket (ws://localhost:8083).
 * - ForceGraph2D : noeuds blancs (taille proportionnelle aux connexions),
 *   liens semi-transparents, halo sur hover.
 * - Fond #0a0a0f, accent VAULT #a855f7.
 * - Fermeture : bouton X (top-right) ou ESC.
 * - Animation fade-in via CSS keyframe injecte sur le bloc.
 */

interface VaultGraphOverlayProps {
  open: boolean;
  onClose: () => void;
}

// --- Helpers de mesure des dimensions plein ecran -----------------

function useFullscreenSize() {
  const [size, setSize] = useState({ width: 0, height: 0 });
  useEffect(() => {
    const measure = () =>
      setSize({ width: window.innerWidth, height: window.innerHeight });
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);
  return size;
}

// --- Pre-calcul du degre (taille des noeuds) ----------------------

interface DecoratedNode extends VaultGraphNode {
  /** Nombre de liens entrants+sortants. */
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

// --- Overlay ------------------------------------------------------

const VAULT_ACCENT = '#a855f7';
const VAULT_GLOW   = 'rgba(168, 85, 247, 0.55)';
const BG           = '#0a0a0f';

export function VaultGraphOverlay({ open, onClose }: VaultGraphOverlayProps) {
  const { graph, state, error } = useVaultGraph({ enabled: open });
  const { width, height } = useFullscreenSize();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);

  // Decoration calculee une seule fois par snapshot.
  const decorated = useMemo(() => decorateGraph(graph), [graph]);

  // ESC -> close
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Reset zoom quand on (re)ouvre.
  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => fgRef.current?.zoomToFit(400, 60), 250);
    return () => window.clearTimeout(t);
  }, [open, graph]);

  const paintNode = useCallback(
    (raw: object, ctx: CanvasRenderingContext2D, scale: number) => {
      const n = raw as DecoratedNode & { x?: number; y?: number };
      if (n.x === undefined || n.y === undefined) return;
      const r = 2 + Math.sqrt(n.degree) * 1.6;
      const isHover = hoverId === n.id;
      const isOrphan = n.group === '_orphan';

      // Halo (hover ou degre eleve).
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

      // Label : on n'affiche qu'au zoom proche ou sur hover, pour eviter le bruit.
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

  if (!open) return null;

  const statusLabel: Record<typeof state, string> = {
    connecting: 'CONNECTING',
    open: 'LIVE',
    closed: 'OFFLINE',
    error: 'ERROR',
  };

  const statusColor =
    state === 'open' ? VAULT_ACCENT : state === 'error' ? '#ff2d55' : 'rgba(255,255,255,0.55)';

  return (
    <>
      <style>{`
        @keyframes nexus9-vaultgraph-fade-in {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
      `}</style>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Vault graph"
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 1000,
          background: BG,
          animation: 'nexus9-vaultgraph-fade-in 220ms ease-out both',
          fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
          color: '#e5e7eb',
        }}
      >
        {/* Header gauche : titre */}
        <div
          style={{
            position: 'absolute',
            top: 16,
            left: 16,
            padding: '6px 12px',
            border: `1px solid ${VAULT_ACCENT}`,
            background: 'rgba(2,5,11,0.7)',
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.3em',
            color: VAULT_ACCENT,
            textShadow: `0 0 8px ${VAULT_GLOW}`,
            pointerEvents: 'none',
          }}
        >
          ◆ VAULT · GRAPH SYNC
        </div>

        {/* Status (live/offline) */}
        <div
          style={{
            position: 'absolute',
            top: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            padding: '4px 10px',
            border: `1px solid ${statusColor}`,
            background: 'rgba(2,5,11,0.7)',
            fontSize: 9,
            letterSpacing: '0.3em',
            color: statusColor,
            pointerEvents: 'none',
          }}
        >
          ● {statusLabel[state]}
          {graph?.stats ? ` · ${graph.stats.files} NOTES · ${graph.stats.links} LINKS` : ''}
          {error ? ` · ${error}` : ''}
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          aria-label="Close vault graph"
          style={{
            position: 'absolute',
            top: 12,
            right: 12,
            width: 32,
            height: 32,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid rgba(255,255,255,0.35)',
            background: 'rgba(2,5,11,0.7)',
            color: '#e5e7eb',
            cursor: 'pointer',
            fontFamily: 'inherit',
            fontSize: 14,
            lineHeight: 1,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = VAULT_ACCENT;
            e.currentTarget.style.color = VAULT_ACCENT;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.35)';
            e.currentTarget.style.color = '#e5e7eb';
          }}
        >
          ×
        </button>

        {/* Hint */}
        <div
          style={{
            position: 'absolute',
            bottom: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            padding: '4px 10px',
            border: '1px solid rgba(255,255,255,0.20)',
            background: 'rgba(2,5,11,0.7)',
            fontSize: 9,
            letterSpacing: '0.25em',
            color: 'rgba(255,255,255,0.55)',
            pointerEvents: 'none',
          }}
        >
          DRAG · SCROLL · HOVER · ESC TO CLOSE
        </div>

        {/* Graph */}
        {width > 0 && height > 0 && (
          <ForceGraph2D
            ref={fgRef}
            width={width}
            height={height}
            backgroundColor={BG}
            graphData={decorated}
            nodeRelSize={4}
            linkColor={() => 'rgba(168, 85, 247, 0.25)'}
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
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              pointerEvents: 'none',
              color: 'rgba(255,255,255,0.45)',
              fontSize: 11,
              letterSpacing: '0.25em',
            }}
          >
            VAULT EMPTY · ADD .md FILES TO {`{VAULT_PATH}`}
          </div>
        )}

        {state !== 'open' && !graph && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              pointerEvents: 'none',
              color: 'rgba(255,255,255,0.45)',
              fontSize: 11,
              letterSpacing: '0.25em',
            }}
          >
            {state === 'connecting' ? 'CONNECTING TO VAULT…' : 'VAULT OFFLINE · START vault_graph SERVICE'}
          </div>
        )}
      </div>
    </>
  );
}
        
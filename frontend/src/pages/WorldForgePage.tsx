/**
 * Nexus9 — World · Forge.
 *
 * 3-column layout pinned to the central HUD panel:
 *   ┌────────────┬──────────────────────────┬────────────┐
 *   │ LEFT DOCK  │   FORGE LABS image       │ RIGHT DOCK │
 *   │  ▦ cards   │   (cinematic + subtle    │  ▦ cards   │
 *   │            │    sci-fi overlays)      │            │
 *   └────────────┴──────────────────────────┴────────────┘
 *   └────────  ADD CARD bar (minimized by default)  ────┘
 *
 * Cards are added via the bottom bar, dock to left or right border, are
 * vertically resizable by dragging their bottom edge, and can flip
 * between docks via the ↔ button. Layout is persisted to localStorage so
 * the user finds the same setup on reload.
 *
 * The source image is never modified — only low-opacity CSS overlays are
 * drawn on top: CRT scan lines, vignette breath, slow sweep band.
 */
import { useEffect, useState } from 'react';
import type { ComponentType } from 'react';
import {
  ChevronUp, ChevronDown, X, Plus,
  Activity, GitBranch, FlaskConical, Settings,
  Sparkles, Box, Printer,
  ArrowLeft, ArrowRight,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import { ForgePipelinesCard } from '../components/CommandCenter/ForgePipelinesCard';
import { NamedSatellite, LiveSatellite } from '../components/CommandCenter/FunctionalSatellites';
import { CardAccentContext } from '../components/CommandCenter/HudCard';

// Re-themed satellite cards
const PipelineMonitorForge = () => <NamedSatellite title="PIPELINE MONITOR" colorKey="forge" />;
const TestDroneForge       = () => <NamedSatellite title="TEST DRONE"        colorKey="forge" />;
const OptimizerDroneForge  = () => <NamedSatellite title="OPTIMIZER DRONE"   colorKey="forge" />;
const MeshyCredits         = () => <NamedSatellite title="MESHY CREDITS"     colorKey="forge" />;
const StlOutput            = () => <LiveSatellite  title="STL OUTPUT"        colorKey="forge" snapshotKey="stl_output" />;
const BambuQueue           = () => <NamedSatellite title="BAMBU QUEUE"       colorKey="forge" />;

// ── Constants ───────────────────────────────────────────────────────────────

const CANDIDATES = ['/world/forge.jpg', '/world/forge.png', '/world/forge.webp'];
const STORAGE_KEY = 'nexus9.world-forge.layout';
const DOCK_WIDTH  = 260;
const MIN_CARD_H  = 160;
const DEFAULT_CARD_H = 240;

type CardType = 'pulse' | 'pipelinemon' | 'testdrone' | 'optimizerdrone' | 'meshy' | 'stl' | 'bambu';
type Side     = 'left' | 'right';

interface CardDef {
  label: string;
  sub:   string;
  icon:  LucideIcon;
  Card:  ComponentType;
}

const CARD_REGISTRY: Record<CardType, CardDef> = {
  pulse:          { label: 'PULSE',            sub: 'Pipeline Monitor',            icon: Activity,      Card: ForgePipelinesCard    },
  pipelinemon:    { label: 'PIPELINE MONITOR', sub: 'Real-time pipeline status',   icon: GitBranch,     Card: PipelineMonitorForge  },
  testdrone:      { label: 'TEST DRONE',       sub: 'Automated STL / code checks', icon: FlaskConical,  Card: TestDroneForge        },
  optimizerdrone: { label: 'OPTIMIZER DRONE',  sub: 'STL orientation / params',    icon: Settings,      Card: OptimizerDroneForge   },
  meshy:          { label: 'MESHY CREDITS',    sub: 'API quota left',              icon: Sparkles,      Card: MeshyCredits          },
  stl:            { label: 'STL OUTPUT',       sub: 'Recent STL exports',          icon: Box,           Card: StlOutput             },
  bambu:          { label: 'BAMBU QUEUE',      sub: 'Bambu Lab printer state',     icon: Printer,       Card: BambuQueue            },
};

interface PlacedCard {
  id:     string;
  type:   CardType;
  side:   Side;
  height: number;
}

const uid = () => Math.random().toString(36).slice(2, 10);

const isPlacedCard = (v: unknown): v is PlacedCard =>
  !!v &&
  typeof v === 'object' &&
  typeof (v as PlacedCard).id === 'string' &&
  (v as PlacedCard).type in CARD_REGISTRY &&
  ((v as PlacedCard).side === 'left' || (v as PlacedCard).side === 'right') &&
  typeof (v as PlacedCard).height === 'number';

const loadCards = (): PlacedCard[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter(isPlacedCard) : [];
  } catch {
    return [];
  }
};

// ── Page component ──────────────────────────────────────────────────────────

export function WorldForgePage() {
  const [idx, setIdx] = useState(0);
  const [allFailed, setAllFailed] = useState(false);
  const [placedCards, setPlacedCards] = useState<PlacedCard[]>(loadCards);

  // Persist layout on every change
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(placedCards)); }
    catch { /* quota / private mode — silently ignore */ }
  }, [placedCards]);

  const handleImgError = () => {
    if (idx + 1 < CANDIDATES.length) setIdx(idx + 1);
    else setAllFailed(true);
  };

  const handleAdd = (type: CardType) => {
    const leftCount  = placedCards.filter((c) => c.side === 'left').length;
    const rightCount = placedCards.filter((c) => c.side === 'right').length;
    const side: Side = leftCount <= rightCount ? 'left' : 'right';
    setPlacedCards((cards) => [
      ...cards,
      { id: uid(), type, side, height: DEFAULT_CARD_H },
    ]);
  };

  const handleResize = (id: string, height: number) =>
    setPlacedCards((cards) =>
      cards.map((c) => (c.id === id ? { ...c, height } : c)),
    );

  const handleClose = (id: string) =>
    setPlacedCards((cards) => cards.filter((c) => c.id !== id));

  const handleFlip = (id: string) =>
    setPlacedCards((cards) =>
      cards.map((c) => (c.id === id ? { ...c, side: c.side === 'left' ? 'right' : 'left' } : c)),
    );

  const leftCards  = placedCards.filter((c) => c.side === 'left');
  const rightCards = placedCards.filter((c) => c.side === 'right');

  return (
    <CardAccentContext.Provider value="forge">
    <div
      className="flex-1 flex flex-col overflow-hidden"
      style={{ background: 'var(--hud-bg)' }}
    >
      {/* Top 3-column area */}
      <div className="flex-1 flex flex-row min-h-0">
        {!allFailed ? (
          <>
            <Dock
              side="left"
              cards={leftCards}
              onResize={handleResize}
              onClose={handleClose}
              onFlip={handleFlip}
            />

            <ImageArea
              src={CANDIDATES[idx]}
              onError={handleImgError}
            />

            <Dock
              side="right"
              cards={rightCards}
              onResize={handleResize}
              onClose={handleClose}
              onFlip={handleFlip}
            />
          </>
        ) : (
          <NotFoundOverlay />
        )}
      </div>

      {/* Bottom card-adder bar (pushes layout) */}
      <CardAdderBar onAdd={handleAdd} placedCount={placedCards.length} />
    </div>
    </CardAccentContext.Provider>
  );
}

// ── Image area (center column with low sci-fi overlays) ─────────────────────

function ImageArea({ src, onError }: { src: string; onError: () => void }) {
  return (
    <div
      className="flex-1 relative overflow-hidden flex items-center justify-center"
      style={{ background: 'var(--hud-bg)' }}
    >
      {/* Main image — fills the column edge-to-edge with `cover` so it
          reaches the docks on both sides (no empty gap). */}
      <img
        src={src}
        alt="Forge Labs — Engineering & Production"
        onError={onError}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: 'center',
          display: 'block',
        }}
      />

      {/* Low-amplitude CRT scan lines (static pattern, very faint) */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(255,138,0,0.022) 3px, rgba(255,138,0,0.022) 4px)',
          pointerEvents: 'none',
          mixBlendMode: 'overlay',
        }}
      />

      {/* Vignette breath — corners darken/lighten slowly */}
      <div className="forge-vignette" aria-hidden="true" />

      {/* Scoped CSS — kept low-amplitude */}
      <style>{`
        @keyframes forge-vignette {
          0%, 100% { box-shadow: inset 0 0 90px -10px rgba(0,0,0,0.55); }
          50%       { box-shadow: inset 0 0 130px -4px rgba(0,0,0,0.7);  }
        }
        .forge-vignette {
          position: absolute;
          inset: 0;
          pointer-events: none;
          animation: forge-vignette 11s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

// ── Dock (left or right) ────────────────────────────────────────────────────

interface DockProps {
  side:     Side;
  cards:    PlacedCard[];
  onResize: (id: string, height: number) => void;
  onClose:  (id: string) => void;
  onFlip:   (id: string) => void;
}

function Dock({ side, cards, onResize, onClose, onFlip }: DockProps) {
  return (
    <div
      style={{
        width: DOCK_WIDTH,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        padding: 8,
        overflowY: 'auto',
        background: 'rgba(2,4,12,0.55)',
        borderLeft:  side === 'right' ? '1px solid var(--hud-border)' : 'none',
        borderRight: side === 'left'  ? '1px solid var(--hud-border)' : 'none',
      }}
    >
      {cards.length === 0 ? (
        <div
          className="text-[9px] tracking-[0.25em] text-center"
          style={{ color: 'var(--hud-text-dim)', opacity: 0.5, padding: '20px 8px' }}
        >
          — EMPTY · ADD CARD BELOW —
        </div>
      ) : (
        cards.map((card) => (
          <DockedCard
            key={card.id}
            card={card}
            def={CARD_REGISTRY[card.type]}
            onResize={onResize}
            onClose={() => onClose(card.id)}
            onFlip={() => onFlip(card.id)}
          />
        ))
      )}
    </div>
  );
}

// ── Docked card (height-resizable, flipable) ────────────────────────────────

interface DockedCardProps {
  card:     PlacedCard;
  def:      CardDef;
  onResize: (id: string, height: number) => void;
  onClose:  () => void;
  onFlip:   () => void;
}

function DockedCard({ card, def, onResize, onClose, onFlip }: DockedCardProps) {
  const Body = def.Card;
  const [resizingNow, setResizingNow] = useState(false);

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    setResizingNow(true);
    const startY = e.clientY;
    const origH  = card.height;
    const move = (ev: MouseEvent) => {
      const h = Math.max(MIN_CARD_H, origH + (ev.clientY - startY));
      onResize(card.id, h);
    };
    const up = () => {
      setResizingNow(false);
      document.removeEventListener('mousemove', move);
      document.removeEventListener('mouseup', up);
    };
    document.addEventListener('mousemove', move);
    document.addEventListener('mouseup', up);
  };

  const FlipIcon = card.side === 'left' ? ArrowRight : ArrowLeft;

  return (
    <div
      style={{
        height: card.height,
        flexShrink: 0,
        position: 'relative',
        background: 'var(--hud-bg-elev)',
        border: '1px solid var(--color-forge)',
        borderTop: '2px solid var(--color-forge)',
        boxShadow: '0 0 18px -8px rgba(255,138,0,0.4)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
      {/* Header */}
      <div
        style={{
          height: 22,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '0 8px',
          borderBottom: '1px solid var(--hud-border)',
          background: 'rgba(0,0,0,0.35)',
          userSelect: 'none',
        }}
      >
        <span className="text-[9px] font-bold tracking-[0.2em]" style={{ color: 'var(--color-forge)' }}>
          ◆ {def.label}
        </span>
        <span className="text-[8px] tracking-wider truncate" style={{ color: 'var(--hud-text-dim)', flex: 1 }}>
          {def.sub}
        </span>
        <button
          onClick={onFlip}
          aria-label={`Flip to ${card.side === 'left' ? 'right' : 'left'} dock`}
          title={`Move to ${card.side === 'left' ? 'right' : 'left'} dock`}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--hud-text-dim)',
            padding: 2,
            cursor: 'pointer',
            display: 'inline-flex',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-forge)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
        >
          <FlipIcon size={10} />
        </button>
        <button
          onClick={onClose}
          aria-label="Close card"
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--hud-text-dim)',
            padding: 2,
            cursor: 'pointer',
            display: 'inline-flex',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-cyberdeck)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
        >
          <X size={10} />
        </button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflow: 'auto', padding: 4, minHeight: 0 }}>
        <Body />
      </div>

      {/* Resize handle (bottom edge) */}
      <div
        onMouseDown={startResize}
        title="Drag to resize height"
        style={{
          position: 'absolute',
          left: 0, right: 0, bottom: 0,
          height: 6,
          cursor: 'ns-resize',
          background: resizingNow ? 'rgba(255,138,0,0.4)' : 'transparent',
          transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => {
          if (!resizingNow) e.currentTarget.style.background = 'rgba(255,138,0,0.2)';
        }}
        onMouseLeave={(e) => {
          if (!resizingNow) e.currentTarget.style.background = 'transparent';
        }}
      />
    </div>
  );
}

// ── Bottom bar (always minimized at mount) ──────────────────────────────────

function CardAdderBar({
  onAdd, placedCount,
}: { onAdd: (type: CardType) => void; placedCount: number }) {
  const [open, setOpen] = useState(false);

  return (
    <div
      style={{
        flexShrink: 0,
        background: 'rgba(2,4,12,0.88)',
        backdropFilter: 'blur(8px)',
        borderTop: '1px solid var(--color-forge)',
        boxShadow: '0 -8px 24px -8px rgba(255,138,0,0.3)',
        transition: 'max-height 0.25s ease',
        maxHeight: open ? 120 : 32,
        overflow: 'hidden',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? 'Minimize card menu' : 'Open card menu'}
        style={{
          width: '100%',
          height: 32,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '0 14px',
          background: 'transparent',
          border: 'none',
          color: 'var(--color-forge)',
          cursor: 'pointer',
          fontFamily: 'inherit',
        }}
      >
        <Plus size={12} />
        <span className="text-[10px] font-bold tracking-[0.3em]">ADD CARD</span>
        <span className="text-[9px] tracking-wider" style={{ color: 'var(--hud-text-dim)' }}>
          {open
            ? 'click to minimize'
            : `auto-docks to side with fewer cards${placedCount ? ` · ${placedCount} placed` : ''}`}
        </span>
        <span style={{ marginLeft: 'auto', display: 'inline-flex' }}>
          {open ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </span>
      </button>

      <div style={{ padding: '0 14px 12px 14px', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {(Object.entries(CARD_REGISTRY) as [CardType, CardDef][]).map(([type, def]) => {
          const Icon = def.icon;
          return (
            <button
              key={type}
              onClick={() => onAdd(type)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 12px',
                background: 'rgba(255,138,0,0.05)',
                border: '1px solid var(--color-forge)',
                color: 'var(--color-forge)',
                fontFamily: 'inherit',
                fontSize: 10,
                letterSpacing: '0.18em',
                cursor: 'pointer',
                transition: 'background 0.15s, color 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-forge)';
                e.currentTarget.style.color = '#000';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,138,0,0.05)';
                e.currentTarget.style.color = 'var(--color-forge)';
              }}
            >
              <Icon size={11} />+ {def.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Not-found overlay (image asset missing) ─────────────────────────────────

function NotFoundOverlay() {
  return (
    <div
      className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-6"
      style={{
        color: 'var(--hud-text-dim)',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
      <div className="text-[10px] tracking-[0.3em] font-bold" style={{ color: 'var(--color-forge)' }}>
        ◆ FORGE IMAGE NOT FOUND
      </div>
      <div className="text-[11px] tracking-wider max-w-md">Save your image as one of:</div>
      <pre
        className="text-[10px] p-3"
        style={{
          background: 'rgba(255,138,0,0.06)',
          border: '1px solid rgba(255,138,0,0.3)',
          color: 'var(--hud-text)',
        }}
      >
{`C:\\OpenJarvisNexus\\frontend\\public\\world\\forge.jpg
C:\\OpenJarvisNexus\\frontend\\public\\world\\forge.png
C:\\OpenJarvisNexus\\frontend\\public\\world\\forge.webp`}
      </pre>
      <div className="text-[9px] tracking-wider opacity-70 max-w-md">then refresh this page</div>
    </div>
  );
}

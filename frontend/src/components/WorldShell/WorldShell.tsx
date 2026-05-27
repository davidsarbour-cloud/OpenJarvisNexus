/**
 * Nexus9 — WorldShell.
 *
 * Shared 3-column dashboard shell used by every World page (Forge,
 * Jarvis, Commerce, Vault, Cyberdeck, Docker). Each page used to
 * inline ~500 lines of nearly-identical Dock / DockedCard / ImageArea /
 * CardAdderBar / NotFoundOverlay code; this component centralises all
 * of that and parameterises only what actually differs between worlds:
 *
 *    ┌────────────┬──────────────────────────┬────────────┐
 *    │ LEFT DOCK  │   <imageAlt> image       │ RIGHT DOCK │
 *    │  ▦ cards   │   (CRT scanlines tinted  │  ▦ cards   │
 *    │            │    with the world accent)│            │
 *    └────────────┴──────────────────────────┴────────────┘
 *    └────────  ADD CARD bar (minimized by default)  ────┘
 *
 * Each world page is now a ~30-line wrapper that:
 *   - imports its own card components,
 *   - declares its CardType union (a string literal type),
 *   - hands a CARD_REGISTRY and an image candidate list to WorldShell.
 *
 * Layout (which cards live in which dock, at what height) is persisted
 * to localStorage under `storageKey`. First-visit defaults can be
 * provided through `defaultSeeds`.
 */
import { useEffect, useState } from 'react';
import type { ComponentType, ReactNode } from 'react';
import {
  ArrowLeft, ArrowRight, ChevronDown, ChevronUp, Plus, X,
  type LucideIcon,
} from 'lucide-react';
import { MODULE_COLORS, type ModuleKey } from '../../lib/colors';
import { CardAccentContext } from '../CommandCenter/HudCard';

// ── Layout constants (consistent across all worlds) ─────────────────────────

const DOCK_WIDTH       = 260;
const MIN_CARD_H       = 160;
const DEFAULT_CARD_H   = 240;

export type Side = 'left' | 'right';

export interface PlacedCard<T extends string = string> {
  id:     string;
  type:   T;
  side:   Side;
  height: number;
}

export interface CardDef {
  label: string;
  sub:   string;
  icon:  LucideIcon;
  Card:  ComponentType;
}

export interface WorldShellProps<T extends string> {
  /** Accent / palette key (drives all colors). */
  colorKey:      ModuleKey;
  /** Image candidates tried in order until one loads (webp → png → jpg). */
  imageCandidates: string[];
  /** alt= text for the hero image. */
  imageAlt:      string;
  /** localStorage key for layout persistence (each world has its own). */
  storageKey:    string;
  /** Map of available card types → their definition. */
  cardRegistry:  Record<T, CardDef>;
  /** Optional defaults seeded on first visit (no localStorage entry yet). */
  defaultSeeds?: PlacedCard<T>[];
  /** Optional human label for the not-found overlay. Defaults to colorKey. */
  worldLabel?:   string;
}

// ── Utilities ───────────────────────────────────────────────────────────────

const uid = () => Math.random().toString(36).slice(2, 10);

function hexToRgbTriplet(hex: string): string {
  const h = hex.replace('#', '');
  const n = h.length === 3
    ? h.split('').map((c) => c + c).join('')
    : h;
  const r = parseInt(n.slice(0, 2), 16);
  const g = parseInt(n.slice(2, 4), 16);
  const b = parseInt(n.slice(4, 6), 16);
  return `${r},${g},${b}`;
}

function isPlacedCard<T extends string>(
  v: unknown,
  registry: Record<T, CardDef>,
): v is PlacedCard<T> {
  if (!v || typeof v !== 'object') return false;
  const o = v as Partial<PlacedCard<T>>;
  return (
    typeof o.id === 'string' &&
    typeof o.type === 'string' && (o.type as T) in registry &&
    (o.side === 'left' || o.side === 'right') &&
    typeof o.height === 'number'
  );
}

function loadLayout<T extends string>(
  storageKey: string,
  registry: Record<T, CardDef>,
  defaults: PlacedCard<T>[] | undefined,
): PlacedCard<T>[] {
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw === null) return defaults ?? [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((v): v is PlacedCard<T> => isPlacedCard(v, registry));
  } catch {
    return defaults ?? [];
  }
}

// ── Main component ──────────────────────────────────────────────────────────

export function WorldShell<T extends string>({
  colorKey,
  imageCandidates,
  imageAlt,
  storageKey,
  cardRegistry,
  defaultSeeds,
  worldLabel,
}: WorldShellProps<T>) {
  const palette  = MODULE_COLORS[colorKey];
  const accent   = `var(--${palette.cssVar})`;
  const accentRgb = hexToRgbTriplet(palette.hex);

  const [idx, setIdx] = useState(0);
  const [allFailed, setAllFailed] = useState(false);
  const [placedCards, setPlacedCards] = useState<PlacedCard<T>[]>(
    () => loadLayout(storageKey, cardRegistry, defaultSeeds),
  );

  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify(placedCards)); }
    catch { /* quota / private mode — silently ignore */ }
  }, [placedCards, storageKey]);

  const handleImgError = () => {
    if (idx + 1 < imageCandidates.length) setIdx(idx + 1);
    else setAllFailed(true);
  };

  const handleAdd = (type: T) => {
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
    <CardAccentContext.Provider value={colorKey}>
      <div
        className="flex-1 flex flex-col overflow-hidden"
        style={{ background: 'var(--hud-bg)' }}
      >
        <div className="flex-1 flex flex-row min-h-0">
          {!allFailed ? (
            <>
              <Dock
                side="left"
                cards={leftCards}
                registry={cardRegistry}
                accent={accent}
                accentRgb={accentRgb}
                onResize={handleResize}
                onClose={handleClose}
                onFlip={handleFlip}
              />
              <ImageArea
                src={imageCandidates[idx]}
                alt={imageAlt}
                onError={handleImgError}
                colorKey={colorKey}
                accentRgb={accentRgb}
              />
              <Dock
                side="right"
                cards={rightCards}
                registry={cardRegistry}
                accent={accent}
                accentRgb={accentRgb}
                onResize={handleResize}
                onClose={handleClose}
                onFlip={handleFlip}
              />
            </>
          ) : (
            <NotFoundOverlay
              worldLabel={(worldLabel ?? palette.label).toUpperCase()}
              accent={accent}
              accentRgb={accentRgb}
              imageCandidates={imageCandidates}
            />
          )}
        </div>
        <CardAdderBar
          registry={cardRegistry}
          accent={accent}
          accentRgb={accentRgb}
          onAdd={handleAdd}
          placedCount={placedCards.length}
        />
      </div>
    </CardAccentContext.Provider>
  );
}

// ── Image area (center column with tinted CRT scanlines + vignette) ─────────

interface ImageAreaProps {
  src:       string;
  alt:       string;
  onError:   () => void;
  colorKey:  ModuleKey;
  accentRgb: string;
}

function ImageArea({ src, alt, onError, colorKey, accentRgb }: ImageAreaProps) {
  // Vignette uses a per-instance class so multiple WorldShell mounts on
  // the same page (unlikely but defensible) don't fight over the same
  // keyframes namespace.
  const vignetteClass = `world-vignette-${colorKey}`;
  return (
    <div
      className="flex-1 relative overflow-hidden flex items-center justify-center"
      style={{ background: 'var(--hud-bg)' }}
    >
      <img
        src={src}
        alt={alt}
        onError={onError}
        style={{
          position: 'absolute', inset: 0,
          width: '100%', height: '100%',
          objectFit: 'cover', objectPosition: 'center',
          display: 'block',
        }}
      />
      {/* Low-amplitude CRT scan lines tinted with the world accent */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute', inset: 0,
          background:
            `repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(${accentRgb},0.025) 3px, rgba(${accentRgb},0.025) 4px)`,
          pointerEvents: 'none',
          mixBlendMode: 'overlay',
        }}
      />
      {/* Vignette breath — corners darken/lighten on a slow 11s loop */}
      <div className={vignetteClass} aria-hidden="true" />
      <style>{`
        @keyframes ${vignetteClass}-anim {
          0%, 100% { box-shadow: inset 0 0 90px -10px rgba(0,0,0,0.55); }
          50%      { box-shadow: inset 0 0 130px -4px rgba(0,0,0,0.7);  }
        }
        .${vignetteClass} {
          position: absolute;
          inset: 0;
          pointer-events: none;
          animation: ${vignetteClass}-anim 11s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

// ── Dock (left or right column of cards) ────────────────────────────────────

interface DockProps<T extends string> {
  side:      Side;
  cards:     PlacedCard<T>[];
  registry:  Record<T, CardDef>;
  accent:    string;
  accentRgb: string;
  onResize:  (id: string, height: number) => void;
  onClose:   (id: string) => void;
  onFlip:    (id: string) => void;
}

function Dock<T extends string>({
  side, cards, registry, accent, accentRgb, onResize, onClose, onFlip,
}: DockProps<T>) {
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
            def={registry[card.type]}
            accent={accent}
            accentRgb={accentRgb}
            onResize={onResize}
            onClose={() => onClose(card.id)}
            onFlip={() => onFlip(card.id)}
          />
        ))
      )}
    </div>
  );
}

// ── Docked card (height-resizable, flipable between docks) ──────────────────

interface DockedCardProps<T extends string> {
  card:      PlacedCard<T>;
  def:       CardDef;
  accent:    string;
  accentRgb: string;
  onResize:  (id: string, height: number) => void;
  onClose:   () => void;
  onFlip:    () => void;
}

function DockedCard<T extends string>({
  card, def, accent, accentRgb, onResize, onClose, onFlip,
}: DockedCardProps<T>) {
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
        border: `1px solid ${accent}`,
        borderTop: `2px solid ${accent}`,
        boxShadow: `0 0 18px -8px rgba(${accentRgb},0.4)`,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
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
        <span className="text-[9px] font-bold tracking-[0.2em]" style={{ color: accent }}>
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
            background: 'transparent', border: 'none',
            color: 'var(--hud-text-dim)', padding: 2,
            cursor: 'pointer', display: 'inline-flex',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = accent)}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
        >
          <FlipIcon size={10} />
        </button>
        <button
          onClick={onClose}
          aria-label="Close card"
          style={{
            background: 'transparent', border: 'none',
            color: 'var(--hud-text-dim)', padding: 2,
            cursor: 'pointer', display: 'inline-flex',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-cyberdeck)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
        >
          <X size={10} />
        </button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 4, minHeight: 0 }}>
        <Body />
      </div>

      <div
        onMouseDown={startResize}
        title="Drag to resize height"
        style={{
          position: 'absolute',
          left: 0, right: 0, bottom: 0,
          height: 6,
          cursor: 'ns-resize',
          background: resizingNow ? `rgba(${accentRgb},0.4)` : 'transparent',
          transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => {
          if (!resizingNow) e.currentTarget.style.background = `rgba(${accentRgb},0.2)`;
        }}
        onMouseLeave={(e) => {
          if (!resizingNow) e.currentTarget.style.background = 'transparent';
        }}
      />
    </div>
  );
}

// ── Bottom card-adder bar ───────────────────────────────────────────────────

interface CardAdderBarProps<T extends string> {
  registry:    Record<T, CardDef>;
  accent:      string;
  accentRgb:   string;
  onAdd:       (type: T) => void;
  placedCount: number;
}

function CardAdderBar<T extends string>({
  registry, accent, accentRgb, onAdd, placedCount,
}: CardAdderBarProps<T>) {
  const [open, setOpen] = useState(false);
  return (
    <div
      style={{
        flexShrink: 0,
        background: 'rgba(2,4,12,0.88)',
        backdropFilter: 'blur(8px)',
        borderTop: `1px solid ${accent}`,
        boxShadow: `0 -8px 24px -8px rgba(${accentRgb},0.3)`,
        transition: 'max-height 0.25s ease',
        maxHeight: open ? 200 : 32,
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
          color: accent,
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
        {(Object.entries(registry) as [T, CardDef][]).map(([type, def]) => {
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
                background: `rgba(${accentRgb},0.05)`,
                border: `1px solid ${accent}`,
                color: accent,
                fontFamily: 'inherit',
                fontSize: 10,
                letterSpacing: '0.18em',
                cursor: 'pointer',
                transition: 'background 0.15s, color 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = accent;
                e.currentTarget.style.color = '#000';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = `rgba(${accentRgb},0.05)`;
                e.currentTarget.style.color = accent;
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

// ── Not-found overlay (all image candidates 404'd) ──────────────────────────

interface NotFoundOverlayProps {
  worldLabel:      string;
  accent:          string;
  accentRgb:       string;
  imageCandidates: string[];
}

function NotFoundOverlay({ worldLabel, accent, accentRgb, imageCandidates }: NotFoundOverlayProps): ReactNode {
  return (
    <div
      className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-6"
      style={{
        color: 'var(--hud-text-dim)',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
      <div className="text-[10px] tracking-[0.3em] font-bold" style={{ color: accent }}>
        ◆ {worldLabel} IMAGE NOT FOUND
      </div>
      <div className="text-[11px] tracking-wider max-w-md">Save your image as one of:</div>
      <pre
        className="text-[10px] p-3"
        style={{
          background: `rgba(${accentRgb},0.06)`,
          border: `1px solid rgba(${accentRgb},0.3)`,
          color: 'var(--hud-text)',
        }}
      >{imageCandidates.map((c) => `frontend/public${c}`).join('\n')}</pre>
      <div className="text-[9px] tracking-wider opacity-70 max-w-md">then refresh this page</div>
    </div>
  );
}

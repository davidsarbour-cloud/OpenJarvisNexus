/**
 * Nexus9 — Tactical visual polish (Phase 4 · Step 9).
 *
 * One full-screen overlay that paints, in order:
 *   1. CRT scanlines (very subtle, 2% opacity, repeating linear-gradient)
 *   2. Vignette darkening on edges
 *   3. Slow radar sweep (conic gradient, 24s loop)
 *
 * All layers are pointer-events:none so they NEVER block clicks.
 *
 * Design rules respected from the cheat sheet:
 *   - no oversaturation
 *   - no random cyberpunk clutter
 *   - subtle, professional command-bridge feel
 *
 * Mount ONCE near the root (HudLayout). To disable, pass enabled={false}.
 */
import { memo } from 'react';

interface TacticalOverlayProps {
  /** Master switch (default true). */
  enabled?: boolean;
  /** Disable the rotating radar sweep (e.g. on the orbital page where the
   *  3D scene already has its own motion). Default false. */
  radar?: boolean;
}

function TacticalOverlayImpl({ enabled = true, radar = true }: TacticalOverlayProps) {
  if (!enabled) return null;

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-40 overflow-hidden"
      style={{ contain: 'strict' }}
    >
      {/* 1. Scanlines */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            'repeating-linear-gradient(0deg, rgba(255,255,255,0.025) 0 1px, transparent 1px 3px)',
          mixBlendMode: 'overlay',
        }}
      />

      {/* 2. Vignette */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55) 100%)',
        }}
      />

      {/* 3. Radar sweep — slow, dim, single rotating wedge */}
      {radar && (
        <div
          className="absolute"
          style={{
            top: '-50%',
            left: '-50%',
            width: '200%',
            height: '200%',
            background:
              'conic-gradient(from 0deg at 50% 50%, transparent 0deg, rgba(0,212,255,0.05) 18deg, transparent 36deg, transparent 360deg)',
            animation: 'nexus-radar-sweep 24s linear infinite',
            transformOrigin: '50% 50%',
            mixBlendMode: 'screen',
          }}
        />
      )}

      {/* Keyframes injected once. */}
      <style>{`
        @keyframes nexus-radar-sweep {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export const TacticalOverlay = memo(TacticalOverlayImpl);

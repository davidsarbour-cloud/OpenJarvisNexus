import { Suspense } from 'react';
import { OrbitalScene } from '../components/Orbital/OrbitalScene';

/**
 * OrbitalPage — route `/orbital`.
 * Full-bleed Three.js solar system with JARVIS at the center, planets in
 * orbit and spaceship agents flying Lissajous curves. Click a body to
 * open its module panel.
 */
export function OrbitalPage() {
  return (
    <div className="flex-1 relative overflow-hidden" style={{ background: '#020509' }}>
      <Suspense
        fallback={
          <div
            className="absolute inset-0 flex items-center justify-center text-[11px] tracking-[0.25em]"
            style={{ color: 'var(--hud-text-dim)' }}
          >
            initialising orbital scene…
          </div>
        }
      >
        <OrbitalScene />
      </Suspense>

      {/* Top-left HUD label */}
      <div
        className="absolute top-3 left-3 px-3 py-1.5 text-[9px] font-bold tracking-[0.3em] pointer-events-none"
        style={{
          color: 'var(--color-jarvis)',
          background: 'rgba(2,5,11,0.7)',
          border: '1px solid var(--hud-border)',
          textShadow: '0 0 8px var(--color-jarvis-glow)',
        }}
      >
        ◆ NEXUS9 · ORBITAL VIEW
      </div>

      {/* Hint */}
      <div
        className="absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1.5 text-[9px] tracking-[0.25em] pointer-events-none"
        style={{
          color: 'var(--hud-text-dim)',
          background: 'rgba(2,5,11,0.7)',
          border: '1px solid var(--hud-border)',
        }}
      >
        DRAG · SCROLL ZOOM · CLICK A PLANET → ITS WORLD
      </div>
    </div>
  );
}

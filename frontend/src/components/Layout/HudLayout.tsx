import { Outlet, useLocation } from 'react-router';
import { TopBar } from './TopBar';
import { HudSidebar } from './HudSidebar';
import { RightPanel } from './RightPanel';
import { BottomPanel } from './BottomPanel';
import { AlertBanner, useAlertGc } from '../../systems/alerts';
import { TacticalOverlay } from '../../systems/TacticalOverlay';

/**
 * HudLayout — tactical 5-zone command bridge layout.
 *
 *   ┌──────────────────────────────────────────────────┐
 *   │                   TopBar                          │
 *   ├────────┬───────────────────────────────┬────────┤
 *   │        │                                │        │
 *   │ Hud    │          <Outlet />            │ Right  │
 *   │ Side   │   (CommandCenter / Orbital)    │ Panel  │
 *   │        │                                │        │
 *   ├────────┴───────────────────────────────┴────────┤
 *   │                  BottomPanel                      │
 *   └──────────────────────────────────────────────────┘
 *
 * Used for the two main routes only:
 *   /         → CommandCenterPage
 *   /orbital  → OrbitalPage
 *
 * Sub-pages (chat, agents, settings, ...) keep the legacy `Layout`.
 */
export function HudLayout() {
  const location = useLocation();
  const isOrbital = location.pathname.startsWith('/orbital');
  useAlertGc(); // prune acknowledged alerts > 5min, once per HUD mount

  return (
    <div
      className="flex flex-col h-full w-full overflow-hidden"
      style={{
        background: 'var(--hud-bg)',
        color: 'var(--hud-text)',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
        backgroundImage: [
          'linear-gradient(var(--hud-grid) 1px, transparent 1px)',
          'linear-gradient(90deg, var(--hud-grid) 1px, transparent 1px)',
        ].join(','),
        backgroundSize: '32px 32px, 32px 32px',
      }}
    >
      <AlertBanner />
      <TopBar />

      <div className="flex flex-1 min-h-0 relative">
        {/* Left sidebar — hidden on the orbital view to maximise canvas */}
        {!isOrbital && <HudSidebar />}

        {/* Central viewport */}
        <main
          className="flex-1 flex flex-col min-w-0 min-h-0 relative overflow-hidden"
          style={{
            borderLeft: !isOrbital ? '1px solid var(--hud-border)' : 'none',
            borderRight: !isOrbital ? '1px solid var(--hud-border)' : 'none',
          }}
        >
          <Outlet />
        </main>

        {/* Right panel — alerts + events. Hidden on orbital. */}
        {!isOrbital && <RightPanel />}
      </div>

      {/* Bottom strip — graphs / quick stats. Hidden on orbital. */}
      {!isOrbital && <BottomPanel />}

      {/* Tactical polish — scanlines + vignette + radar sweep.
          Radar disabled on /orbital (3D scene already provides motion). */}
      <TacticalOverlay radar={!isOrbital} />
    </div>
  );
}

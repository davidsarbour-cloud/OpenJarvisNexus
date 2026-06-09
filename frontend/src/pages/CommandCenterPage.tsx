import { useState } from 'react';
import { ScheduledTasksCard } from '../components/CommandCenter/ScheduledTasksCard';
import { UptimeCard } from '../components/CommandCenter/UptimeCard';
import { HealthShortcutCard, BenchmarkShortcutCard } from '../components/CommandCenter/HealthBenchCards';
import { DailyReportCard } from '../components/CommandCenter/DailyReportCard';
import { RevenueCard } from '../components/CommandCenter/RevenueCard';
import { GumroadRevenueCard } from '../components/CommandCenter/GumroadRevenueCard';
import { YouTubeStatsCard } from '../components/CommandCenter/YouTubeStatsCard';
import { HueForgeCard } from '../components/CommandCenter/HueForgeCard';

/**
 * CommandCenterPage — route `/`.
 *
 * Mirrors the /world/<name> shell: a 3-column layout with the NEXUS9 bridge
 * image filling the center column edge-to-edge (objectFit cover, touching
 * both docks) and docks pinned left/right.
 *   ┌────────────┬──────────────────────────┬────────────┐
 *   │ AUTOMATION │   NEXUS9 bridge image    │  RESERVED  │
 *   │ scheduled  │   (CRT scanlines + slow  │  (empty    │
 *   │  tasks     │    vignette breath)      │   for now) │
 *   └────────────┴──────────────────────────┴────────────┘
 */
const IMAGE_SRC = '/world/command-center.png';
const DOCK_WIDTH = 300;

export function CommandCenterPage() {
  const [imgFailed, setImgFailed] = useState(false);

  return (
    <div
      className="flex-1 flex flex-row overflow-hidden min-h-0"
      style={{ background: 'var(--hud-bg)' }}
    >
      {/* LEFT — automation schedule */}
      <div
        style={{
          width: DOCK_WIDTH,
          flexShrink: 0,
          overflowY: 'auto',
          padding: 10,
          background: 'rgba(2,4,12,0.55)',
          borderRight: '1px solid var(--hud-border)',
        }}
      >
        <ScheduledTasksCard buckets={['daily']} title="Daily Schedule" />
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <DailyReportCard />
          <RevenueCard />
          <GumroadRevenueCard />
          <YouTubeStatsCard />
          <HueForgeCard />
        </div>
      </div>

      {/* CENTER — NEXUS9 bridge image, edge-to-edge */}
      {imgFailed ? <NotFoundOverlay /> : <ImageArea onError={() => setImgFailed(true)} />}

      {/* RIGHT — weekly + monthly schedule */}
      <div
        style={{
          width: DOCK_WIDTH,
          flexShrink: 0,
          overflowY: 'auto',
          padding: 10,
          background: 'rgba(2,4,12,0.55)',
          borderLeft: '1px solid var(--hud-border)',
        }}
      >
        <ScheduledTasksCard buckets={['weekly', 'monthly']} title="Weekly + Monthly" columns={1} />
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <UptimeCard />
          <HealthShortcutCard />
          <BenchmarkShortcutCard />
        </div>
      </div>
    </div>
  );
}

// ── Image area (center column, edge-to-edge with subtle sci-fi overlays) ────

function ImageArea({ onError }: { onError: () => void }) {
  return (
    <div
      className="flex-1 relative overflow-hidden flex items-center justify-center"
      style={{ background: 'var(--hud-bg)' }}
    >
      {/* Main image — `cover` so it reaches both docks (no empty gap). */}
      <img
        src={IMAGE_SRC}
        alt="NEXUS9 Bridge — Command Center"
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

      {/* CRT scan lines — cyan tint, very faint */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(0,212,255,0.025) 3px, rgba(0,212,255,0.025) 4px)',
          pointerEvents: 'none',
          mixBlendMode: 'overlay',
        }}
      />

      {/* Slow sweep band — accent-tinted scan drifting top→bottom every 24s */}
      <div className="cc-sweep" aria-hidden="true" />

      {/* Vignette breath */}
      <div className="cc-vignette" aria-hidden="true" />

      <style>{`
        @keyframes cc-sweep {
          0%   { transform: translateY(-80px); opacity: 0; }
          8%   { opacity: 0.9; }
          92%  { opacity: 0.9; }
          100% { transform: translateY(100vh); opacity: 0; }
        }
        .cc-sweep {
          position: absolute;
          top: 0; left: 0; right: 0;
          height: 80px;
          background: linear-gradient(to bottom, transparent, rgba(0,212,255,0.14), transparent);
          pointer-events: none;
          mix-blend-mode: screen;
          animation: cc-sweep 24s linear infinite;
        }
        @keyframes cc-vignette {
          0%, 100% { box-shadow: inset 0 0 90px -10px rgba(0,0,0,0.55); }
          50%      { box-shadow: inset 0 0 130px -4px rgba(0,0,0,0.7);  }
        }
        .cc-vignette {
          position: absolute;
          inset: 0;
          pointer-events: none;
          animation: cc-vignette 11s ease-in-out infinite;
        }
      `}</style>
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
      <div className="text-[10px] tracking-[0.3em] font-bold" style={{ color: 'var(--color-jarvis)' }}>
        ◆ COMMAND CENTER IMAGE NOT FOUND
      </div>
      <div className="text-[11px] tracking-wider max-w-md">Expected file:</div>
      <pre
        className="text-[10px] p-3"
        style={{
          background: 'rgba(0,212,255,0.06)',
          border: '1px solid rgba(0,212,255,0.3)',
          color: 'var(--hud-text)',
        }}
      >{`frontend/public${IMAGE_SRC}`}</pre>
      <div className="text-[9px] tracking-wider opacity-70 max-w-md">then refresh this page</div>
    </div>
  );
}

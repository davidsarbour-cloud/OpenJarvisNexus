/**
 * Nexus9 — WorldPage.
 *
 * Generic empty canvas for the WORLD sidebar entries (JARVIS, Forge,
 * Commerce, Cyberdeck, Vault, Docker). Reuses the Command Center
 * layout shell so cards/graphs can be dropped in later — currently the
 * page only renders the section title and an empty grid placeholder.
 *
 * One component, one route per world (`/world/<key>`), routed in App.tsx.
 */
import { cssVar, moduleColor, type ModuleKey } from '../lib/colors';

interface WorldPageProps {
  worldKey: ModuleKey;
  /** Optional override; defaults to MODULE_COLORS[worldKey].label */
  title?: string;
}

export function WorldPage({ worldKey, title }: WorldPageProps) {
  const color = moduleColor(worldKey);
  const accent = cssVar(worldKey);
  const displayTitle = (title ?? color.label).toUpperCase();

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
      <SectionTitle text={displayTitle} accent={accent} />

      <EmptyZone accent={accent} label="OVERVIEW" />
      <EmptyZone accent={accent} label="LIVE METRICS" />
      <EmptyZone accent={accent} label="ACTIVITY" />
    </div>
  );
}

function SectionTitle({ text, accent }: { text: string; accent: string }) {
  return (
    <div
      className="flex items-center gap-3 text-[10px] font-bold tracking-[0.3em]"
      style={{ color: 'var(--hud-text-dim)' }}
    >
      <span style={{ color: accent }}>◆</span>
      {text}
      <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
    </div>
  );
}

/**
 * Placeholder grid section — same column structure as CommandCenterPage's
 * card grid, but the slots are empty dashed cells. Dropping a real card
 * component into this grid (and renaming this `EmptyZone` to a custom
 * layout) is the next step when cards/graphs become available.
 */
function EmptyZone({ accent, label }: { accent: string; label: string }) {
  return (
    <section>
      <div
        className="px-1 pb-2 text-[9px] font-bold tracking-[0.25em]"
        style={{ color: 'var(--hud-text-dim)' }}
      >
        -- {label}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-10 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="aspect-[5/4] flex items-center justify-center text-[9px] tracking-[0.22em]"
            style={{
              border: `1px dashed ${accent}`,
              background: 'rgba(255,255,255,0.015)',
              color: 'var(--hud-text-dim)',
              borderRadius: 6,
            }}
          >
            slot {i + 1}
          </div>
        ))}
      </div>
    </section>
  );
}

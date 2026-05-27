import { ScheduledTasksCard } from '../components/CommandCenter/ScheduledTasksCard';

/**
 * CommandCenterPage — route `/`.
 *
 * After the Phase 7 card migration, every service card was relocated to
 * its themed `/world/<name>` room. Only AUTOMATION SCHEDULE remains here
 * (it spans all rooms — global view of every APScheduler job).
 * Navigation to worlds lives in the left sidebar (HudSidebar).
 */
export function CommandCenterPage() {
  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
      <SectionTitle text="AUTOMATION" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-10 gap-3">
        <div className="col-span-2 sm:col-span-3 lg:col-span-5 xl:col-span-6 2xl:col-span-10">
          <ScheduledTasksCard />
        </div>
      </div>
    </div>
  );
}

// ── Section title ───────────────────────────────────────────────────────────

function SectionTitle({ text }: { text: string }) {
  return (
    <div
      className="flex items-center gap-3 text-[10px] font-bold tracking-[0.3em]"
      style={{ color: 'var(--hud-text-dim)' }}
    >
      <span style={{ color: 'var(--color-jarvis)' }}>◆</span>
      {text}
      <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
    </div>
  );
}

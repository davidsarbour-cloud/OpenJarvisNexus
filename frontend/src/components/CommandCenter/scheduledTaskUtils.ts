/**
 * Pure helpers for the Automation Schedule card. Extracted from
 * ScheduledTasksCard.tsx so the file only exports the component itself
 * (react-refresh hot-reload requirement) and so urgencyFor can be unit-tested
 * without pulling in the React component tree.
 */
export type Urgency = 'idle' | 'warn' | 'alert' | 'overdue';

export function urgencyFor(deltaMs: number | null): Urgency {
  if (deltaMs === null) return 'idle';
  if (deltaMs < 0) return 'overdue';
  if (deltaMs < 10 * 60_000) return 'alert';
  if (deltaMs < 60 * 60_000) return 'warn';
  return 'idle';
}

/**
 * Pure helpers for the Brain Hub constellation view. Extracted from
 * BrainHubPage.tsx so the page file only exports the component itself
 * (react-refresh hot-reload requirement) and so topGroup can be unit-tested
 * without pulling in react-force-graph-2d.
 */

/** Couleur par dossier Obsidian (Johnny Decimal prefix). */
export const GROUP_COLORS: Record<string, string> = {
  '00_Core':            '#22d3ee', // cyan
  '01_Inbox':           '#fbbf24', // amber
  '02_Daily':           '#4ade80', // green
  '03_Projects':        '#fb923c', // orange
  '04_Areas':           '#60a5fa', // blue
  '05_Resources':       '#a78bfa', // violet
  '06_Agents':          '#f87171', // red
  '07_Schemas':         '#f472b6', // pink
  '08_Command-Center':  '#e879f9', // fuchsia
  '09_Archives':        '#94a3b8', // slate
  '_orphan':            'rgba(255,255,255,0.25)',
};

export function groupColor(group: string | undefined): string {
  if (!group) return '#ffffff';
  for (const [key, col] of Object.entries(GROUP_COLORS)) {
    if (group.startsWith(key) || group === key) return col;
  }
  return '#ffffff';
}

/**
 * Normalize a node's full group string (e.g. "03_Projects/STL") to its
 * top-level Johnny-Decimal bucket ("03_Projects") so all subfolder notes
 * cluster into the same constellation.
 */
export function topGroup(group: string | undefined): string {
  if (!group) return '_orphan';
  for (const key of Object.keys(GROUP_COLORS)) {
    if (group.startsWith(key) || group === key) return key;
  }
  return '_orphan';
}

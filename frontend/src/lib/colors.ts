/**
 * Nexus9 module identity palette.
 *
 * Each major module (planet/system) has a consistent color across:
 *   - Command Center cards (border, accents, icons)
 *   - Orbital View planets (material color, ring color)
 *   - Sidebar section indicators
 *
 * Hex values are mirrored as CSS custom properties in index.css
 * (e.g. `var(--color-forge)`).
 */

export type ModuleKey =
  | 'jarvis'
  | 'forge'
  | 'commerce'
  | 'cyberdeck'
  | 'vault'
  | 'docker'
  | 'cortex'
  | 'security'
  | 'mining';

export interface ModuleColor {
  /** Display name. */
  label: string;
  /** Primary hex (full opacity). */
  hex: string;
  /** CSS variable name (kebab-case, without the leading --). */
  cssVar: string;
  /** Tailwind-friendly rgba accent (subtle bg). */
  subtle: string;
  /** Glow for box-shadow / Three.js emissive. */
  glow: string;
}

export const MODULE_COLORS: Record<ModuleKey, ModuleColor> = {
  jarvis: {
    label: 'JARVIS Core',
    hex: '#00d4ff',
    cssVar: 'color-jarvis',
    subtle: 'rgba(0, 212, 255, 0.10)',
    glow: 'rgba(0, 212, 255, 0.45)',
  },
  forge: {
    label: 'Forge',
    hex: '#ff8a00',
    cssVar: 'color-forge',
    subtle: 'rgba(255, 138, 0, 0.10)',
    glow: 'rgba(255, 138, 0, 0.45)',
  },
  commerce: {
    label: 'Commerce',
    hex: '#00d4a8',
    cssVar: 'color-commerce',
    subtle: 'rgba(0, 212, 168, 0.10)',
    glow: 'rgba(0, 212, 168, 0.45)',
  },
  cyberdeck: {
    label: 'Cyberdeck',
    hex: '#ff2d55',
    cssVar: 'color-cyberdeck',
    subtle: 'rgba(255, 45, 85, 0.10)',
    glow: 'rgba(255, 45, 85, 0.45)',
  },
  vault: {
    label: 'Vault',
    hex: '#a855f7',
    cssVar: 'color-vault',
    subtle: 'rgba(168, 85, 247, 0.10)',
    glow: 'rgba(168, 85, 247, 0.45)',
  },
  docker: {
    label: 'Docker',
    hex: '#00ff88',
    cssVar: 'color-docker',
    subtle: 'rgba(0, 255, 136, 0.10)',
    glow: 'rgba(0, 255, 136, 0.45)',
  },
  cortex: {
    label: 'Cortex',
    hex: '#8b5cf6',
    cssVar: 'color-cortex',
    subtle: 'rgba(139, 92, 246, 0.10)',
    glow: 'rgba(139, 92, 246, 0.45)',
  },
  security: {
    label: 'Security',
    hex: '#f59e0b',
    cssVar: 'color-security',
    subtle: 'rgba(245, 158, 11, 0.10)',
    glow: 'rgba(245, 158, 11, 0.45)',
  },
  mining: {
    label: 'Mining',
    hex: '#ffd60a',
    cssVar: 'color-mining',
    subtle: 'rgba(255, 214, 10, 0.10)',
    glow: 'rgba(255, 214, 10, 0.45)',
  },
};

/** Convenience accessor. */
export const moduleColor = (key: ModuleKey): ModuleColor => MODULE_COLORS[key];

/** CSS variable form for inline styles, e.g. `color: cssVar('forge')`. */
export const cssVar = (key: ModuleKey): string => `var(--${MODULE_COLORS[key].cssVar})`;

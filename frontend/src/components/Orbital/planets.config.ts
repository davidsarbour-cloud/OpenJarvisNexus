import type { ModuleKey } from '../../lib/colors';
import { MODULE_COLORS } from '../../lib/colors';

/**
 * Optional Saturn-style ring around a planet.
 * Rendered as two concentric thin bands (Cassini-like split).
 */
export interface PlanetRing {
  /** Inner band start (in planet-radius multiples). */
  inner: number;
  /** Inner band end (also start of the gap). */
  innerOuter: number;
  /** Outer band start (after the gap). */
  outerInner: number;
  /** Outer band end. */
  outer: number;
  /** Ring color hex. */
  color: string;
  /** Tilt around X axis (rad) on top of the equatorial plane. */
  tilt: number;
  /** Roll around Z axis (rad). Useful for asymmetric tilt. */
  roll?: number;
  /** Base opacity multiplier (default 1). */
  opacity?: number;
}

export interface PlanetDef {
  id: ModuleKey;
  label: string;
  description: string;
  orbit: number;
  radius: number;
  speed: number;
  phase: number;
  tilt?: number;
  route?: string;
  external?: string;
  color: string;
  glow: string;
  /** Saturn-style ring. */
  ring?: PlanetRing;
  /** Subtle red-orange fire eruption overlay (FORGE). */
  fire?: boolean;
}

export type ShipPattern = 'recon' | 'relay' | 'maintenance' | 'patrol';

export interface SpaceshipDef {
  id: string;
  label: string;
  description: string;
  pattern: ShipPattern;
  mission: string;
  speed: number;
  phase: number;
  scale: number;
  scale2?: number;
  color: string;
  glow: string;
}

export interface JarvisDef {
  id: 'jarvis';
  label: string;
  description: string;
  color: string;
  glow: string;
  model: string;
  role: string;
  scope: string;
}

const c = (k: ModuleKey) => MODULE_COLORS[k];

export const JARVIS_DEF: JarvisDef = {
  id: 'jarvis',
  label: 'JARVIS',
  description:
    'Central orchestrator core. Every mission lands here first; JARVIS routes the request to FORGE, VAULT, CYBERDECK, COMMERCE or DOCKER and dispatches the right agent (Ultron, Qwen, Cortana, Bruce). Never bypassed.',
  color: c('jarvis').hex,
  glow:  c('jarvis').glow,
  model: 'claude-haiku-4-5',
  role:  'Orchestrator',
  scope: 'every message',
};

export const PLANETS: PlanetDef[] = [
  {
    id: 'forge',
    label: 'FORGE',
    description: 'STL pipeline · 3D fabrication · Meshy AI + trimesh',
    orbit: 5.5,  radius: 0.55, speed: 0.18,  phase: 0,             tilt: 0.04,
    color: c('forge').hex, glow: c('forge').glow,
    fire: true,
  },
  {
    id: 'vault',
    label: 'VAULT',
    description: 'Long-term memory · ChromaDB · facts & skills',
    orbit: 8.0,  radius: 0.50, speed: 0.13,  phase: 1.2,           tilt: -0.06,
    color: c('vault').hex, glow: c('vault').glow,
  },
  {
    id: 'cyberdeck',
    label: 'CYBERDECK',
    description: 'Security · surveillance · pen-test ops',
    orbit: 10.5, radius: 0.48, speed: 0.10,  phase: 2.4,           tilt: 0.08,
    color: c('cyberdeck').hex, glow: c('cyberdeck').glow,
    ring: {
      inner:      1.45,
      innerOuter: 1.75,
      outerInner: 1.85,
      outer:      2.30,
      color:      '#ff2d55',
      tilt:       0.42,
      roll:       0.08,
      opacity:    0.55,
    },
  },
  {
    id: 'commerce',
    label: 'COMMERCE',
    description: 'Etsy · Shopify · D3Dprintix store ops',
    orbit: 13.0, radius: 0.52, speed: 0.08,  phase: 3.6,           tilt: -0.05,
    color: c('commerce').hex, glow: c('commerce').glow,
  },
  {
    id: 'docker',
    label: 'DOCKER',
    description: 'Infra · containers',
    orbit: 15.5, radius: 0.92, speed: 0.065, phase: 4.8,           tilt: 0.10,
    color: c('docker').hex, glow: c('docker').glow,
  },
  {
    id: 'mining',
    label: 'MINING',
    description: 'AI trading · Alpaca · momentum + trailing stop · paper-only (validated on backtest, not live)',
    orbit: 18.5, radius: 0.60, speed: 0.05,  phase: 5.7,           tilt: -0.07,
    route: '/world/mining',
    color: c('mining').hex, glow: c('mining').glow,
    ring: {
      inner:      1.40,
      innerOuter: 1.70,
      outerInner: 1.82,
      outer:      2.25,
      color:      '#ffd60a',
      tilt:       0.50,
      roll:       0.12,
      opacity:    0.50,
    },
  },
];

export const SPACESHIPS: SpaceshipDef[] = [
  {
    id: 'ultron',  label: 'ULTRON',  description: 'Sonnet 4-6 · strategy',
    pattern: 'recon',
    mission: 'High-altitude recon scout',
    speed: 0.060, phase: 0.0,
    scale: 10.5, scale2: 2.4,
    color: c('cortex').hex, glow: c('cortex').glow,
  },
  {
    id: 'qwen',    label: 'QWEN',    description: 'Ollama qwen3:14b · general',
    pattern: 'relay',
    mission: 'Inter-station data relay',
    speed: 0.100, phase: 1.5,
    scale: 8.5, scale2: 1.8,
    color: c('jarvis').hex, glow: c('jarvis').glow,
  },
  {
    id: 'cortana', label: 'CORTANA', description: 'deepseek-coder · code',
    pattern: 'maintenance',
    mission: 'Maintenance shuttle FORGE / VAULT',
    speed: 0.120, phase: 3.0,
    scale: 8.0, scale2: 5.5,
    color: c('commerce').hex, glow: c('commerce').glow,
  },
  {
    id: 'bruce',   label: 'BRUCE',   description: 'OpenHands autonomous',
    pattern: 'patrol',
    mission: 'Wide perimeter patrol',
    speed: 0.045, phase: 4.5,
    scale: 14.5, scale2: 2.6,
    color: c('security').hex, glow: c('security').glow,
  },
  {
    id: 'valkyrie', label: 'VALKYRIE', description: 'OpenAI gpt-image-1 · image gen',
    pattern: 'recon',
    mission: 'Visual recon · image-generation sorties',
    speed: 0.075, phase: 2.2,
    scale: 12.0, scale2: 3.0,
    color: c('valkyrie').hex, glow: c('valkyrie').glow,
  },
];

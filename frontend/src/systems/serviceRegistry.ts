/**
 * Nexus9 — Service Registry (Phase 4 · Step 1)
 *
 * SINGLE SOURCE OF TRUTH for every monitored service.
 * Consumed by:
 *   - Command Center cards (icon, color, endpoint, status)
 *   - Orbital UI (which planet a service belongs to)
 *   - Alert engine (which system raised the alert)
 *   - Sidebar / Command Palette (routing)
 *
 * RULE: never hardcode a service id, endpoint, or color anywhere else.
 *       Always import from here.
 */
import {
  Server,        // ollama
  Database,      // chroma
  Activity,      // prometheus
  BarChart3,     // grafana
  ShieldCheck,   // sonarqube
  Boxes,         // docker / cadvisor
  HardDrive,     // postgres
  Zap,           // redis
  Network,       // traefik
  Bot,           // bruce (openhands)
  BookOpen,      // obsidian-skills
  Sparkles,      // superpowers
  Hammer,        // forge
  Lock,          // vault
  Cpu,           // backend
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ModuleKey } from '../lib/colors';

// ── Types ────────────────────────────────────────────────

export type ServiceCategory =
  | 'ai'           // LLMs, agents
  | 'memory'       // vector DBs, caches
  | 'monitoring'   // prometheus, grafana, cadvisor
  | 'quality'      // sonarqube
  | 'infra'        // docker, traefik, postgres
  | 'commerce'     // etsy, shopify
  | 'fabrication'  // forge, stl
  | 'security';    // vault, cyberdeck

export type ServiceStatus = 'live' | 'demo' | 'warn' | 'down' | 'loading';

export interface ServiceDef {
  /** Unique kebab-case id, e.g. "ollama", "chromadb". */
  id: string;
  /** Display name (uppercase recommended). */
  label: string;
  /** Short tagline. */
  description: string;
  /** Visual identity (mirrors MODULE_COLORS). */
  colorKey: ModuleKey;
  /** Lucide icon component. */
  icon: LucideIcon;
  /** Internal Nexus9 route, if any (e.g. "/orbital", "/agents"). */
  route?: string;
  /** External URL for the underlying service UI (Grafana, Sonar, etc.). */
  externalUrl?: string;
  /** Backend API endpoint that returns this service's live data. */
  apiEndpoint?: string;
  /** Direct container/host port for diagnostics. */
  hostPort?: number;
  /** Orbital planet/spaceship id this service is associated with. */
  orbitalRelation?: ModuleKey;
  /** Functional category. */
  category: ServiceCategory;
  /** Compose service name, for docker-related cross-refs. */
  containerName?: string;
}

// ── Registry ─────────────────────────────────────────────

export const SERVICES: ServiceDef[] = [
  // ─── AI layer ──────────────────────────────────────────
  {
    id: 'ollama',
    label: 'OLLAMA',
    description: 'Local LLM runtime (qwen3, deepseek, etc.)',
    colorKey: 'forge',
    icon: Server,
    route: '/agents',
    apiEndpoint: '/v1/models',
    hostPort: 11434,
    orbitalRelation: 'forge',
    category: 'ai',
    containerName: 'nexus_ollama',
  },
  {
    id: 'bruce',
    label: 'BRUCE',
    description: 'OpenHands autonomous agent',
    colorKey: 'security',
    icon: Bot,
    apiEndpoint: '/v1/agents',
    hostPort: 3000,
    orbitalRelation: 'cyberdeck',
    category: 'ai',
    containerName: 'nexus_bruce',
  },

  // ─── Memory ────────────────────────────────────────────
  {
    id: 'chromadb',
    label: 'CHROMADB',
    description: 'Vector memory · embeddings · long-term recall',
    colorKey: 'vault',
    icon: Database,
    apiEndpoint: '/v1/chromadb/stats',
    hostPort: 8001,
    orbitalRelation: 'vault',
    category: 'memory',
    containerName: 'nexus_chromadb',
  },
  {
    id: 'redis',
    label: 'REDIS',
    description: 'Session cache · rate-limiting · pub/sub',
    colorKey: 'jarvis',
    icon: Zap,
    hostPort: 6379,
    category: 'memory',
    containerName: 'nexus_redis',
  },

  // ─── Monitoring ────────────────────────────────────────
  {
    id: 'prometheus',
    label: 'PROMETHEUS',
    description: 'Metrics scraping · time-series store',
    colorKey: 'docker',
    icon: Activity,
    apiEndpoint: '/v1/prometheus/targets',
    externalUrl: 'http://localhost:9090',
    hostPort: 9090,
    orbitalRelation: 'docker',
    category: 'monitoring',
    containerName: 'nexus_prometheus',
  },
  {
    id: 'grafana',
    label: 'GRAFANA',
    description: 'Dashboards · visual telemetry',
    colorKey: 'docker',
    icon: BarChart3,
    externalUrl: 'http://localhost:3001',
    hostPort: 3001,
    orbitalRelation: 'docker',
    category: 'monitoring',
    containerName: 'nexus_grafana',
  },
  {
    id: 'cadvisor',
    label: 'CADVISOR',
    description: 'Container resource usage · CPU/RAM/IO',
    colorKey: 'docker',
    icon: Boxes,
    externalUrl: 'http://localhost:8888',
    hostPort: 8888,
    orbitalRelation: 'docker',
    category: 'monitoring',
    containerName: 'nexus_cadvisor',
  },

  // ─── Quality ───────────────────────────────────────────
  {
    id: 'sonarqube',
    label: 'SONARQUBE',
    description: 'Static analysis · bugs · vulnerabilities',
    colorKey: 'security',
    icon: ShieldCheck,
    apiEndpoint: '/v1/sonarqube/issues',
    externalUrl: 'http://localhost:9000',
    hostPort: 9000,
    orbitalRelation: 'cyberdeck',
    category: 'quality',
    containerName: 'nexus_sonarqube',
  },

  // ─── Infra ─────────────────────────────────────────────
  {
    id: 'docker',
    label: 'DOCKER',
    description: 'Container orchestration · all Nexus9 services',
    colorKey: 'docker',
    icon: Boxes,
    apiEndpoint: '/v1/docker/containers',
    orbitalRelation: 'docker',
    category: 'infra',
  },
  {
    id: 'traefik',
    label: 'TRAEFIK',
    description: 'Reverse proxy · TLS · routing',
    colorKey: 'docker',
    icon: Network,
    hostPort: 443,
    category: 'infra',
    containerName: 'nexus_traefik',
  },
  {
    id: 'postgres',
    label: 'POSTGRES',
    description: 'Relational store (Sonar + app data)',
    colorKey: 'vault',
    icon: HardDrive,
    hostPort: 5432,
    category: 'infra',
    containerName: 'nexus_postgres',
  },
  {
    id: 'backend',
    label: 'BACKEND',
    description: 'Nexus9 FastAPI · orchestrator',
    colorKey: 'jarvis',
    icon: Cpu,
    apiEndpoint: '/v1/health/deep',
    hostPort: 8000,
    category: 'infra',
    containerName: 'nexus_backend',
  },

  // ─── Skills bridges ────────────────────────────────────
  {
    id: 'obsidian',
    label: 'OBSIDIAN',
    description: 'Obsidian Skills bridge',
    colorKey: 'cortex',
    icon: BookOpen,
    externalUrl: 'http://localhost:8081',
    hostPort: 8081,
    category: 'ai',
    containerName: 'nexus_obsidian',
  },
  {
    id: 'superpowers',
    label: 'SUPERPOWERS',
    description: 'Mission routing bridge',
    colorKey: 'cortex',
    icon: Sparkles,
    externalUrl: 'http://localhost:8082',
    hostPort: 8082,
    category: 'ai',
    containerName: 'nexus_superpowers',
  },

  // ─── Fabrication ───────────────────────────────────────
  {
    id: 'forge',
    label: 'FORGE',
    description: 'STL pipeline · Meshy AI · D3Dprintix',
    colorKey: 'forge',
    icon: Hammer,
    apiEndpoint: '/v1/crew/jobs',
    orbitalRelation: 'forge',
    category: 'fabrication',
  },

  // ─── Security ──────────────────────────────────────────
  {
    id: 'vault',
    label: 'VAULT',
    description: 'Secrets · credentials · key store',
    colorKey: 'vault',
    icon: Lock,
    orbitalRelation: 'vault',
    category: 'security',
  },
];

// ── Helpers ──────────────────────────────────────────────

const _byId = new Map(SERVICES.map((s) => [s.id, s]));

export const getService = (id: string): ServiceDef | undefined => _byId.get(id);

export const servicesByCategory = (cat: ServiceCategory): ServiceDef[] =>
  SERVICES.filter((s) => s.category === cat);

export const servicesByOrbital = (planet: ModuleKey): ServiceDef[] =>
  SERVICES.filter((s) => s.orbitalRelation === planet);

export const ALL_SERVICE_IDS: ReadonlyArray<string> = SERVICES.map((s) => s.id);

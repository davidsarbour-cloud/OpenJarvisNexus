/**
 * Nexus9 — Command Center live API wrappers.
 *
 * Thin layer above the existing api.ts. Each function targets one
 * Phase-2 widget. Endpoints with stub/empty backend responses are
 * documented inline.
 *
 * Base URL resolution:
 *   - In Vite dev, requests are relative (proxied or hit the same host).
 *   - Setting VITE_API_URL overrides at build time.
 */

const API_BASE = (() => {
  try {
    if (typeof window !== 'undefined') {
      const raw = localStorage.getItem('openjarvis-settings');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.apiUrl) return String(parsed.apiUrl).replace(/\/+$/, '');
      }
    }
  } catch { /* ignore */ }
  const env = (import.meta as { env?: Record<string, string> }).env;
  if (env && env.VITE_API_URL) return env.VITE_API_URL.replace(/\/+$/, '');
  return '';
})();

const url = (path: string): string => `${API_BASE}${path}`;

async function getJSON<T>(path: string, timeoutMs = 4000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url(path), { signal: ctrl.signal });
    if (!r.ok) throw new Error(`HTTP ${r.status} on ${path}`);
    return (await r.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

async function postJSON<T>(path: string, timeoutMs = 5000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url(path), { method: 'POST', signal: ctrl.signal });
    if (!r.ok) throw new Error(`HTTP ${r.status} on ${path}`);
    return (await r.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

// ─── Health ────────────────────────────────────────────
export type ServiceStatus = string; // "ok" | "offline" | "timeout" | "not_configured" | "error: ..."

export interface HealthDeep {
  backend:    ServiceStatus;
  claude_api: ServiceStatus;
  ollama:     ServiceStatus;
  forge_room: ServiceStatus;
  meshy_api:  ServiceStatus;
  timestamp:  string;
}

export const fetchHealthDeep = () => getJSON<HealthDeep>('/v1/health/deep', 6000);

// ─── Mining (Phase 3 — proxy to the mining orchestrator :8090) ──
// Every endpoint is enveloped: {cluster:'online'|'offline', data}. The cluster
// is normally OFFLINE (docker-compose.mining not running) — the UI degrades.
export interface MiningEnvelope<T = unknown> {
  cluster: 'online' | 'offline';
  data: T | null;
  error?: string;
}
export interface MiningHealth {
  ok: boolean;
  mode: string;            // "paper" | "live"
  live_enabled: boolean;
  tickers: string[];
  halted: boolean | null;
}
export const fetchMiningHealth = () =>
  getJSON<MiningEnvelope<MiningHealth>>('/v1/mining/health', 4000);
export const fetchMiningPositions = () =>
  getJSON<MiningEnvelope<Record<string, unknown>>>('/v1/mining/positions', 4000);
export const haltMining = (on: boolean) =>
  postJSON<MiningEnvelope>(`/v1/mining/halt?on=${on}`);

// ─── Agents ────────────────────────────────────────────
export type AgentStatus = 'online' | 'idle' | 'offline' | string;

export interface AgentInfo {
  id: string;
  name: string;
  provider: string;
  model: string;
  role: string;
  description: string;
  status: AgentStatus;
}

export const fetchAgents = () =>
  getJSON<{ agents: AgentInfo[] }>('/v1/agents');

// ─── Models ────────────────────────────────────────────
export interface ModelInfo {
  id: string;
  provider: string;
  available: boolean;
}

export const fetchModels = () =>
  getJSON<{ models: ModelInfo[] }>('/v1/models');

// ─── Crew jobs (forge / missions) ──────────────────────
export interface CrewJob {
  id?: string;
  status?: string;
  [k: string]: unknown;
}

export const fetchCrewJobs = () =>
  getJSON<{ jobs: CrewJob[] }>('/v1/crew/jobs');

// ─── Budget ────────────────────────────────────────────
export interface BudgetInfo {
  session?: {
    cost_usd: number;
    calls_claude: number;
    calls_ollama: number;
  };
  budget_max?: number;
  budget_remaining?: number;
  [k: string]: unknown;
}

export const fetchBudget = () => getJSON<BudgetInfo>('/v1/budget');

// ─── Logs (currently a backend stub returning {logs: []}) ──
export interface LogEntry {
  ts?: string;
  level?: string;
  source?: string;
  msg?: string;
  [k: string]: unknown;
}

export const fetchLogs = () =>
  getJSON<{ logs: LogEntry[] }>('/v1/logs');


// ════════════════════════════════════════════════════════
// Phase 4 — Monitoring proxies (Docker / Prometheus / ChromaDB / Sonar / Grafana)
// ════════════════════════════════════════════════════════

// ─── Docker via docker.sock / TCP / cAdvisor ───────────
export interface DockerContainer {
  id: string;
  name: string;
  image: string;
  running: boolean;
}

export interface DockerContainersResponse {
  available: boolean;
  source?: string;
  error?: string;
  count?: number;
  containers: DockerContainer[];
}

export const fetchDockerContainers = () =>
  getJSON<DockerContainersResponse>('/v1/docker/containers', 6000);

// ─── ChromaDB ──────────────────────────────────────────
export interface ChromaStatsResponse {
  available: boolean;
  heartbeat?: unknown;
  collections: number | null;
  error?: string;
}

export const fetchChromaStats = () =>
  getJSON<ChromaStatsResponse>('/v1/chromadb/stats');

// ─── World Cards Snapshot (/v1/world/cards/snapshot) ───
export interface WorldCardMetric {
  label: string;
  value: string;
}

export interface WorldCardSnapshot {
  status:  'active' | 'standby';
  metrics: WorldCardMetric[];
}

export interface WorldCardsSnapshotData {
  stl_output:         WorldCardSnapshot;
  approval_queue:     WorldCardSnapshot;
  token_budget:       WorldCardSnapshot;
  gpu_temp:           WorldCardSnapshot;
  error_log:          WorldCardSnapshot;
  vault_growth:       WorldCardSnapshot;
  orphan_alert:       WorldCardSnapshot;
  morning_brief:      WorldCardSnapshot;
  disk_usage:         WorldCardSnapshot;
  container_logs:     WorldCardSnapshot;
  telegram_activity:  WorldCardSnapshot;
  model_routing:      WorldCardSnapshot;
  generated_at:       string;
}

export const fetchWorldCardsSnapshot = () =>
  getJSON<WorldCardsSnapshotData>('/v1/world/cards/snapshot', 6000);

// ─── Boot info (/v1/boot/info) — uptime since the backend process started ──
export interface BootInfo {
  boot_id:    string;
  started_at: string; // ISO8601 UTC, e.g. "2026-05-28T18:40:00+00:00"
}

export const fetchBootInfo = () => getJSON<BootInfo>('/v1/boot/info', 5000);

// ─── Scheduled Tasks (/v1/daily/status) ────────────────
export interface ScheduledJob {
  id: string;
  name: string;
  next_run: string;
}

export interface ScheduledJobsResponse {
  status: string;
  jobs: ScheduledJob[];
}

export const fetchScheduledTasks = () =>
  getJSON<ScheduledJobsResponse>('/v1/daily/status');

// ─── System Metrics (/v1/system/metrics) ───────────────
export interface SystemMetrics {
  cpu:          number;
  ram:          number;
  vram:         number | null;
  storage:      number | null;
  network_mbps: number;
  health_score: number;
  health_label: string;
}

export const fetchSystemMetrics = () =>
  getJSON<SystemMetrics>('/v1/system/metrics', 3000);

// ─── Health aggregator (/v1/health/all) ────────────────
export type HealthStatus = 'up' | 'down' | 'warn';

export interface HealthService {
  status: HealthStatus;
  detail: unknown;
}

export interface HealthAll {
  overall: 'healthy' | 'degraded' | 'down';
  ts: string;
  services: Record<string, HealthService>;
}

export const fetchHealthAll = () => getJSON<HealthAll>('/v1/health/all', 8000);

// ─── Auto-Factory (/v1/factory) — 3 production lines ───────
export interface FactoryLineState { done: string[]; cycle: number; }
export interface FactoryConfigResponse {
  config: {
    enabled: boolean;
    schedule_hour: number;
    schedule_minute: number;
    selection_mode: string;
    products: string[];
    [k: string]: unknown;
  };
  state: {
    stl:   FactoryLineState;
    icons: FactoryLineState;
    pod:   FactoryLineState;
    last?: string;
  };
  stl_niches:  number;
  icon_themes: number;
  pod_designs: number;
}
export const fetchFactoryConfig = () =>
  getJSON<FactoryConfigResponse>('/v1/factory/config', 5000);

export interface FactoryCatalogItem { key: string; tier: string; label: string; }
export interface FactoryCatalogResponse {
  stl_niches:  FactoryCatalogItem[];
  icon_themes: FactoryCatalogItem[];
  pod_designs: FactoryCatalogItem[];
}
export const fetchFactoryCatalog = () =>
  getJSON<FactoryCatalogResponse>('/v1/factory/catalog', 5000);

export interface FactoryDryRunResponse {
  dry?: boolean;
  detail?: Record<string, { label: string; reason: string }>;
}
export const postFactoryDryRun = () =>
  postJSON<FactoryDryRunResponse>('/v1/factory/run?dry=true', 20000);

// src/types.ts — VERSION CORRIGÉE COMPLÈTE

// ============================================
// TYPES DE BASE NexusX9
// ============================================

export type AgentStatus = 
  | "idle" 
  | "active" 
  | "processing" 
  | "error" 
  | "offline";

export type AgentName = 
  | "Architecte" 
  | "Laboratoire" 
  | "Surveillance" 
  | "AtelierCode" 
  | "CoffreMémoire";

export type MessageRole = "user" | "assistant" | "system" | "agent";

export type EventType =
  | "agent_status_change"
  | "task_created"
  | "task_completed"
  | "task_failed"
  | "energy_pulse"
  | "memory_updated"
  | "orchestrator_message";

// ============================================
// INTERFACES AGENTS
// ============================================

export interface AgentConfig {
  id: string;
  name: AgentName;
  model: "claude" | "ollama";
  status: AgentStatus;
  orbitRadius: number;
  color: string;
  glowColor: string;
  capabilities: string[];
}

export interface AgentState {
  config: AgentConfig;
  currentTask: Task | null;
  taskHistory: Task[];
  energyLevel: number;       // 0-100
  processingLoad: number;    // 0-100
  lastActive: Date | null;
}

// ============================================
// INTERFACES TÂCHES
// ============================================

export interface Task {
  id: string;
  title: string;
  description: string;
  assignedAgent: AgentName;
  status: "pending" | "running" | "completed" | "failed";
  priority: "low" | "medium" | "high" | "critical";
  createdAt: Date;
  completedAt: Date | null;
  result: string | null;
  metadata: Record<string, unknown>;
}

export interface TaskRequest {
  prompt: string;
  targetAgent?: AgentName;
  priority?: Task["priority"];
  context?: string;
}

export interface TaskResponse {
  taskId: string;
  agentName: AgentName;
  result: string;
  processingTime: number;
  tokensUsed?: number;
  success: boolean;
  error?: string;
}

// ============================================
// INTERFACES MESSAGES
// ============================================

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  agentName?: AgentName;
  timestamp: Date;
  metadata?: {
    model?: string;
    tokens?: number;
    processingMs?: number;
  };
}

export interface ConversationContext {
  sessionId: string;
  messages: ChatMessage[];
  activeAgent: AgentName | null;
  startedAt: Date;
}

// ============================================
// INTERFACES WEBSOCKET / EVENTS
// ============================================

export interface WSEvent {
  type: EventType;
  payload: unknown;
  timestamp: string;
  source: AgentName | "orchestrator" | "system";
}

export interface AgentStatusEvent {
  type: "agent_status_change";
  agentName: AgentName;
  oldStatus: AgentStatus;
  newStatus: AgentStatus;
  reason?: string;
}

export interface EnergyPulseEvent {
  type: "energy_pulse";
  from: AgentName | "jarvis";
  to: AgentName | "jarvis";
  intensity: number;
  color?: string;
}

// ============================================
// INTERFACES UI / SOLAIRE
// ============================================

export interface PlanetPosition {
  x: number;
  y: number;
  angle: number;
  orbitRadius: number;
  speed: number;
}

export interface EnergyLine {
  id: string;
  fromAgent: AgentName | "jarvis";
  toAgent: AgentName | "jarvis";
  active: boolean;
  intensity: number;
  color: string;
  animationPhase: number;
}

export interface SolarSystemState {
  planets: Record<AgentName, PlanetPosition>;
  energyLines: EnergyLine[];
  centerPulse: number;
  globalEnergy: number;
}

// ============================================
// INTERFACES API
// ============================================

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

export interface OllamaRequest {
  model: string;
  prompt: string;
  stream: boolean;
  options?: {
    temperature?: number;
    top_p?: number;
    max_tokens?: number;
  };
}

export interface OllamaResponse {
  model: string;
  response: string;
  done: boolean;
  context?: number[];
  total_duration?: number;
  eval_count?: number;
}

// ============================================
// INTERFACES MÉMOIRE
// ============================================

export interface MemoryEntry {
  id: string;
  key: string;
  value: unknown;
  category: "context" | "result" | "config" | "knowledge";
  agentOwner: AgentName | "global";
  createdAt: Date;
  expiresAt: Date | null;
  accessCount: number;
}

export interface MemoryStore {
  entries: Record<string, MemoryEntry>;
  totalSize: number;
  lastCleanup: Date;
}

// ============================================
// INTERFACES SYSTÈME
// ============================================

export interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  activeAgents: number;
  tasksCompleted: number;
  tasksRunning: number;
  uptime: number;
  wsConnections: number;
}

export interface NexusConfig {
  version: string;
  environment: "development" | "production";
  apiBaseUrl: string;
  wsBaseUrl: string;
  ollamaUrl: string;
  defaultModel: string;
  maxConcurrentTasks: number;
  debugMode: boolean;
}
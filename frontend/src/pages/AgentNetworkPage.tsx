/**
 * Nexus9 — Agent Network (Phase 4 · Step 8)
 *
 * React Flow visualization of the agent constellation.
 * JARVIS sits at the center as the orchestrator; every other agent
 * has an animated edge back to it (representing the dispatch link).
 *
 * Status is fetched live from /v1/agents (polled every 8s via
 * useLiveMetric) and reflected in the pulsing dot on each node.
 */
import { useMemo, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Edge,
  type NodeTypes,
  MarkerType,
  type ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  AgentNode,
  type AgentNodeData,
  type AgentFlowNode,
} from '../components/AgentNetwork/AgentNode';
import { AgentDetailPanel } from '../components/AgentNetwork/AgentDetailPanel';
import { useLiveMetric } from '../hooks/useLiveMetric';
import { fetchAgents, type AgentInfo } from '../lib/apiLive';
import { MODULE_COLORS, type ModuleKey } from '../lib/colors';
import { useNexusStore } from '../systems/nexusStore';

// ── Identity mapping ─────────────────────────────────────
const AGENT_COLOR: Record<string, ModuleKey> = {
  jarvis:  'jarvis',
  ultron:  'cortex',
  qwen:    'jarvis',
  cortana: 'commerce',
  kaizen:  'forge',
  bruce:   'security',
  etsy:    'commerce',
  forge:   'forge',
  vault:   'vault',
  nova:    'cyberdeck',
};

// Top-level agents only — the STL sub-agents (stl_blender, stl_concept,
// stl_optim, stl_files, stl_research) and ETSY are internal roles inside
// the FORGE/Commerce pipelines, not standalone agents. They live in the
// Pipeline Hub view, not in the Agent Network.
const MAIN_AGENT_IDS = new Set([
  'jarvis', 'ultron', 'kaizen', 'qwen', 'cortana', 'bruce', 'nova', 'forge',
]);

// Fallback agent set if the backend is unreachable.
const FALLBACK_AGENTS: AgentInfo[] = [
  { id: 'jarvis',  name: 'JARVIS',  provider: 'claude',  model: 'claude-haiku-4-5',   role: 'Orchestrator',        description: '', status: 'online' },
  { id: 'ultron',  name: 'ULTRON',  provider: 'claude',  model: 'claude-sonnet-4-6',  role: 'Strategy & Analysis', description: '', status: 'idle' },
  { id: 'qwen',    name: 'QWEN',    provider: 'ollama',  model: 'qwen3:14b',          role: 'General reasoning',   description: '', status: 'online' },
  { id: 'cortana', name: 'CORTANA', provider: 'ollama',  model: 'deepseek-coder:6.7b',role: 'Code',                description: '', status: 'online' },
  { id: 'bruce',   name: 'BRUCE',   provider: 'openhands', model: 'qwen3:14b',        role: 'Autonomous',          description: '', status: 'idle' },
  { id: 'nova',    name: 'NOVA',    provider: 'ollama',  model: 'deepseek-r1:7b',     role: 'Complex code',        description: '', status: 'offline' },
  { id: 'forge',   name: 'FORGE',   provider: 'local',   model: 'Meshy AI + trimesh', role: 'STL pipeline',        description: '', status: 'online' },
];

function ringPosition(idx: number, total: number, radius = 320) {
  const angle = (idx / total) * Math.PI * 2 - Math.PI / 2;
  return {
    x: 480 + Math.cos(angle) * radius,
    y: 320 + Math.sin(angle) * radius,
  };
}

const NODE_TYPES: NodeTypes = { agent: AgentNode };

export default function AgentNetworkPage() {
  const { data, error } = useLiveMetric(fetchAgents, { intervalMs: 8000, wsTopic: 'snapshot/agents' });
  const setFocusedService = useNexusStore((s) => s.setFocusedService);
  const rfRef = useRef<ReactFlowInstance<AgentFlowNode, Edge> | null>(null);
  // Selected agent for the side-panel detail view. null = panel closed.
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  const agents: AgentInfo[] = useMemo(() => {
    const live = data?.agents ?? [];
    const source = live.length ? live : FALLBACK_AGENTS;
    // Keep only top-level agents — drop STL sub-agents + ETSY internals.
    return source.filter((a) => MAIN_AGENT_IDS.has(a.id));
  }, [data]);

  const selectedAgent = useMemo(
    () => (selectedAgentId ? agents.find((a) => a.id === selectedAgentId) ?? null : null),
    [selectedAgentId, agents],
  );
  const selectedColorKey: ModuleKey =
    (selectedAgent && AGENT_COLOR[selectedAgent.id]) || 'jarvis';

  const nodes: AgentFlowNode[] = useMemo(() => {
    const jarvis = agents.find((a) => a.id === 'jarvis');
    const others = agents.filter((a) => a.id !== 'jarvis');

    const makeNode = (a: AgentInfo, pos: { x: number; y: number }, isCore = false): AgentFlowNode => ({
      id: a.id,
      type: 'agent',
      position: pos,
      data: {
        label: a.name,
        role: a.role,
        model: a.model,
        colorKey: AGENT_COLOR[a.id] ?? 'jarvis',
        status: a.status,
        isCore,
      },
      draggable: true,
    });

    const list: AgentFlowNode[] = [];
    if (jarvis) list.push(makeNode(jarvis, { x: 460, y: 300 }, true));
    others.forEach((a, i) => list.push(makeNode(a, ringPosition(i, others.length))));
    return list;
  }, [agents]);

  const edges: Edge[] = useMemo(() => {
    const jarvisId = agents.find((a) => a.id === 'jarvis')?.id ?? 'jarvis';
    return agents
      .filter((a) => a.id !== 'jarvis')
      .map<Edge>((a) => {
        const colorKey = AGENT_COLOR[a.id] ?? 'jarvis';
        const color = MODULE_COLORS[colorKey].hex;
        return {
          id: `e-${jarvisId}-${a.id}`,
          source: jarvisId,
          target: a.id,
          animated: a.status === 'online',
          style: {
            stroke: color,
            strokeWidth: 1.2,
            opacity: a.status === 'offline' ? 0.25 : 0.65,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color,
            width: 12,
            height: 12,
          },
        };
      });
  }, [agents]);

  useEffect(() => {
    if (error) console.debug('[AgentNetwork] /v1/agents error:', error);
  }, [error]);

  // Re-fit the viewport whenever the agent count changes — the ringPosition
  // anchors recompute on every count change (e.g. fallback 7 → live 12), so
  // existing nodes shift outward and would otherwise leave the viewport.
  useEffect(() => {
    if (!rfRef.current || agents.length === 0) return;
    // Defer one frame so React Flow finishes laying out the new nodes before fitting.
    const t = window.setTimeout(() => {
      rfRef.current?.fitView({ padding: 0.2, duration: 500 });
    }, 80);
    return () => window.clearTimeout(t);
  }, [agents.length]);

  return (
    <div
      className="flex-1 relative"
      style={{
        background: 'var(--hud-bg)',
        backgroundImage: [
          'linear-gradient(var(--hud-grid) 1px, transparent 1px)',
          'linear-gradient(90deg, var(--hud-grid) 1px, transparent 1px)',
        ].join(','),
        backgroundSize: '32px 32px, 32px 32px',
      }}
    >
      {/* Header strip */}
      <div
        className="absolute top-0 left-0 right-0 z-10 px-4 py-2 flex items-center gap-3 text-[10px] font-bold tracking-[0.3em]"
        style={{
          background: 'rgba(0,0,0,0.55)',
          borderBottom: '1px solid var(--hud-border)',
          color: 'var(--hud-text-dim)',
          backdropFilter: 'blur(4px)',
        }}
      >
        <span style={{ color: 'var(--color-jarvis)' }}>◆</span>
        AGENT NETWORK
        <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
        <span style={{ color: 'var(--hud-text-dim)' }}>
          {agents.length} NODES · {edges.filter((e) => e.animated).length} ACTIVE LINKS
        </span>
        {error && (
          <span style={{ color: 'var(--color-security)' }}>FALLBACK MAP</span>
        )}
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.6}
        defaultEdgeOptions={{ animated: true }}
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_, n) => {
          setSelectedAgentId(n.id);
          setFocusedService(n.id);
        }}
        onPaneClick={() => setSelectedAgentId(null)}
        onInit={(rf) => { rfRef.current = rf; }}
        style={{ width: '100%', height: '100%' }}
      >
        <Background gap={24} size={1} color="var(--hud-grid)" />
        <Controls
          showInteractive={false}
          style={{
            background: 'rgba(2,5,11,0.85)',
            border: '1px solid var(--hud-border)',
          }}
        />
        <MiniMap
          pannable
          zoomable
          nodeColor={(n) => {
            const data = (n.data ?? {}) as Partial<AgentNodeData>;
            const key = data.colorKey ?? 'jarvis';
            return MODULE_COLORS[key]?.hex ?? '#00d4ff';
          }}
          style={{
            background: 'rgba(2,5,11,0.85)',
            border: '1px solid var(--hud-border)',
          }}
        />
      </ReactFlow>

      <AgentDetailPanel
        agent={selectedAgent}
        colorKey={selectedColorKey}
        onClose={() => setSelectedAgentId(null)}
      />
    </div>
  );
}

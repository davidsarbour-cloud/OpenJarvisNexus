/**
 * Nexus9 — Pipeline Hub.
 *
 * Pipelines grouped by category. Click a card to expand and see all
 * the steps in detail. Layout uses the standard Nexus9 10-col
 * responsive grid (matches CommandCenterPage).
 *
 * Progress is estimated client-side from a per-pipeline
 * `estimatedSecondsPerStep` tick — the real backend pipelines don't
 * yet expose a uniform progress endpoint.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { Boxes, ShoppingBag, Zap, Search, Container } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import {
  PipelineNode,
  type PipelineRunState,
} from '../components/PipelineHub/PipelineNode';
import { MODULE_COLORS, type ModuleKey } from '../lib/colors';

interface PipelineSpec {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
  colorKey: ModuleKey;
  category: string;
  totalSteps: number;
  estimatedSecondsPerStep: number;
  steps: string[];
  endpoint?: string;
  bodyKey?: string;
  inputLabel?: string;
  obsidianPath?: string;
}

const OBSIDIAN_VAULT = 'BRAIN';

const PIPELINES: PipelineSpec[] = [
  {
    id: 'stl',
    label: 'STL Pipeline',
    category: 'fabrication',
    description: '3D model · Meshy → repair → orient → export',
    icon: Boxes,
    colorKey: 'forge',
    totalSteps: 11,
    estimatedSecondsPerStep: 12,
    endpoint: '/v1/forge/mission',
    bodyKey: 'prompt',
    inputLabel: 'ex: dragon égyptien stylisé...',
    obsidianPath: '03_Projects/STL/stl-pipeline.md',
    steps: [
      'Routing (JARVIS detects intent)',
      'Planning (ULTRON fabrication brief)',
      'Code generation (DeepSeek availability)',
      'Mesh generation (Meshy → Blender → OpenSCAD)',
      'Validation (raw mesh quality audit)',
      'Repair (auto-fix manifold issues)',
      'Orientation (FDM optimization)',
      'Support analysis (overhang detection)',
      'Final validation (printability score)',
      'Export (STL file generation)',
      'Report (metrics + Vault persistence)',
    ],
  },
  {
    id: 'commerce',
    label: 'Commerce',
    category: 'commerce',
    description: 'Concept → STL → metadata → approval → publish',
    icon: ShoppingBag,
    colorKey: 'commerce',
    totalSteps: 5,
    estimatedSecondsPerStep: 25,
    endpoint: '/v1/commerce/pipeline',
    bodyKey: 'idea',
    inputLabel: 'product idea...',
    obsidianPath: '07_Schemas/system/commerce-pipeline.md',
    steps: [
      'Concept (ULTRON product brief)',
      'Fabrication (Forge Room STL gen)',
      'Metadata (ULTRON + QWEN SEO copy)',
      'Approval queue (human review)',
      'Publishing (Etsy / Shopify push)',
    ],
  },
  {
    id: 'cheat-code',
    label: 'Cheat Code',
    category: 'system',
    description: 'System sync · daily tasks · vault index',
    icon: Zap,
    colorKey: 'jarvis',
    totalSteps: 8,
    estimatedSecondsPerStep: 8,
    endpoint: '/v1/cheat-code',
    obsidianPath: '07_Schemas/system/cheat-code-pipeline.md',
    steps: [
      'Sync agents (parallel · Ollama, Backend, BRUCE, Claude)',
      'Fetch Vault stats (collections + scheduled jobs)',
      'Fetch ecosystem score (0–100 + grade)',
      'Daily tasks · 4 parallel (cleanup · STL sync · logs)',
      'Daily tasks · 6 sequential (analytics · maintenance · smoke)',
      'Persist to Vault (orchestration summary → ChromaDB)',
      'Write reports (JSON + Markdown → 08_Command-Center)',
      'Brain re-index + TTS notification (fr-FR)',
    ],
  },
  {
    id: 'docker',
    label: 'Docker Restart',
    category: 'infrastructure',
    description: 'Restart all Nexus9 stack containers in place',
    icon: Container,
    colorKey: 'docker',
    totalSteps: 5,
    estimatedSecondsPerStep: 8,
    endpoint: '/v1/docker/restart',
    obsidianPath: '07_Schemas/system/docker-restart-pipeline.md',
    steps: [
      'Send SIGTERM to all services',
      'Containers stop (graceful 10s grace)',
      'Start containers back up',
      'Verify daemon connectivity',
      'Confirm all services up',
    ],
  },
  {
    id: 'research',
    label: 'Daily Research',
    category: 'knowledge',
    description: '8 parallel Ollama research tasks',
    icon: Search,
    colorKey: 'cortex',
    totalSteps: 8,
    estimatedSecondsPerStep: 30,
    endpoint: '/v1/pipeline/daily/start',
    obsidianPath: '07_Schemas/system/daily-research-pipeline.md',
    steps: [
      'Code snippets (20 AI/Python/JS scripts)',
      'STL models (15 open-source 3D models)',
      'Thumbnails (30 video/product ideas)',
      'AI innovation (10 recent 2026 trends)',
      'Agent AI (8 automation agents)',
      'AI tools (25 frameworks/SaaS/libs)',
      'Learning resources (15 tutorials)',
      'Project ideas (10 AI/3D projects)',
    ],
  },
];


interface CategorySpec {
  id: string;
  label: string;
  accent: ModuleKey;
}

const CATEGORIES: CategorySpec[] = [
  { id: 'fabrication',    label: 'FABRICATION',    accent: 'forge'    },
  { id: 'commerce',       label: 'COMMERCE',       accent: 'commerce' },
  { id: 'system',         label: 'SYSTEM OPS',     accent: 'jarvis'   },
  { id: 'knowledge',      label: 'KNOWLEDGE',      accent: 'cortex'   },
  { id: 'infrastructure', label: 'INFRASTRUCTURE', accent: 'docker'   },
];

const PIPELINE_IMAGE = '/world/pipeline.png';
const DOCK_WIDTH = 360;

function initialRunState(): PipelineRunState {
  return { status: 'idle', currentStep: 0 };
}

function SectionTitle({ text, accent }: { text: string; accent: string }) {
  return (
    <div
      className="flex items-center gap-3 text-[10px] font-bold tracking-[0.3em] mb-2"
      style={{ color: 'var(--hud-text-dim)' }}
    >
      <span style={{ color: accent }}>◆</span>
      {text}
      <span className="flex-1" style={{ height: 1, background: 'var(--hud-border)' }} />
    </div>
  );
}

export default function PipelineHubPage() {
  const [runStates, setRunStates] = useState<Record<string, PipelineRunState>>(
    () => Object.fromEntries(PIPELINES.map((p) => [p.id, initialRunState()])),
  );
  const [inputs, setInputs] = useState<Record<string, string>>(
    () => Object.fromEntries(PIPELINES.map((p) => [p.id, ''])),
  );
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [imgFailed, setImgFailed] = useState(false);

  const tickersRef = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  const stopTicker = useCallback((id: string) => {
    const t = tickersRef.current[id];
    if (t) {
      clearInterval(t);
      delete tickersRef.current[id];
    }
  }, []);

  useEffect(() => {
    const refs = tickersRef.current;
    return () => {
      Object.values(refs).forEach((t) => clearInterval(t));
    };
  }, []);

  const handleInputChange = useCallback((id: string, v: string) => {
    setInputs((prev) => ({ ...prev, [id]: v }));
  }, []);

  const handleToggleExpand = useCallback((id: string) => {
    setExpandedId((cur) => (cur === id ? null : id));
  }, []);

  const handleActivate = useCallback(
    async (id: string) => {
      const spec = PIPELINES.find((p) => p.id === id);
      if (!spec || !spec.endpoint) return;

      const input = inputs[id]?.trim() ?? '';
      if (spec.inputLabel && !input) {
        setRunStates((prev) => ({
          ...prev,
          [id]: { status: 'error', currentStep: 0, message: 'Input required' },
        }));
        return;
      }

      const startedAt = Date.now();
      setRunStates((prev) => ({
        ...prev,
        [id]: { status: 'running', currentStep: 0, startedAt },
      }));
      setExpandedId(id);

      stopTicker(id);
      const stepMs = spec.estimatedSecondsPerStep * 1000;
      tickersRef.current[id] = setInterval(() => {
        setRunStates((prev) => {
          const cur = prev[id];
          if (!cur || cur.status !== 'running') return prev;
          const elapsed = Date.now() - (cur.startedAt ?? startedAt);
          const estimatedStep = Math.min(spec.totalSteps - 1, Math.floor(elapsed / stepMs));
          if (estimatedStep === cur.currentStep) return prev;
          return { ...prev, [id]: { ...cur, currentStep: estimatedStep } };
        });
      }, 800);

      try {
        const body: Record<string, unknown> = {};
        if (spec.bodyKey) {
          body[spec.bodyKey] = input;
        }
        const res = await fetch(spec.endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });

        stopTicker(id);

        if (!res.ok) {
          setRunStates((prev) => ({
            ...prev,
            [id]: {
              status: 'error',
              currentStep: prev[id]?.currentStep ?? 0,
              startedAt,
              finishedAt: Date.now(),
              message: `HTTP ${res.status}`,
            },
          }));
          return;
        }

        // Some pipelines return HTTP 200 with { ok: false, error: ... } on failure.
        let payload: { ok?: boolean; error?: string } | null = null;
        try {
          payload = (await res.clone().json()) as { ok?: boolean; error?: string };
        } catch {
          /* not JSON or empty — treat as success */
        }
        if (payload && payload.ok === false) {
          setRunStates((prev) => ({
            ...prev,
            [id]: {
              status: 'error',
              currentStep: prev[id]?.currentStep ?? 0,
              startedAt,
              finishedAt: Date.now(),
              message: payload?.error ?? 'pipeline returned ok=false',
            },
          }));
          return;
        }

        setRunStates((prev) => ({
          ...prev,
          [id]: {
            status: 'done',
            currentStep: spec.totalSteps,
            startedAt,
            finishedAt: Date.now(),
          },
        }));
      } catch (err) {
        stopTicker(id);
        setRunStates((prev) => ({
          ...prev,
          [id]: {
            status: 'error',
            currentStep: prev[id]?.currentStep ?? 0,
            startedAt,
            finishedAt: Date.now(),
            message: err instanceof Error ? err.message : 'network error',
          },
        }));
      }
    },
    [inputs, stopTicker],
  );

  const activeCount = Object.values(runStates).filter((s) => s.status === 'running').length;

  return (
    <div
      className="flex-1 relative overflow-hidden min-h-0"
      style={{ background: 'var(--hud-bg)' }}
    >
      {/* Background — pipeline image fills the whole frame */}
      {imgFailed ? <PipelineImageNotFound /> : <PipelineImage onError={() => setImgFailed(true)} />}

      {/* LEFT overlay — pipeline cards sit ON the left side of the picture */}
      <div
        style={{
          position: 'absolute', left: 0, top: 0, bottom: 0, zIndex: 2,
          width: DOCK_WIDTH,
          overflowY: 'auto',
          padding: 12,
          background: 'rgba(2,4,12,0.62)',
          backdropFilter: 'blur(2px)',
          borderRight: '1px solid var(--hud-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <div
          className="flex items-center gap-2 text-[10px] font-bold tracking-[0.3em] shrink-0"
          style={{ color: 'var(--hud-text-dim)' }}
        >
          <span style={{ color: 'var(--color-security)' }}>◆</span>
          PIPELINE HUB
          <span className="ml-auto text-[9px]">{PIPELINES.length} · {activeCount} RUNNING</span>
        </div>

        {CATEGORIES.map((cat) => {
          const cardsInCat = PIPELINES.filter((p) => p.category === cat.id);
          if (cardsInCat.length === 0) return null;
          return (
            <section key={cat.id} className="flex flex-col gap-2">
              <SectionTitle text={cat.label} accent={MODULE_COLORS[cat.accent].hex} />
              {cardsInCat.map((p) => (
                <PipelineNode
                  key={p.id}
                  data={{
                    id: p.id,
                    label: p.label,
                    description: p.description,
                    icon: p.icon,
                    colorKey: p.colorKey,
                    totalSteps: p.totalSteps,
                    estimatedSecondsPerStep: p.estimatedSecondsPerStep,
                    steps: p.steps,
                    inputLabel: p.inputLabel,
                    inputValue: inputs[p.id] ?? '',
                    runState: runStates[p.id] ?? initialRunState(),
                    isExpanded: expandedId === p.id,
                    obsidianPath: p.obsidianPath,
                    obsidianVault: OBSIDIAN_VAULT,
                    onInputChange: handleInputChange,
                    onActivate: handleActivate,
                    onToggleExpand: handleToggleExpand,
                  }}
                />
              ))}
            </section>
          );
        })}
      </div>
    </div>
  );
}

// ── Image area (right column, edge-to-edge with subtle sci-fi overlays) ─────

function PipelineImage({ onError }: { onError: () => void }) {
  return (
    <div
      style={{ position: 'absolute', inset: 0, zIndex: 0, overflow: 'hidden', background: 'var(--hud-bg)' }}
    >
      <img
        src={PIPELINE_IMAGE}
        alt="Pipeline Hub"
        onError={onError}
        style={{
          position: 'absolute', inset: 0, width: '100%', height: '100%',
          objectFit: 'cover', objectPosition: 'center', display: 'block',
        }}
      />
      {/* CRT scan lines — amber tint, faint */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute', inset: 0,
          background:
            'repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(245,158,11,0.025) 3px, rgba(245,158,11,0.025) 4px)',
          pointerEvents: 'none', mixBlendMode: 'overlay',
        }}
      />
      {/* Vignette breath */}
      <div className="pipeline-vignette" aria-hidden="true" />
      <style>{`
        @keyframes pipeline-vignette {
          0%, 100% { box-shadow: inset 0 0 90px -10px rgba(0,0,0,0.55); }
          50%      { box-shadow: inset 0 0 130px -4px rgba(0,0,0,0.7);  }
        }
        .pipeline-vignette {
          position: absolute; inset: 0; pointer-events: none;
          animation: pipeline-vignette 11s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

function PipelineImageNotFound() {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 text-center px-6"
      style={{ position: 'absolute', inset: 0, zIndex: 0, color: 'var(--hud-text-dim)', fontFamily: "'IBM Plex Mono', ui-monospace, monospace" }}
    >
      <div className="text-[10px] tracking-[0.3em] font-bold" style={{ color: 'var(--color-security)' }}>
        ◆ PIPELINE IMAGE NOT FOUND
      </div>
      <div className="text-[11px] tracking-wider max-w-md">Expected file:</div>
      <pre
        className="text-[10px] p-3"
        style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.3)', color: 'var(--hud-text)' }}
      >{`frontend/public${PIPELINE_IMAGE}`}</pre>
    </div>
  );
}

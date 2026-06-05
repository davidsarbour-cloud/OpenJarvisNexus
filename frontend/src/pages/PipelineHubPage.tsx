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
  allowImage?: boolean;
}

const OBSIDIAN_VAULT = 'BRAIN';

const PIPELINES: PipelineSpec[] = [
  {
    id: 'stl',
    label: 'STL Pipeline',
    category: 'fabrication',
    description: '3D model · texte OU image → Meshy → repair → export',
    icon: Boxes,
    colorKey: 'forge',
    totalSteps: 11,
    estimatedSecondsPerStep: 12,
    endpoint: '/v1/forge/mission',
    bodyKey: 'prompt',
    inputLabel: 'ex: dragon égyptien stylisé... (ou ajoute une image)',
    allowImage: true,
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

// Bandeau LIVE : affiche la mission forge la plus récente (lancée d'OÙ QUE CE
// SOIT — chat JARVIS, bouton du Hub, auto-factory) avec sa vraie progression.
// Répond au besoin "le Pipeline Hub ne montre pas l'activation".
function ForgeLiveStatus() {
  const [m, setM] = useState<{
    id: string; status?: string; progress_pct?: number; current_step?: string;
    files?: { jarvis_stl?: string; final_stl?: string };
    report?: { printability_score?: number };
  } | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const r = await fetch('/v1/forge/missions');
        if (!r.ok) return;
        const d = await r.json();
        const ms: Array<{ id: string; created_at?: string }> = d.missions ?? [];
        if (!ms.length) { if (alive) setM(null); return; }
        const latest = [...ms].sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))[0];
        const dr = await fetch(`/v1/forge/mission/${latest.id}`);
        if (!dr.ok) return;
        const det = await dr.json();
        if (alive) setM(det);
      } catch { /* transient — retry next tick */ }
    };
    tick();
    const iv = setInterval(tick, 4000);
    return () => { alive = false; clearInterval(iv); };
  }, []);

  if (!m) return null;
  const running = m.status === 'running';
  const done = m.status === 'completed';
  const failed = m.status === 'failed' || m.status === 'error';
  const color = failed ? 'var(--color-cyberdeck)' : done ? 'var(--color-docker)' : MODULE_COLORS.forge.hex;
  const f = m.files?.jarvis_stl ?? m.files?.final_stl ?? '';
  const fname = f ? f.split(/[\\/]/).pop() : '';
  const score = m.report?.printability_score;
  return (
    <div
      className="shrink-0 px-2 py-1.5"
      style={{ background: 'rgba(0,0,0,0.35)', border: `1px solid ${color}`, borderRadius: 4 }}
    >
      <div className="flex items-center gap-1.5 text-[9px]">
        <span style={{ width: 6, height: 6, borderRadius: 1, background: color, boxShadow: `0 0 6px ${color}` }} />
        <span className="font-bold tracking-[0.18em]" style={{ color }}>
          FORGE {running ? `· ${m.progress_pct ?? 0}%` : done ? '· OK' : failed ? '· ERREUR' : ''}
        </span>
        <span className="ml-auto" style={{ color: 'var(--hud-text-dim)' }}>#{m.id}</span>
      </div>
      <div className="mt-0.5 text-[9px] truncate" style={{ color: 'var(--hud-text-dim)' }}>
        {running
          ? `étape: ${m.current_step ?? '?'}`
          : done
            ? (fname ? `STL: ${fname}${score != null ? ` · ${score}/100` : ''}` : 'terminé')
            : failed
              ? 'mission échouée'
              : (m.status ?? '')}
      </div>
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
  const [images, setImages] = useState<Record<string, { dataUri: string; name: string } | null>>({});
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

  const handleImageChange = useCallback(
    (id: string, dataUri: string | null, name: string | null) => {
      setImages((prev) => ({ ...prev, [id]: dataUri && name ? { dataUri, name } : null }));
    },
    [],
  );

  const handleToggleExpand = useCallback((id: string) => {
    setExpandedId((cur) => (cur === id ? null : id));
  }, []);

  const handleActivate = useCallback(
    async (id: string) => {
      const spec = PIPELINES.find((p) => p.id === id);
      if (!spec || !spec.endpoint) return;

      const input = inputs[id]?.trim() ?? '';
      const image = spec.allowImage ? images[id] : null;
      if (spec.inputLabel && !input && !image) {
        setRunStates((prev) => ({
          ...prev,
          [id]: { status: 'error', currentStep: 0, message: 'Texte ou image requis' },
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
        if (image) {
          body.image = image.dataUri;
        }
        // STL : si le prompt mentionne "bambu", ouvrir Bambu Studio à la fin.
        if (spec.id === 'stl' && /\bbambu\b/i.test(input)) {
          body.auto_bambu = true;
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
        type ForgePayload = { ok?: boolean; error?: string; mission_id?: string; poll_url?: string };
        let payload: ForgePayload | null = null;
        try {
          payload = (await res.clone().json()) as ForgePayload;
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

        // Forge/STL renvoie une mission ASYNCHRONE (mission_id + poll_url) qui
        // tourne ~minutes en arrière-plan. On suit le VRAI statut au lieu de
        // mentir "COMPLETED" dès le POST. Les autres pipelines finissent direct.
        if (payload && payload.mission_id) {
          const pollUrl = payload.poll_url ?? `/v1/forge/mission/${payload.mission_id}`;
          const deadline = Date.now() + 15 * 60 * 1000; // garde-fou 15 min
          let settled = false;
          while (!settled && Date.now() < deadline) {
            await new Promise((r) => setTimeout(r, 4000));
            let st:
              | {
                  status?: string; progress_pct?: number; error?: string;
                  files?: { jarvis_stl?: string; final_stl?: string };
                  report?: { printability_score?: number };
                }
              | null = null;
            try {
              const pr = await fetch(pollUrl);
              if (pr.ok) st = await pr.json();
            } catch {
              /* transient — retry next tick */
            }

            if (st?.status === 'completed') {
              const f = st.files?.jarvis_stl ?? st.files?.final_stl ?? '';
              const fname = f ? f.split(/[\\/]/).pop() : '';
              const score = st.report?.printability_score;
              setRunStates((prev) => ({
                ...prev,
                [id]: {
                  status: 'done', currentStep: spec.totalSteps, startedAt, finishedAt: Date.now(),
                  message: fname
                    ? `STL prêt: ${fname}${score != null ? ` · ${score}/100` : ''}`
                    : 'Terminé',
                },
              }));
              settled = true;
            } else if (st?.status === 'failed' || st?.status === 'error') {
              setRunStates((prev) => ({
                ...prev,
                [id]: {
                  status: 'error', currentStep: prev[id]?.currentStep ?? 0,
                  startedAt, finishedAt: Date.now(), message: st?.error ?? 'mission échouée',
                },
              }));
              settled = true;
            } else {
              const pct = typeof st?.progress_pct === 'number' ? st.progress_pct : 0;
              const step = Math.min(spec.totalSteps - 1, Math.round((pct / 100) * spec.totalSteps));
              setRunStates((prev) => {
                const cur = prev[id];
                if (!cur || cur.status !== 'running') return prev;
                return { ...prev, [id]: { ...cur, currentStep: step } };
              });
            }
          }
          if (!settled) {
            setRunStates((prev) => ({
              ...prev,
              [id]: {
                status: 'done', currentStep: spec.totalSteps, startedAt, finishedAt: Date.now(),
                message: 'Toujours en cours (timeout suivi) — vérifie le dossier STL',
              },
            }));
          }
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
    [inputs, images, stopTicker],
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
          position: 'absolute', left: 16, top: 16, bottom: 16, zIndex: 2,
          width: DOCK_WIDTH,
          overflowY: 'auto',
          padding: 16,
          background: 'rgba(2,4,12,0.58)',
          backdropFilter: 'blur(3px)',
          border: '1px solid var(--hud-border)',
          borderRadius: 8,
          display: 'flex',
          flexDirection: 'column',
          gap: 18,
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

        <ForgeLiveStatus />

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
                    allowImage: p.allowImage,
                    imageName: images[p.id]?.name ?? null,
                    onInputChange: handleInputChange,
                    onActivate: handleActivate,
                    onToggleExpand: handleToggleExpand,
                    onImageChange: handleImageChange,
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

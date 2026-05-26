import { motion, AnimatePresence } from 'motion/react';
import { Play, Loader2, Check, AlertTriangle, ChevronDown, Circle, BookOpen } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ModuleKey } from '../../lib/colors';
import { cssVar, MODULE_COLORS } from '../../lib/colors';

export type PipelineRunStatus = 'idle' | 'running' | 'done' | 'error';

export interface PipelineRunState {
  status: PipelineRunStatus;
  currentStep: number;
  startedAt?: number;
  finishedAt?: number;
  message?: string;
}

export interface PipelineNodeData {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
  colorKey: ModuleKey;
  totalSteps: number;
  estimatedSecondsPerStep: number;
  steps: string[];
  inputLabel?: string;
  inputValue: string;
  runState: PipelineRunState;
  isExpanded: boolean;
  obsidianPath?: string;
  obsidianVault?: string;
  onInputChange: (id: string, v: string) => void;
  onActivate: (id: string) => void;
  onToggleExpand: (id: string) => void;
}

const STATUS_DOT: Record<PipelineRunStatus, string> = {
  idle: 'var(--hud-text-dim)',
  running: 'var(--color-jarvis)',
  done: 'var(--color-docker)',
  error: 'var(--color-cyberdeck)',
};

function fmtElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
}

export function PipelineNode({ data }: { data: PipelineNodeData }) {
  if (!data) return null;

  const c = cssVar(data.colorKey);
  const glow = MODULE_COLORS[data.colorKey]?.glow ?? 'rgba(0,212,255,0.4)';
  const Icon = data.icon;

  const { runState, isExpanded } = data;
  const isRunning = runState.status === 'running';
  const isDone = runState.status === 'done';
  const isError = runState.status === 'error';
  const dot = STATUS_DOT[runState.status];

  // TODO: switch to a useNow()/useSyncExternalStore tick hook so the elapsed
  // counter re-renders on a schedule instead of relying on parent re-renders
  // — would also satisfy react-hooks/purity properly.
  /* eslint-disable react-hooks/purity */
  const elapsedMs = runState.startedAt
    ? (runState.finishedAt ?? Date.now()) - runState.startedAt
    : 0;
  /* eslint-enable react-hooks/purity */
  const totalEstMs = data.totalSteps * data.estimatedSecondsPerStep * 1000;
  const remainingMs = Math.max(0, totalEstMs - elapsedMs);
  const progressPct = data.totalSteps > 0
    ? Math.min(100, (runState.currentStep / data.totalSteps) * 100)
    : 0;

  return (
    <motion.div
      onClick={() => data.onToggleExpand(data.id)}
      whileHover={{ scale: 1.015 }}
      transition={{ type: 'spring', stiffness: 320, damping: 22 }}
      style={{
        background: 'rgba(2,5,11,0.92)',
        border: `1px solid ${c}`,
        borderTop: `2px solid ${c}`,
        boxShadow: `inset 0 0 16px rgba(0,0,0,0.5), 0 0 ${isExpanded ? 24 : 14}px -4px ${glow}`,
        padding: '12px 14px',
        width: '100%',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
        color: 'var(--hud-text)',
        position: 'relative',
        cursor: 'pointer',
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <motion.span
          aria-hidden
          animate={isRunning ? { opacity: [1, 0.3, 1] } : { opacity: 1 }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: 1,
            background: dot,
            boxShadow: `0 0 6px ${dot}`,
          }}
        />
        <Icon size={12} style={{ color: c }} />
        <span className="text-[10px] font-bold tracking-[0.22em]" style={{ color: c }}>
          {data.label.toUpperCase()}
        </span>
        <span className="ml-auto text-[9px]" style={{ color: 'var(--hud-text-dim)' }}>
          {data.totalSteps} STEPS
        </span>
        {data.obsidianPath && (
          <button
            className="nodrag"
            onClick={(e) => {
              e.stopPropagation();
              const vault = data.obsidianVault ?? 'BRAIN';
              const url = `obsidian://open?vault=${encodeURIComponent(vault)}&file=${encodeURIComponent(
                data.obsidianPath!,
              )}`;
              window.open(url, '_self');
            }}
            title={`Open in Obsidian → ${data.obsidianPath}`}
            style={{
              padding: 2,
              background: 'transparent',
              border: 'none',
              color: 'var(--hud-text-dim)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              transition: 'color 0.15s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = c)}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
          >
            <BookOpen size={12} />
          </button>
        )}
        <ChevronDown
          size={11}
          style={{
            color: 'var(--hud-text-dim)',
            transform: isExpanded ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.2s',
          }}
        />
      </div>

      <div className="text-[9px] tracking-wider mb-2" style={{ color: 'var(--hud-text-dim)' }}>
        {data.description}
      </div>

      {data.inputLabel && (
        <input
          type="text"
          value={data.inputValue}
          onChange={(e) => data.onInputChange(data.id, e.target.value)}
          placeholder={data.inputLabel}
          disabled={isRunning}
          className="nodrag w-full mb-1.5 px-2 py-1 text-[10px] outline-none rounded-sm"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--hud-border)',
            color: 'var(--hud-text)',
            fontFamily: 'inherit',
          }}
          onClick={(e) => e.stopPropagation()}
        />
      )}

      <button
        onClick={(e) => {
          e.stopPropagation();
          if (!isRunning) data.onActivate(data.id);
        }}
        disabled={isRunning}
        className="nodrag w-full flex items-center justify-center gap-1.5 px-2 py-1.5 text-[10px] font-bold tracking-[0.18em] rounded-sm transition-colors"
        style={{
          background: isRunning ? 'rgba(255,255,255,0.04)' : c,
          color: isRunning ? c : '#000',
          border: `1px solid ${c}`,
          opacity: isRunning ? 0.7 : 1,
          cursor: isRunning ? 'not-allowed' : 'pointer',
        }}
      >
        {isRunning ? (
          <>
            <Loader2 size={11} className="animate-spin" />
            RUNNING
          </>
        ) : isDone ? (
          <>
            <Check size={11} />
            COMPLETED · RUN AGAIN
          </>
        ) : isError ? (
          <>
            <AlertTriangle size={11} />
            FAILED · RETRY
          </>
        ) : (
          <>
            <Play size={11} />
            ACTIVATE
          </>
        )}
      </button>

      {(isRunning || isDone) && (
        <div className="mt-2">
          <div className="flex justify-between text-[9px] mb-0.5" style={{ color: 'var(--hud-text-dim)' }}>
            <span>STEP {runState.currentStep}/{data.totalSteps}</span>
            <span>
              {isRunning
                ? `${fmtElapsed(elapsedMs)} · ~${fmtElapsed(remainingMs)} LEFT`
                : fmtElapsed(elapsedMs)}
            </span>
          </div>
          <div
            style={{
              height: 3,
              background: 'rgba(255,255,255,0.05)',
              borderRadius: 1,
              overflow: 'hidden',
            }}
          >
            <motion.div
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              style={{
                height: '100%',
                background: c,
                boxShadow: `0 0 8px ${glow}`,
              }}
            />
          </div>
        </div>
      )}

      {isError && runState.message && (
        <div className="mt-1.5 text-[9px]" style={{ color: 'var(--color-cyberdeck)' }}>
          {runState.message}
        </div>
      )}

      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--hud-border)' }}>
              <div
                className="text-[10px] font-bold tracking-[0.2em] mb-2"
                style={{ color: 'var(--hud-text-dim)' }}
              >
                STEPS
              </div>
              <div className="flex flex-col gap-0.5">
                {data.steps.map((step, i) => {
                  const stepIdx = i + 1;
                  const isDoneStep = isDone || (isRunning && stepIdx <= runState.currentStep);
                  const isActiveStep = isRunning && stepIdx === runState.currentStep + 1;
                  const isPendingStep = !isDoneStep && !isActiveStep;
                  return (
                    <div
                      key={i}
                      className="flex items-start gap-2 text-[16px]"
                      style={{
                        lineHeight: 1.35,
                        background: isActiveStep
                          ? MODULE_COLORS[data.colorKey].subtle
                          : 'transparent',
                        borderLeft: isActiveStep
                          ? `2px solid ${c}`
                          : '2px solid transparent',
                        paddingLeft: 6,
                        paddingTop: 3,
                        paddingBottom: 3,
                        borderRadius: 2,
                      }}
                    >
                      <span
                        style={{
                          width: 18,
                          display: 'inline-flex',
                          justifyContent: 'center',
                          alignItems: 'center',
                          paddingTop: 3,
                          flexShrink: 0,
                        }}
                      >
                        {isActiveStep ? (
                          <Loader2 size={16} className="animate-spin" style={{ color: c }} />
                        ) : isDoneStep ? (
                          <Check size={16} style={{ color: 'var(--color-docker)' }} />
                        ) : (
                          <Circle size={11} style={{ color: 'var(--hud-text-dim)', opacity: 0.5 }} />
                        )}
                      </span>
                      <span
                        style={{
                          color: isPendingStep
                            ? 'var(--hud-text-dim)'
                            : isActiveStep
                              ? c
                              : 'var(--hud-text)',
                          opacity: isPendingStep ? 0.55 : 1,
                          fontFamily: 'inherit',
                          fontWeight: isActiveStep ? 600 : 400,
                        }}
                      >
                        <span style={{ opacity: 0.55 }}>
                          {String(stepIdx).padStart(2, '0')}.
                        </span>{' '}
                        {step}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/**
 * Nexus9 — AgentDetailPanel.
 *
 * Slide-in right-edge panel that appears when an agent node is clicked
 * in AgentNetworkPage. Shows:
 *   - Big circular "avatar" themed by the agent's ModuleKey (no real
 *     photo asset needed — uses Lucide icon + accent palette so the
 *     visual stays consistent with the rest of the HUD).
 *   - Name + status pill (online / idle / offline)
 *   - Role + provider + model
 *   - Description block (free text from /v1/agents)
 *
 * Closed via the X button, by clicking outside the panel, or by hitting Esc.
 */
import { useEffect } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { X, type LucideIcon } from 'lucide-react';
import {
  Cpu, Brain, Hammer, Atom, Code2,
  ShoppingBag, Workflow, Lock, Sparkles,
} from 'lucide-react';
import { MODULE_COLORS, type ModuleKey } from '../../lib/colors';
import type { AgentInfo } from '../../lib/apiLive';

const STATUS_COLOR: Record<string, string> = {
  online:  'var(--color-docker)',
  idle:    'var(--color-security)',
  offline: 'var(--color-cyberdeck)',
};

const STATUS_LABEL: Record<string, string> = {
  online:  'ONLINE',
  idle:    'IDLE',
  offline: 'OFFLINE',
  active:  'ACTIVE',
};

/** Agent identifier → Lucide icon used as the avatar centerpiece. */
const AGENT_ICON: Record<string, LucideIcon> = {
  jarvis:  Cpu,
  ultron:  Brain,
  qwen:    Sparkles,
  cortana: Code2,
  bruce:   Workflow,
  nova:    Atom,
  forge:   Hammer,
  kaizen:  Hammer,
  vault:   Lock,
  etsy:    ShoppingBag,
};

interface AgentDetailPanelProps {
  agent: AgentInfo | null;
  colorKey: ModuleKey;
  onClose: () => void;
}

export function AgentDetailPanel({ agent, colorKey, onClose }: AgentDetailPanelProps) {
  // Close on Esc.
  useEffect(() => {
    if (!agent) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [agent, onClose]);

  const color = MODULE_COLORS[colorKey];
  const accent = color.hex;
  const glow   = color.glow;
  const subtle = color.subtle;
  const Icon   = (agent && AGENT_ICON[agent.id]) || Cpu;
  const statusKey = (agent?.status ?? 'offline').toLowerCase();
  const statusColor = STATUS_COLOR[statusKey] ?? 'var(--hud-text-dim)';
  const statusLabel = STATUS_LABEL[statusKey] ?? statusKey.toUpperCase();

  return (
    <AnimatePresence>
      {agent && (
        <>
          {/* Click-out backdrop. Subtle so the graph stays visible. */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            onClick={onClose}
            className="absolute inset-0 z-20"
            style={{ background: 'rgba(0,0,0,0.30)', backdropFilter: 'blur(1px)' }}
            aria-hidden
          />

          <motion.aside
            key="panel"
            role="dialog"
            aria-label={`Agent ${agent.name}`}
            initial={{ x: 360, opacity: 0 }}
            animate={{ x: 0,    opacity: 1 }}
            exit={{    x: 360, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="absolute top-0 right-0 bottom-0 z-30 flex flex-col"
            style={{
              width: 360,
              background: 'linear-gradient(180deg, rgba(2,5,11,0.97) 0%, rgba(2,5,11,0.92) 100%)',
              borderLeft: `1px solid ${accent}`,
              boxShadow: `-12px 0 36px -16px ${glow}, inset 8px 0 28px -18px ${glow}`,
              fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
            }}
          >
            {/* Top bar with close button */}
            <header className="flex items-center justify-between px-4 py-2 shrink-0"
                    style={{ borderBottom: '1px solid var(--hud-border)' }}>
              <span className="text-[9px] font-bold tracking-[0.3em]"
                    style={{ color: 'var(--hud-text-dim)' }}>
                ◆ AGENT DETAIL
              </span>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close agent detail"
                className="flex items-center justify-center rounded transition-colors"
                style={{
                  width: 22, height: 22,
                  color: 'var(--hud-text-dim)',
                  background: 'transparent',
                  border: '1px solid var(--hud-border)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = 'var(--color-cyberdeck)';
                  e.currentTarget.style.borderColor = 'var(--color-cyberdeck)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = 'var(--hud-text-dim)';
                  e.currentTarget.style.borderColor = 'var(--hud-border)';
                }}
              >
                <X size={12} />
              </button>
            </header>

            {/* Scroll area */}
            <div className="flex-1 overflow-y-auto px-5 py-5 flex flex-col gap-4">
              {/* Avatar — big themed disk */}
              <div className="flex flex-col items-center gap-3">
                <div
                  className="relative flex items-center justify-center rounded-full"
                  style={{
                    width: 120, height: 120,
                    background: `radial-gradient(circle at 30% 30%, ${subtle} 0%, rgba(0,0,0,0.6) 90%)`,
                    border: `2px solid ${accent}`,
                    boxShadow: `0 0 36px -6px ${glow}, inset 0 0 24px -8px ${glow}`,
                  }}
                >
                  <Icon size={56} color={accent} strokeWidth={1.5} />
                  {/* Pulsing status ring at bottom-right */}
                  <span
                    className="absolute rounded-full"
                    style={{
                      right: 6, bottom: 6,
                      width: 16, height: 16,
                      background: statusColor,
                      boxShadow: `0 0 10px ${statusColor}`,
                      border: '2px solid rgba(2,5,11,0.9)',
                      animation: statusKey === 'online' ? 'agent-status-pulse 1.6s ease-in-out infinite' : 'none',
                    }}
                  />
                </div>
                <style>{`
                  @keyframes agent-status-pulse {
                    0%, 100% { transform: scale(1);   opacity: 1;   }
                    50%      { transform: scale(1.2); opacity: 0.6; }
                  }
                `}</style>

                <div className="text-base font-bold tracking-[0.3em]"
                     style={{ color: accent, textShadow: `0 0 12px ${glow}` }}>
                  {agent.name}
                </div>
                <div
                  className="px-2 py-0.5 text-[9px] tracking-[0.22em] rounded"
                  style={{
                    color: statusColor,
                    border: `1px solid ${statusColor}`,
                    background: 'rgba(0,0,0,0.4)',
                  }}
                >
                  ● {statusLabel}
                </div>
              </div>

              <DetailRow label="ROLE"     value={agent.role || '—'} />
              <DetailRow label="PROVIDER" value={agent.provider || '—'} />
              <DetailRow label="MODEL"    value={agent.model || '—'} mono />

              {agent.description && (
                <div className="flex flex-col gap-1.5">
                  <div className="text-[8px] tracking-[0.3em]"
                       style={{ color: 'var(--hud-text-dim)' }}>
                    DESCRIPTION
                  </div>
                  <div
                    className="px-3 py-2 text-[11px] leading-relaxed"
                    style={{
                      color: 'var(--hud-text)',
                      background: 'rgba(255,255,255,0.018)',
                      border: '1px solid var(--hud-border)',
                      borderLeft: `2px solid ${accent}`,
                      borderRadius: 3,
                    }}
                  >
                    {agent.description}
                  </div>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="text-[8px] tracking-[0.3em]" style={{ color: 'var(--hud-text-dim)' }}>
        {label}
      </div>
      <div
        className={`text-[11px] ${mono ? 'tracking-wider' : 'tracking-wide'}`}
        style={{
          color: 'var(--hud-text)',
          fontFamily: mono ? "'IBM Plex Mono', ui-monospace, monospace" : undefined,
          wordBreak: 'break-word',
        }}
      >
        {value}
      </div>
    </div>
  );
}

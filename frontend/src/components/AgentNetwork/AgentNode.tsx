/**
 * Nexus9 — AgentNode (custom React Flow node).
 *
 * v12 of @xyflow/react expects nodes to use the NodeProps<TNode> type
 * where TNode is a Node<TData>. The previous looser signature
 * `{ data }: { data: T }` would crash at runtime when React Flow tried
 * to pass extra props (isConnectable, selected, etc.) through.
 */
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { motion } from 'motion/react';
import type { ModuleKey } from '../../lib/colors';
import { cssVar, MODULE_COLORS } from '../../lib/colors';

export type AgentNodeData = {
  label: string;
  role: string;
  model: string;
  colorKey: ModuleKey;
  status: 'online' | 'idle' | 'offline' | string;
  isCore?: boolean;
};

// Concrete node type required by xyflow v12 generic NodeProps.
export type AgentFlowNode = Node<AgentNodeData, 'agent'>;

const DOT_COLOR: Record<string, string> = {
  online:  'var(--color-docker)',
  idle:    'var(--color-security)',
  offline: 'var(--color-cyberdeck)',
};

export function AgentNode({ data }: NodeProps<AgentFlowNode>) {
  // Defensive: in some edge cases (initial paint) data can be partial.
  if (!data) return null;

  const c = cssVar(data.colorKey);
  const glow = MODULE_COLORS[data.colorKey]?.glow ?? 'rgba(0,212,255,0.4)';
  const dot = DOT_COLOR[data.status] ?? 'var(--hud-text-dim)';
  const isCore = !!data.isCore;

  return (
    <motion.div
      whileHover={{ scale: 1.04 }}
      transition={{ type: 'spring', stiffness: 320, damping: 22 }}
      style={{
        background: 'rgba(2,5,11,0.92)',
        border: `1px solid ${c}`,
        borderTop: `2px solid ${c}`,
        boxShadow: `inset 0 0 16px rgba(0,0,0,0.5), 0 0 ${isCore ? 28 : 14}px -4px ${glow}`,
        padding: isCore ? '14px 16px' : '10px 12px',
        minWidth: isCore ? 180 : 150,
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
        color: 'var(--hud-text)',
        position: 'relative',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />

      <div className="flex items-center gap-2 mb-1">
        <motion.span
          aria-hidden
          animate={
            data.status === 'online'
              ? { opacity: [1, 0.3, 1] }
              : { opacity: 1 }
          }
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: 1,
            background: dot,
            boxShadow: `0 0 6px ${dot}`,
          }}
        />
        <span
          className="text-[10px] font-bold tracking-[0.22em]"
          style={{ color: c }}
        >
          {(data.label || '').toUpperCase()}
        </span>
      </div>

      <div
        className="text-[9px] tracking-wider mb-0.5"
        style={{ color: 'var(--hud-text-dim)' }}
      >
        {data.role}
      </div>

      <div
        className="text-[9px] truncate"
        style={{ color: 'var(--hud-text-dim)', opacity: 0.7 }}
        title={data.model}
      >
        {data.model}
      </div>
    </motion.div>
  );
}

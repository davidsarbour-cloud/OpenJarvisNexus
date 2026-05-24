import { useAppStore } from '../lib/store';
import { ChatArea } from '../components/Chat/ChatArea';
import { SystemPanel } from '../components/Chat/SystemPanel';

/**
 * ChatPage — layout:
 *
 *   ┌────────────────┬──────────────────────────────────┐
 *   │                │                                  │
 *   │  Jarvis Logo   │   Chat messages + input          │
 *   │  (animated,    │   (scrollable history,           │
 *   │   pulses when  │    streaming, tool calls…)       │
 *   │   talking)     │                                  │
 *   └────────────────┴──────────────────────────────────┘
 *
 * The conversations sidebar is provided by the parent <Layout>.
 */
export function ChatPage() {
  const systemPanelOpen = useAppStore((s) => s.systemPanelOpen);

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Center: Jarvis animated logo ─── */}
      <div
        className="flex items-center justify-center shrink-0"
        style={{
          width: 260,
          borderRight: '1px solid var(--color-border)',
          background: 'var(--color-bg)',
        }}
      >
        <JarvisLogo />
      </div>

      {/* ── Right: chat messages + input ─── */}
      <div className="flex-1 min-w-0 flex overflow-hidden">
        <div className="flex-1 min-w-0">
          <ChatArea />
        </div>
        {systemPanelOpen && <SystemPanel />}
      </div>
    </div>
  );
}

// ─── Animated Jarvis logo ──────────────────────────────────────────────────

function JarvisLogo() {
  const isStreaming = useAppStore((s) => s.streamState.isStreaming);
  const phase       = useAppStore((s) => s.streamState.phase);

  /* Ring durations — faster when talking */
  const d1 = isStreaming ? '2.5s'  : '10s';
  const d2 = isStreaming ? '1.8s'  : '7s';
  const d3 = isStreaming ? '1.1s'  : '4.5s';

  const dPulse = isStreaming
    ? 'jarvis-pulse 0.75s ease-in-out infinite'
    : 'jarvis-breathe 3.2s ease-in-out infinite';
  const dGlow = isStreaming
    ? 'jarvis-glow-talk 0.75s ease-in-out infinite'
    : 'jarvis-glow-fade 3.2s ease-in-out infinite';

  const statusLabel = isStreaming ? (phase || 'PROCESSING') : 'JARVIS · ONLINE';
  const subLabel    = isStreaming ? '◆ TRANSMITTING'        : '● REACTOR STABLE';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 24,
        userSelect: 'none',
        padding: '0 16px',
      }}
    >
      {/* ── Orb ─────────────────────── */}
      <div style={{ position: 'relative', width: 180, height: 180 }}>

        {/* Outermost dashed ring */}
        <div style={{
          position: 'absolute', inset: 0,
          borderRadius: '50%',
          border: '1px dashed rgba(0,212,255,0.18)',
          animation: `jarvis-spin-cw ${d1} linear infinite`,
        }} />

        {/* Outer ring */}
        <div style={{
          position: 'absolute', inset: '7%',
          borderRadius: '50%',
          border: '1px solid rgba(0,212,255,0.28)',
          borderTopColor: 'rgba(0,212,255,0.7)',
          animation: `jarvis-spin-ccw ${d2} linear infinite`,
        }} />

        {/* Mid ring */}
        <div style={{
          position: 'absolute', inset: '18%',
          borderRadius: '50%',
          border: '1px solid rgba(0,212,255,0.22)',
          borderBottomColor: 'rgba(0,212,255,0.65)',
          borderRightColor: 'rgba(0,212,255,0.5)',
          animation: `jarvis-spin-cw ${d3} linear infinite`,
        }} />

        {/* Inner ring */}
        <div style={{
          position: 'absolute', inset: '28%',
          borderRadius: '50%',
          border: `1px solid rgba(0,212,255,${isStreaming ? 0.75 : 0.4})`,
          animation: `jarvis-spin-ccw ${d3} linear infinite`,
        }} />

        {/* Corona halo */}
        <div style={{
          position: 'absolute', inset: '28%',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,212,255,0.3) 0%, transparent 70%)',
          filter: 'blur(8px)',
          animation: dGlow,
        }} />

        {/* Plasma core */}
        <div style={{
          position: 'absolute', inset: '33%',
          borderRadius: '50%',
          background: 'radial-gradient(circle at 38% 35%, #c8f8ff 0%, #00d4ff 35%, #0055cc 80%, #001244 100%)',
          animation: `${dPulse}, ${dGlow}`,
        }} />
      </div>

      {/* ── Status text ─────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5 }}>
        <div style={{
          fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: '0.28em',
          color: '#00d4ff',
          textShadow: '0 0 12px rgba(0,212,255,0.65)',
          animation: isStreaming ? 'jarvis-text-flicker 4s linear infinite' : undefined,
          textAlign: 'center',
        }}>
          {statusLabel}
        </div>
        <div style={{
          fontSize: 8,
          letterSpacing: '0.25em',
          color: 'var(--color-text-tertiary)',
          textAlign: 'center',
        }}>
          {subLabel}
        </div>
      </div>
    </div>
  );
}

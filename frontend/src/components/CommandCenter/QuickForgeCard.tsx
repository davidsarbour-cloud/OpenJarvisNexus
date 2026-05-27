/**
 * QuickForgeCard — quick-launcher to fire an STL Forge mission directly
 * from a docked card without having to navigate elsewhere.
 *
 * UX:
 *   ┌──────────────────────────────┐
 *   │ ◆ QUICK FORGE      [dot]     │
 *   │ Launch STL mission           │
 *   │                              │
 *   │ ┌─────────────────────────┐  │
 *   │ │ describe the STL...     │  │
 *   │ └─────────────────────────┘  │
 *   │ [ LAUNCH MISSION → ]         │
 *   │                              │
 *   │ last: M-20260527-…  ok       │
 *   └──────────────────────────────┘
 *
 * Wired to backend POST /v1/forge/mission with default engine="auto" and
 * target_size_mm=150. Optimistically shows the returned mission_id and
 * polls /v1/forge/mission/{id} once to surface initial status.
 */
import { useContext, useState } from 'react';
import { Hammer } from 'lucide-react';
import { CardAccentContext } from './HudCard';
import { cssVar, MODULE_COLORS } from '../../lib/colors';
import type { ModuleKey } from '../../lib/colors';

interface LastMission {
  id:     string;
  status: string;
  ts:     number;
}

export function QuickForgeCard() {
  const ctxAccent = useContext(CardAccentContext);
  const colorKey: ModuleKey = ctxAccent ?? 'forge';
  const c     = cssVar(colorKey);
  const glow  = MODULE_COLORS[colorKey].glow;

  const [prompt,  setPrompt]  = useState('');
  const [sending, setSending] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [last,    setLast]    = useState<LastMission | null>(null);

  const submit = async () => {
    const p = prompt.trim();
    if (!p || sending) return;
    setSending(true);
    setError(null);
    try {
      const r = await fetch('/v1/forge/mission', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          prompt:         p,
          engine:         'auto',
          target_size_mm: 150,
          auto_repair:    true,
          auto_orient:    true,
          auto_bambu:     false,
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      setLast({ id: String(j.mission_id ?? '?'), status: String(j.status ?? 'running'), ts: Date.now() });
      setPrompt('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed');
    } finally {
      setSending(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl+Enter or Cmd+Enter → submit (textarea so plain Enter inserts newline)
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submit();
    }
  };

  const canSend = prompt.trim().length > 0 && !sending;

  return (
    <div
      className="flex flex-col p-3 relative"
      style={{
        background: 'var(--hud-bg-elev)',
        border: '1px solid var(--hud-border)',
        borderTop: `2px solid ${c}`,
        boxShadow: 'inset 0 0 24px rgba(0,0,0,0.4)',
        minHeight: 140,
        height: '100%',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
      {/* Status dot — green when idle, amber when sending */}
      <span
        aria-label="Quick Forge status"
        title={sending ? 'sending' : error ? 'error' : 'idle'}
        className="absolute"
        style={{
          top: 8,
          right: 8,
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: error ? '#000' : c,
          boxShadow: `0 0 6px ${error ? 'rgba(0,0,0,0.8)' : glow}`,
          border: error ? '1px solid var(--hud-border)' : 'none',
        }}
      />

      {/* Header */}
      <div className="flex items-center gap-2 mb-0.5">
        <Hammer size={14} style={{ color: c }} />
        <span className="text-[10px] font-bold tracking-[0.22em]" style={{ color: c }}>
          QUICK FORGE
        </span>
      </div>
      <div className="text-[9px] tracking-wider mb-2" style={{ color: 'var(--hud-text-dim)' }}>
        Launch STL mission · Ctrl+Enter
      </div>

      {/* Input + button */}
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="describe the STL: ex. low-poly dragon 150mm..."
        spellCheck={false}
        disabled={sending}
        style={{
          width:      '100%',
          minHeight:  56,
          flex:       1,
          padding:    '6px 8px',
          background: 'rgba(0,0,0,0.45)',
          border:     `1px solid ${c}`,
          color:      'var(--hud-text)',
          fontFamily: 'inherit',
          fontSize:   11,
          lineHeight: 1.35,
          resize:     'none',
          outline:    'none',
          marginBottom: 6,
        }}
      />

      <button
        onClick={submit}
        disabled={!canSend}
        style={{
          width:      '100%',
          padding:    '6px 10px',
          background: canSend ? c : 'rgba(255,255,255,0.05)',
          border:     `1px solid ${c}`,
          color:      canSend ? '#000' : 'var(--hud-text-dim)',
          fontFamily: 'inherit',
          fontSize:   10,
          letterSpacing: '0.22em',
          fontWeight: 700,
          cursor:     canSend ? 'pointer' : 'not-allowed',
          transition: 'background 0.15s, color 0.15s',
        }}
      >
        {sending ? 'LAUNCHING…' : 'LAUNCH MISSION →'}
      </button>

      {/* Footer: last mission / error */}
      <div className="mt-2 text-[9px] tracking-wider" style={{ minHeight: 12 }}>
        {error ? (
          <span style={{ color: '#ff6b6b' }}>! {error}</span>
        ) : last ? (
          <span style={{ color: 'var(--hud-text-dim)' }}>
            last:&nbsp;
            <span style={{ color: c }}>{last.id}</span>
            &nbsp;·&nbsp;
            <span style={{ color: 'var(--hud-text)' }}>{last.status}</span>
          </span>
        ) : (
          <span style={{ color: 'var(--hud-text-dim)', opacity: 0.55 }}>
            no mission launched yet
          </span>
        )}
      </div>
    </div>
  );
}

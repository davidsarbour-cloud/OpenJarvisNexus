/**
 * ValkyrieGenerateCard — fire an OpenAI gpt-image-1 generation inline.
 *
 * UX:
 *   ┌──────────────────────────────┐
 *   │ ✶ VALKYRIE         [dot]      │
 *   │ Generate · gpt-image-1        │
 *   │ ┌─────────────────────────┐  │
 *   │ │ describe the image...   │  │
 *   │ └─────────────────────────┘  │
 *   │ [ size ▾ ] [ quality ▾ ]     │
 *   │ [ GENERATE → ]               │
 *   │ ▣ thumb  ·  3.1s · ~$0.167   │
 *   └──────────────────────────────┘
 *
 * Wired to POST /v1/valkyrie/generate {prompt, size, quality, n}.
 * On success it emits a `valkyrie:generated` window event so the gallery
 * card auto-refreshes, and previews the freshly generated image.
 */
import { useContext, useState } from 'react';
import { Wand2 } from 'lucide-react';
import { CardAccentContext } from './HudCard';
import { cssVar, MODULE_COLORS } from '../../lib/colors';
import type { ModuleKey } from '../../lib/colors';
import { getBase } from '../../lib/api';

interface GenImage { name: string; url: string }
interface GenResult {
  images: GenImage[];
  count: number;
  elapsed_s: number;
  estimated_cost_usd: number;
}

const SIZES = [
  { value: '1024x1024', label: 'Carré 1024²' },
  { value: '1536x1024', label: 'Paysage' },
  { value: '1024x1536', label: 'Portrait' },
  { value: 'auto',      label: 'Auto' },
];
const QUALITIES = [
  { value: 'low',    label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high',   label: 'High' },
  { value: 'auto',   label: 'Auto' },
];

export function ValkyrieGenerateCard() {
  const ctxAccent = useContext(CardAccentContext);
  const colorKey: ModuleKey = ctxAccent ?? 'valkyrie';
  const c    = cssVar(colorKey);
  const glow = MODULE_COLORS[colorKey].glow;

  const [prompt,  setPrompt]  = useState('');
  const [size,    setSize]    = useState('1024x1024');
  const [quality, setQuality] = useState('high');
  const [sending, setSending] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [result,  setResult]  = useState<GenResult | null>(null);

  const base = getBase();
  const canSend = prompt.trim().length > 0 && !sending;

  const submit = async () => {
    const p = prompt.trim();
    if (!p || sending) return;
    setSending(true);
    setError(null);
    try {
      const r = await fetch(`${base}/v1/valkyrie/generate`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ prompt: p, size, quality, n: 1 }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({ detail: `HTTP ${r.status}` }));
        throw new Error(typeof j.detail === 'string' ? j.detail : `HTTP ${r.status}`);
      }
      const j: GenResult = await r.json();
      setResult(j);
      window.dispatchEvent(new CustomEvent('valkyrie:generated'));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed');
    } finally {
      setSending(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit(); }
  };

  const selectStyle: React.CSSProperties = {
    flex: 1, minWidth: 0, padding: '4px 6px',
    background: 'rgba(0,0,0,0.45)', border: `1px solid ${c}`,
    color: 'var(--hud-text)', fontFamily: 'inherit', fontSize: 10, outline: 'none',
  };

  const last = result?.images?.[0];

  return (
    <div
      className="flex flex-col p-3 relative"
      style={{
        background: 'var(--hud-bg-elev)',
        border: '1px solid var(--hud-border)',
        borderTop: `2px solid ${c}`,
        boxShadow: 'inset 0 0 24px rgba(0,0,0,0.4)',
        minHeight: 200,
        height: '100%',
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      }}
    >
      {/* Status dot */}
      <span
        aria-label="Valkyrie status"
        title={sending ? 'generating' : error ? 'error' : 'idle'}
        className="absolute"
        style={{
          top: 8, right: 8, width: 7, height: 7, borderRadius: '50%',
          background: error ? '#000' : c,
          boxShadow: `0 0 6px ${error ? 'rgba(0,0,0,0.8)' : glow}`,
          border: error ? '1px solid var(--hud-border)' : 'none',
        }}
      />

      {/* Header */}
      <div className="flex items-center gap-2 mb-0.5">
        <Wand2 size={14} style={{ color: c }} />
        <span className="text-[10px] font-bold tracking-[0.22em]" style={{ color: c }}>
          VALKYRIE
        </span>
      </div>
      <div className="text-[9px] tracking-wider mb-2" style={{ color: 'var(--hud-text-dim)' }}>
        Generate · gpt-image-1 · Ctrl+Enter
      </div>

      {/* Prompt */}
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="describe the image: ex. dragon figurine product shot, studio light..."
        spellCheck={false}
        disabled={sending}
        style={{
          width: '100%', minHeight: 56, flex: 1, padding: '6px 8px',
          background: 'rgba(0,0,0,0.45)', border: `1px solid ${c}`,
          color: 'var(--hud-text)', fontFamily: 'inherit', fontSize: 11,
          lineHeight: 1.35, resize: 'none', outline: 'none', marginBottom: 6,
        }}
      />

      {/* Size + quality */}
      <div className="flex gap-1.5 mb-1.5">
        <select value={size} onChange={(e) => setSize(e.target.value)} disabled={sending} style={selectStyle}>
          {SIZES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <select value={quality} onChange={(e) => setQuality(e.target.value)} disabled={sending} style={selectStyle}>
          {QUALITIES.map((q) => <option key={q.value} value={q.value}>{q.label}</option>)}
        </select>
      </div>

      <button
        onClick={submit}
        disabled={!canSend}
        style={{
          width: '100%', padding: '6px 10px',
          background: canSend ? c : 'rgba(255,255,255,0.05)',
          border: `1px solid ${c}`,
          color: canSend ? '#000' : 'var(--hud-text-dim)',
          fontFamily: 'inherit', fontSize: 10, letterSpacing: '0.22em', fontWeight: 700,
          cursor: canSend ? 'pointer' : 'not-allowed',
          transition: 'background 0.15s, color 0.15s',
        }}
      >
        {sending ? 'GENERATING…' : 'GENERATE →'}
      </button>

      {/* Footer: last result / error */}
      <div className="mt-2 text-[9px] tracking-wider flex items-center gap-2" style={{ minHeight: 14 }}>
        {error ? (
          <span style={{ color: '#ff6b6b', wordBreak: 'break-word' }}>! {error}</span>
        ) : last ? (
          <>
            <img
              src={`${base}${last.url}`}
              alt="last generation"
              style={{ width: 28, height: 28, objectFit: 'cover', border: `1px solid ${c}` }}
            />
            <span style={{ color: 'var(--hud-text-dim)' }}>
              {result?.elapsed_s}s · <span style={{ color: c }}>~${result?.estimated_cost_usd}</span>
            </span>
          </>
        ) : (
          <span style={{ color: 'var(--hud-text-dim)', opacity: 0.55 }}>no image generated yet</span>
        )}
      </div>
    </div>
  );
}

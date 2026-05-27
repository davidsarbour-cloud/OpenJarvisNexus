/**
 * Nexus9 — SkillActivator modal.
 *
 * Click an "ACTIVATE" button on a SkillCard → this modal opens, pre-filled
 * with the skill's example invocation. The user tweaks the prompt and
 * sends it through POST /v1/chat/completions (streaming OFF — we render
 * the final assistant message inline, no SSE plumbing here). The chat
 * router already injects the skill catalog at every turn, so JARVIS picks
 * `skill_get` on its own and follows the protocol.
 *
 * Keep this self-contained: no router navigation, no global state — just
 * a small fetch + a markdown-flavored result panel.
 */
import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { X, Send, Loader2 } from 'lucide-react';
import { getBase } from '../../lib/api';

interface SkillActivatorProps {
  skillName:    string;
  description:  string;
  exampleText:  string;
  /** Obsidian note path (relative to BRAIN vault) attached to the
   *  completion event so the RightPanel row becomes clickable. */
  notePath?:    string;
  accent:       string;
  glow:         string;
  subtle:       string;
  onClose:      () => void;
}

interface ChatResponse {
  choices?: { message?: { content?: string } }[];
  model?:   string;
}

export function SkillActivator({
  skillName,
  description,
  exampleText,
  notePath,
  accent,
  glow,
  subtle,
  onClose,
}: SkillActivatorProps) {
  const [prompt, setPrompt]   = useState(exampleText);
  const [result, setResult]   = useState<string>('');
  const [model,  setModel]    = useState<string>('');
  const [error,  setError]    = useState<string>('');
  const [loading, setLoading] = useState(false);
  const textareaRef           = useRef<HTMLTextAreaElement>(null);
  const resultRef             = useRef<HTMLDivElement>(null);

  // When a response (or error) arrives, scroll the modal body to it —
  // budget-block messages especially are easy to miss otherwise.
  useEffect(() => {
    if (result || error) {
      resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [result, error]);

  // Esc to close + autofocus the textarea
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    textareaRef.current?.focus();
    textareaRef.current?.select();
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  async function send() {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setError('');
    setResult('');
    setModel('');
    try {
      // Prefix the prompt with `!local` so chat_router → should_use_claude()
      // returns False and Ollama (qwen3:14b) handles the skill instead of
      // Claude. Reasons:
      //   1. qwen3:14b is fully capable of every Hermes protocol (plan,
      //      humanizer, ideation, systematic-debugging…) — they're text
      //      analyses, not Claude-specific.
      //   2. Skills can fire often from the UI; routing them to Claude
      //      drained the budget on the first try and surfaced as
      //      "doesn't send" in the modal (model=bloqué).
      //   3. Frees the Claude budget for ad-hoc chat in /chat where
      //      reasoning quality matters.
      // The `!local` token is stripped by chat_router and never appears
      // in the assistant context. The displayed `prompt` stays unchanged
      // so the user always sees the natural-language invocation they
      // typed.
      const wireMessage = `!local ${prompt.trim()}`;

      const r = await fetch(`${getBase()}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: wireMessage, stream: false }),
      });
      if (!r.ok) {
        setError(`HTTP ${r.status}`);
        return;
      }
      const data = (await r.json()) as ChatResponse;
      const m = data.model || '?';
      setModel(m);
      setResult(data.choices?.[0]?.message?.content || '(empty response)');

      // Broadcast a completion event so RightPanel ALERTS & EVENTS picks
      // it up (clickable → opens the Hermes note in Obsidian). Skipped
      // when the budget guard blocked the request — that's not a real
      // skill run. Fire-and-forget; errors here must not break the UI.
      const blocked = m === 'bloqué' || m === 'bloque';
      if (!blocked) {
        void fetch(`${getBase()}/v1/events/publish`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            level:  'info',
            source: 'SKILL',
            msg:    `${skillName} · manual activation complete`,
            ...(notePath ? { note: notePath } : {}),
            skill:  skillName,
          }),
        }).catch(() => { /* event publish is best-effort */ });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        onClick={onClose}
        className="fixed inset-0 z-40 flex items-center justify-center px-4"
        style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(3px)' }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 6 }}
          animate={{ opacity: 1, scale: 1,    y: 0 }}
          exit={{    opacity: 0, scale: 0.96, y: 6 }}
          transition={{ type: 'spring', stiffness: 320, damping: 28 }}
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-label={`Activate skill ${skillName}`}
          className="w-full max-w-2xl max-h-[80vh] flex flex-col"
          style={{
            background:   'linear-gradient(180deg, rgba(2,5,11,0.98) 0%, rgba(2,5,11,0.95) 100%)',
            border:       `1px solid ${accent}`,
            boxShadow:    `0 0 48px -8px ${glow}, inset 0 0 32px -16px ${glow}`,
            borderRadius: 6,
            fontFamily:   "'IBM Plex Mono', ui-monospace, monospace",
          }}
        >
          {/* Header */}
          <header
            className="flex items-center justify-between px-4 py-3 shrink-0"
            style={{ borderBottom: '1px solid var(--hud-border)' }}
          >
            <div className="flex items-center gap-3">
              <span className="text-[9px] font-bold tracking-[0.3em]"
                    style={{ color: 'var(--hud-text-dim)' }}>
                ◆ ACTIVATE
              </span>
              <span className="text-[12px] font-bold tracking-[0.22em]"
                    style={{ color: accent, textShadow: `0 0 8px ${glow}` }}>
                {skillName.toUpperCase()}
              </span>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="flex items-center justify-center rounded transition-colors"
              style={{
                width: 22, height: 22,
                color: 'var(--hud-text-dim)',
                border: '1px solid var(--hud-border)',
                background: 'transparent',
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

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
            <p className="text-[10.5px] leading-relaxed"
               style={{ color: 'var(--hud-text-dim)' }}>
              {description}
            </p>

            <label className="text-[8px] tracking-[0.3em]"
                   style={{ color: 'var(--hud-text-dim)' }}>
              PROMPT
            </label>
            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                  e.preventDefault();
                  void send();
                }
              }}
              rows={4}
              spellCheck={false}
              className="w-full px-3 py-2 text-[12px] resize-none outline-none"
              style={{
                background:   'rgba(0,0,0,0.4)',
                border:       '1px solid var(--hud-border)',
                borderLeft:   `2px solid ${accent}`,
                color:        'var(--hud-text)',
                fontFamily:   'inherit',
                borderRadius: 3,
              }}
            />

            <div className="flex items-center justify-between text-[9px] tracking-wider"
                 style={{ color: 'var(--hud-text-dim)' }}>
              <span>
                Ctrl+Enter pour envoyer · routé sur{' '}
                <span style={{ color: accent }}>Ollama</span> (local, sans budget)
              </span>
              <button
                type="button"
                onClick={() => void send()}
                disabled={loading || !prompt.trim()}
                className="flex items-center gap-2 px-3 py-1.5 text-[10px] font-bold tracking-[0.22em] transition-colors"
                style={{
                  color: loading ? 'var(--hud-text-dim)' : accent,
                  background: loading ? 'transparent' : subtle,
                  border: `1px solid ${accent}`,
                  borderRadius: 3,
                  cursor: loading ? 'wait' : 'pointer',
                  opacity: !prompt.trim() ? 0.4 : 1,
                }}
              >
                {loading ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
                {loading ? 'SENDING' : 'SEND'}
              </button>
            </div>

            {error && (
              <div
                ref={resultRef}
                className="px-3 py-2 text-[10.5px]"
                style={{
                  color:      'var(--color-cyberdeck)',
                  background: 'rgba(255,45,85,0.08)',
                  border:     '1px solid var(--color-cyberdeck)',
                  borderRadius: 3,
                }}
              >
                <strong>error</strong> · {error}
              </div>
            )}

            {result && (() => {
              // Chat router returns model="bloqué" when the budget guard
              // intercepts a Claude-routed prompt. Render that path as a
              // warning so the user doesn't read "the SEND did nothing" —
              // the response IS the budget message.
              const isBlocked = model === 'bloqué' || model === 'bloque';
              const stripeColor = isBlocked ? 'var(--color-security)' : accent;
              const tagColor    = isBlocked ? 'var(--color-security)' : accent;
              const tagLabel    = isBlocked ? 'BUDGET BLOCKED' : `RESPONSE · ${model || '?'}`;
              return (
                <div ref={!error ? resultRef : null} className="flex flex-col gap-2">
                  <label className="text-[8px] tracking-[0.3em] mt-1"
                         style={{ color: tagColor }}>
                    {tagLabel}
                  </label>
                  <pre
                    className="px-3 py-2 text-[11px] whitespace-pre-wrap break-words"
                    style={{
                      background: isBlocked ? 'rgba(245,158,11,0.05)' : 'rgba(0,0,0,0.4)',
                      border:     `1px solid ${isBlocked ? 'var(--color-security)' : 'var(--hud-border)'}`,
                      borderLeft: `2px solid ${stripeColor}`,
                      color:      'var(--hud-text)',
                      fontFamily: 'inherit',
                      borderRadius: 3,
                      maxHeight: '40vh',
                      overflowY: 'auto',
                    }}
                  >
                    {result}
                  </pre>
                  {isBlocked && (
                    <div className="text-[10px] leading-relaxed"
                         style={{ color: 'var(--hud-text-dim)' }}>
                      Le routing chat a tenté Claude. Pour débloquer : bump
                      <code style={{ color: 'var(--color-security)' }}> BUDGET_MAX_USD </code>
                      dans <code style={{ color: accent }}>backend/.env</code> puis restart le backend.
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

import { useRef, useEffect, useState } from 'react';
import { ChevronRight, ChevronLeft } from 'lucide-react';
import { useAppStore } from '../lib/store';
import { MessageBubble } from '../components/Chat/MessageBubble';
import { InputArea } from '../components/Chat/InputArea';
import { StreamingDots } from '../components/Chat/StreamingDots';
import { JarvisOrb } from '../components/Chat/JarvisOrb';

/**
 * JarvisChatPage — route `/chat`.
 * The animated J.A.R.V.I.S core is the centre stage and reacts when it
 * responds; the conversation transcript lives in a collapsible right sidebar.
 * Text + voice (the reused InputArea has the mic) sit below the orb.
 */
export function JarvisChatPage() {
  const messages = useAppStore((s) => s.messages);
  const streamState = useAppStore((s) => s.streamState);
  const speaking = streamState.isStreaming;
  const listRef = useRef<HTMLDivElement>(null);
  const [collapsed, setCollapsed] = useState(false);
  const empty = messages.length === 0 && !streamState.isStreaming;

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, streamState.content, collapsed]);

  return (
    <div className="flex h-full" style={{ background: 'var(--hud-bg)' }}>
      {/* ── Centre stage: animated orb + status + input ──────────────── */}
      <main className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 flex flex-col items-center justify-center gap-8 min-h-0">
          <JarvisOrb speaking={speaking} size={380} />
          <div className="text-center">
            <div
              className="text-[12px] font-bold tracking-[0.35em]"
              style={{ color: speaking ? 'var(--color-jarvis)' : 'var(--hud-text-hot)' }}
            >
              {speaking ? (streamState.phase || 'JARVIS RÉPOND…') : 'JARVIS EN LIGNE'}
            </div>
            <div className="text-[10px] tracking-[0.22em] mt-1.5" style={{ color: 'var(--hud-text-dim)' }}>
              {speaking ? 'TRANSMISSION EN COURS' : 'JARVIS · EN ÉCOUTE'}
            </div>
          </div>
        </div>
        <InputArea />
      </main>

      {/* ── Conversation sidebar (right) — collapsible ───────────────── */}
      <aside
        className="flex flex-col shrink-0 overflow-hidden"
        style={{
          width: collapsed ? 46 : 400,
          background: 'var(--hud-bg-elev)',
          borderLeft: '1px solid var(--hud-border)',
          transition: 'width 0.22s ease',
        }}
      >
        {collapsed ? (
          <button
            onClick={() => setCollapsed(false)}
            title="Afficher la conversation"
            className="flex flex-col items-center gap-3 pt-3 h-full cursor-pointer"
            style={{ color: 'var(--hud-text-dim)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-jarvis)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
          >
            <ChevronLeft size={16} />
            <span className="text-[9px] font-bold tracking-[0.25em]" style={{ writingMode: 'vertical-rl' }}>
              CONVERSATION
            </span>
            {messages.length > 0 && (
              <span
                className="text-[8px] px-1 py-0.5"
                style={{ border: '1px solid var(--hud-border)', color: 'var(--hud-text-dim)' }}
              >
                {messages.length}
              </span>
            )}
          </button>
        ) : (
          <>
            <div
              className="px-3 py-2 text-[9px] font-bold tracking-[0.25em] flex items-center gap-2 shrink-0"
              style={{ color: 'var(--hud-text-dim)', background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid var(--hud-border)' }}
            >
              <span>── CONVERSATION</span>
              <span
                className="ml-auto px-1.5 py-0.5"
                style={{
                  fontSize: 8,
                  color: speaking ? 'var(--color-jarvis)' : 'var(--hud-text-dim)',
                  border: `1px solid ${speaking ? 'var(--color-jarvis)' : 'var(--hud-border)'}`,
                }}
              >
                {speaking ? 'LIVE' : `${messages.length} MSG`}
              </span>
              <button
                onClick={() => setCollapsed(true)}
                title="Réduire la conversation"
                className="flex items-center justify-center cursor-pointer shrink-0"
                style={{ color: 'var(--hud-text-dim)', width: 16, height: 16 }}
                onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-jarvis)')}
                onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
              >
                <ChevronRight size={14} />
              </button>
            </div>

            <div ref={listRef} className="flex-1 overflow-y-auto px-3 py-3 flex flex-col">
              {empty ? (
                <div
                  className="m-auto text-center px-4 text-[10px] tracking-[0.22em] leading-relaxed"
                  style={{ color: 'var(--hud-text-dim)' }}
                >
                  AUCUN MESSAGE
                  <br />
                  PARLE OU ÉCRIS À JARVIS
                </div>
              ) : (
                <div>
                  {messages.map((m) => (
                    <MessageBubble key={m.id} message={m} />
                  ))}
                  {streamState.isStreaming && streamState.content === '' && (
                    <div className="flex justify-start mb-4">
                      <StreamingDots phase={streamState.phase} />
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </aside>
    </div>
  );
}

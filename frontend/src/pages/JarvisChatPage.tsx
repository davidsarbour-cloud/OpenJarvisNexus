import { useRef, useEffect } from 'react';
import { useAppStore } from '../lib/store';
import { MessageBubble } from '../components/Chat/MessageBubble';
import { InputArea } from '../components/Chat/InputArea';
import { StreamingDots } from '../components/Chat/StreamingDots';
import { JarvisOrb } from '../components/Chat/JarvisOrb';

/**
 * JarvisChatPage — route `/chat`.
 * Conversation page with the animated J.A.R.V.I.S core that reacts when it
 * responds. Text + voice (the reused InputArea has the mic). Empty state
 * shows the big orb; once talking, the orb shrinks to a live header.
 */
export function JarvisChatPage() {
  const messages = useAppStore((s) => s.messages);
  const streamState = useAppStore((s) => s.streamState);
  const speaking = streamState.isStreaming;
  const listRef = useRef<HTMLDivElement>(null);
  const empty = messages.length === 0 && !streamState.isStreaming;

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, streamState.content]);

  return (
    <div className="flex flex-col h-full" style={{ background: 'var(--hud-bg)' }}>
      {empty ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-7">
          <JarvisOrb speaking={speaking} size={320} />
          <div className="text-center">
            <div className="text-[12px] font-bold tracking-[0.35em]" style={{ color: 'var(--hud-text-hot)' }}>
              JARVIS EN LIGNE
            </div>
            <div className="text-[10px] tracking-[0.22em] mt-1.5" style={{ color: 'var(--hud-text-dim)' }}>
              PARLE OU ÉCRIS POUR COMMENCER
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="flex flex-col items-center pt-4 pb-2 shrink-0">
            <JarvisOrb speaking={speaking} size={120} />
            <div
              className="text-[9px] font-bold tracking-[0.3em] mt-1"
              style={{ color: speaking ? 'var(--color-jarvis)' : 'var(--hud-text-dim)' }}
            >
              {speaking ? (streamState.phase || 'JARVIS RÉPOND…') : 'JARVIS · EN ÉCOUTE'}
            </div>
          </div>
          <div ref={listRef} className="flex-1 overflow-y-auto">
            <div className="max-w-[var(--chat-max-width)] mx-auto px-4 py-4">
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
              {streamState.isStreaming && streamState.content === '' && (
                <div className="flex justify-start mb-4">
                  <StreamingDots phase={streamState.phase} />
                </div>
              )}
            </div>
          </div>
        </>
      )}
      <InputArea />
    </div>
  );
}

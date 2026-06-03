import { useRef, useEffect, useState, useCallback } from 'react';
import { ChevronRight, ChevronLeft, ChevronDown, Cpu, Volume2, VolumeX } from 'lucide-react';
import { useAppStore } from '../lib/store';
import { getBase } from '../lib/api';
import { useVadSpeech } from '../hooks/useVadSpeech';
import { useSendMessage } from '../hooks/useSendMessage';
import { MessageBubble } from '../components/Chat/MessageBubble';
import { InputArea } from '../components/Chat/InputArea';
import { StreamingDots } from '../components/Chat/StreamingDots';
import { JarvisOrb } from '../components/Chat/JarvisOrb';

/**
 * JarvisChatPage — route `/chat`.
 *
 * Layout:
 *   ┌──────────────────────────────────┬──────────────────┐
 *   │  [model badge ▾]                 │  ── CONVERSATION  │
 *   │                                  │  [LIVE] [🔊] [>]  │
 *   │       JarvisOrb                  │                   │
 *   │                                  │  user: ...        │
 *   │    JARVIS EN LIGNE               │  jarvis: ...      │
 *   │    EN ÉCOUTE · N messages        │    42 chars  [▶]  │
 *   │                                  │  user: ...        │
 *   │         [ InputArea ]            │  ▊ streaming...   │
 *   └──────────────────────────────────┴──────────────────┘
 *
 * Les réponses de JARVIS apparaissent UNIQUEMENT dans la sidebar.
 * La sidebar s'ouvre automatiquement dès que JARVIS commence à répondre.
 */
export function JarvisChatPage() {
  const messages         = useAppStore((s) => s.messages);
  const streamState      = useAppStore((s) => s.streamState);
  const selectedModel    = useAppStore((s) => s.selectedModel);
  const models           = useAppStore((s) => s.models);
  const setSelectedModel = useAppStore((s) => s.setSelectedModel);

  const speaking = streamState.isStreaming;
  const listRef  = useRef<HTMLDivElement>(null);

  // ── Panel states ──────────────────────────────────────────────────────────
  const [sidebarOpen,     setSidebarOpen]     = useState(false);
  const [modelPickerOpen, setModelPickerOpen] = useState(false);
  const [ttsPlaying,      setTtsPlaying]      = useState(false);
  const [ttsEnabled,      setTtsEnabled]      = useState(true);
  const [playingMsgId,    setPlayingMsgId]    = useState<string | null>(null);

  const ttsAudioRef  = useRef<HTMLAudioElement | null>(null);
  const ttsUrlRef    = useRef<string | null>(null);
  const ttsGenRef    = useRef(0);        // generation counter — chaque speakText incrémente, les anciennes boucles se suicident
  const prevStreaming = useRef(false);

  const empty = messages.length === 0 && !streamState.isStreaming;

  const estTokens = Math.round((streamState.content?.length ?? 0) / 4);

  const _CLOUD  = ['gpt-', 'o1-', 'o3-', 'claude-', 'gemini-', 'openrouter/'];
  const isLocal = selectedModel ? !_CLOUD.some((p) => selectedModel.startsWith(p)) : false;
  const modelLabel = selectedModel
    ? (selectedModel.split('/').pop() ?? selectedModel)
    : 'NO MODEL';

  // ── Auto-open sidebar when JARVIS starts streaming ─────────────────────
  // Triggered by an external state change (the streaming flag flipping
  // true). Effect-driven setState is the correct pattern for "react to
  // a derived event"; lint flags it anyway.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (speaking) setSidebarOpen(true);
  }, [speaking]);

  // ── Auto-scroll sidebar ────────────────────────────────────────────────
  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, streamState.content, sidebarOpen]);

  // ── Close model picker on outside click ───────────────────────────────
  useEffect(() => {
    if (!modelPickerOpen) return;
    const handler = () => setModelPickerOpen(false);
    window.addEventListener('click', handler);
    return () => window.removeEventListener('click', handler);
  }, [modelPickerOpen]);

  // ── TTS — pipeline phrase par phrase ─────────────────────────────────
  // Stratégie : découper en phrases → fetch phrase N+1 en parallèle pendant
  // que phrase N joue → zéro gap entre phrases, démarrage quasi-immédiat.

  const _cleanTts = (text: string) =>
    text
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`[^`]+`/g, '')
      .replace(/#{1,6}\s/g, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .trim();

  const _splitSentences = (text: string): string[] => {
    const parts = text
      .split(/(?<=[.!?;:])\s+/)
      .map(s => s.trim())
      .filter(s => s.length > 2);
    return parts.length > 0 ? parts.slice(0, 10) : [text.slice(0, 500)];
  };

  const _fetchAudioUrl = async (sentence: string): Promise<string | null> => {
    try {
      const res = await fetch(
        `${getBase()}/v1/tts?text=${encodeURIComponent(sentence.slice(0, 600))}`,
      );
      if (!res.ok) return null;
      const blob = await res.blob();
      return URL.createObjectURL(blob);
    } catch { return null; }
  };

  const _playUrl = (url: string): Promise<void> =>
    new Promise((resolve) => {
      const audio = new Audio(url);
      ttsAudioRef.current  = audio;
      ttsUrlRef.current    = url;
      const cleanup = () => {
        URL.revokeObjectURL(url);
        ttsUrlRef.current   = null;
        ttsAudioRef.current = null;
        resolve();
      };
      audio.onended  = cleanup;
      audio.onerror  = cleanup;
      audio.play().catch(cleanup);
    });

  const speakText = useCallback(async (text: string, msgId?: string) => {
    if (!text.trim()) return;

    // Incrémente la génération — toutes les boucles précédentes vont se stopper
    const myGen = ++ttsGenRef.current;

    // Stoppe l'audio en cours immédiatement
    ttsAudioRef.current?.pause();
    if (ttsUrlRef.current) { URL.revokeObjectURL(ttsUrlRef.current); ttsUrlRef.current = null; }
    ttsAudioRef.current = null;

    const clean = _cleanTts(text);
    if (!clean) return;

    const sentences = _splitSentences(clean);
    setTtsPlaying(true);
    setPlayingMsgId(msgId ?? null);

    // Pipeline : prefetch phrase i+1 pendant que phrase i joue
    let nextFetch: Promise<string | null> = _fetchAudioUrl(sentences[0]);

    for (let i = 0; i < sentences.length; i++) {
      if (ttsGenRef.current !== myGen) break;  // une nouvelle voix a démarré → on s'arrête

      const url = await nextFetch;
      if (!url || ttsGenRef.current !== myGen) break;

      // Lance le prefetch de la phrase suivante en parallèle
      if (i + 1 < sentences.length) {
        nextFetch = _fetchAudioUrl(sentences[i + 1]);
      }

      await _playUrl(url);
    }

    // Ne reset l'état que si c'est toujours nous qui jouons
    if (ttsGenRef.current === myGen) {
      setTtsPlaying(false);
      setPlayingMsgId(null);
    }
  }, []);  

  const stopTts = useCallback(() => {
    ttsGenRef.current++;  // invalide toute boucle en cours
    ttsAudioRef.current?.pause();
    if (ttsUrlRef.current) { URL.revokeObjectURL(ttsUrlRef.current); ttsUrlRef.current = null; }
    ttsAudioRef.current = null;
    setTtsPlaying(false);
    setPlayingMsgId(null);
  }, []);

  // ── Auto-play TTS on stream end ───────────────────────────────────────
  useEffect(() => {
    const wasStreaming = prevStreaming.current;
    prevStreaming.current = speaking;
    // In hands-free mode the conversation loop drives TTS itself (await), so
    // skip the edge-effect here to avoid speaking twice.
    if (wasStreaming && !speaking && ttsEnabled && !useAppStore.getState().handsFree) {
      const last = [...messages].reverse().find((m) => m.role === 'assistant' && m.content);
      // speakText updates internal speech state — calling it from an
      // effect that observes the streaming edge is intentional.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (last?.content) speakText(last.content, last.id);
    }
  }, [speaking, messages, ttsEnabled, speakText]);

  // ── Hands-free conversation loop ──────────────────────────────────────
  // Toggle once → JARVIS listens (VAD) → auto-sends → replies → speaks (here,
  // awaited) → listens again. No per-turn button. Toggle off to stop.
  const handsFree    = useAppStore((s) => s.handsFree);
  const { state: vadState, listenOnce, abort: abortVad } = useVadSpeech();
  const { send } = useSendMessage();
  const handsFreeRef = useRef(false);

  useEffect(() => {
    handsFreeRef.current = handsFree;
    if (!handsFree) { abortVad(); stopTts(); return; }
    setTtsEnabled(true);                                  // ensure replies are spoken
    const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
    (async () => {
      while (handsFreeRef.current) {
        const text = await listenOnce();                  // resolves when you stop talking
        if (!handsFreeRef.current) break;
        if (!text || !text.trim()) { await sleep(250); continue; }
        const reply = await send(text, { maxTokens: 260 }); // shorter = snappier voice
        if (!handsFreeRef.current) break;
        if (reply && reply.trim()) await speakText(reply);  // SPEAK and wait until done
        await sleep(120);
      }
    })();
    return () => { abortVad(); };
  }, [handsFree, listenOnce, send, abortVad, speakText, stopTts]);

  return (
    <div className="flex h-full" style={{ background: 'var(--hud-bg)' }}>

      {/* ══ Centre stage ═══════════════════════════════════════════════════ */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* ── Model selector pill ──────────────────────────────────────── */}
        <div className="flex items-center justify-center pt-3 pb-1 shrink-0">
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setModelPickerOpen((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 cursor-pointer"
              style={{
                border:        `1px solid ${speaking ? 'var(--color-jarvis)' : 'var(--hud-border)'}`,
                color:         speaking ? 'var(--color-jarvis)' : 'var(--hud-text-dim)',
                background:    'rgba(0,0,0,0.35)',
                fontSize:      9,
                fontWeight:    700,
                letterSpacing: '0.2em',
                transition:    'border-color 0.3s, color 0.3s',
              }}
              title="Changer de modèle"
            >
              <Cpu size={9} />
              <span>{modelLabel.toUpperCase()}</span>
              {isLocal && (
                <span className="text-[8px] px-1" style={{ color: 'var(--color-jarvis)', opacity: 0.7 }}>
                  LOCAL
                </span>
              )}
              {speaking && (
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full animate-pulse"
                  style={{ background: 'var(--color-jarvis)' }}
                />
              )}
              <ChevronDown size={8} style={{ opacity: 0.6 }} />
            </button>

            {/* Dropdown model list */}
            {modelPickerOpen && (
              <div
                className="absolute top-full left-1/2 mt-1 z-50 overflow-y-auto"
                style={{
                  transform:  'translateX(-50%)',
                  background: 'var(--hud-bg-elev)',
                  border:     '1px solid var(--hud-border)',
                  minWidth:   260,
                  maxHeight:  340,
                  boxShadow:  '0 8px 32px rgba(0,0,0,0.6)',
                }}
              >
                <div
                  className="px-3 py-1.5 text-[8px] font-bold tracking-[0.3em]"
                  style={{ color: 'var(--hud-text-dim)', borderBottom: '1px solid var(--hud-border)' }}
                >
                  SÉLECTIONNER UN MODÈLE
                </div>
                {models.length === 0 ? (
                  <div className="px-3 py-3 text-[9px]" style={{ color: 'var(--hud-text-dim)' }}>
                    Chargement des modèles…
                  </div>
                ) : (
                  models.map((m) => {
                    const active = m.id === selectedModel;
                    const local  = !_CLOUD.some((p) => m.id.startsWith(p));
                    return (
                      <button
                        key={m.id}
                        onClick={() => { setSelectedModel(m.id); setModelPickerOpen(false); }}
                        className="w-full text-left px-3 py-2 flex items-center gap-2 cursor-pointer"
                        style={{
                          color:        active ? 'var(--color-jarvis)' : 'var(--hud-text)',
                          background:   active ? 'rgba(0,255,136,0.06)' : 'transparent',
                          borderBottom: '1px solid var(--hud-border)',
                          fontSize:     10,
                          transition:   'background 0.15s',
                        }}
                        onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = active ? 'rgba(0,255,136,0.06)' : 'transparent'; }}
                      >
                        <Cpu size={9} style={{ flexShrink: 0, opacity: 0.6 }} />
                        <span className="font-bold tracking-wider flex-1 truncate">{m.id}</span>
                        {local && (
                          <span className="text-[8px] shrink-0" style={{ color: 'var(--color-jarvis)', opacity: 0.7 }}>LOCAL</span>
                        )}
                        {active && (
                          <span className="text-[8px] shrink-0 font-bold" style={{ color: 'var(--color-jarvis)' }}>● ACTIF</span>
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Orb + status ─────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col items-center justify-center gap-6 min-h-0 px-6 overflow-hidden">

          <JarvisOrb speaking={speaking} size={200} />

          {/* Status line */}
          <div className="text-center shrink-0">
            <div
              className="text-[11px] font-bold tracking-[0.35em]"
              style={{ color: speaking ? 'var(--color-jarvis)' : 'var(--hud-text-hot)' }}
            >
              {speaking ? (streamState.phase || 'JARVIS RÉPOND…') : 'JARVIS EN LIGNE'}
            </div>
            <div className="text-[9px] tracking-[0.22em] mt-1" style={{ color: 'var(--hud-text-dim)' }}>
              {speaking
                ? `${(streamState.elapsedMs / 1000).toFixed(1)}s · ~${estTokens} tokens`
                : 'EN ÉCOUTE · ' + (messages.length > 0 ? `${messages.length} messages` : 'aucun message')}
            </div>
          </div>

          {/* ── Hands-free live status (toggle lives in the chat bar) ───── */}
          {handsFree && (
            <div
              className="flex items-center gap-2 px-4 py-2 shrink-0"
              style={{
                border: '1px solid var(--color-jarvis)', color: 'var(--color-jarvis)',
                background: 'rgba(0,255,136,0.06)', fontSize: 10, fontWeight: 700, letterSpacing: '0.2em',
              }}
            >
              <span className="inline-block w-1.5 h-1.5 rounded-full animate-pulse"
                style={{ background: 'var(--color-jarvis)' }} />
              <span>
                {(vadState === 'listening' || vadState === 'speaking') ? 'EN ÉCOUTE…'
                  : vadState === 'transcribing' ? 'TRANSCRIPTION…'
                  : speaking ? 'JARVIS RÉPOND…'
                  : ttsPlaying ? 'JARVIS PARLE…'
                  : 'CONVERSATION ● ON'}
              </span>
            </div>
          )}

          {/* Empty hint */}
          {empty && !handsFree && (
            <div className="text-[9px] tracking-[0.2em] text-center" style={{ color: 'var(--hud-text-dim)' }}>
              PARLE OU ÉCRIS À JARVIS
            </div>
          )}
        </div>

        <InputArea />
      </main>

      {/* ══ Conversation sidebar (right) ═══════════════════════════════════ */}
      <aside
        className="flex flex-col shrink-0 overflow-hidden"
        style={{
          width:      sidebarOpen ? 420 : 46,
          background: 'var(--hud-bg-elev)',
          borderLeft: '1px solid var(--hud-border)',
          transition: 'width 0.22s ease',
        }}
      >
        {!sidebarOpen ? (
          /* ── Collapsed tab ─────────────────────────────────────────── */
          <button
            onClick={() => setSidebarOpen(true)}
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
          /* ── Expanded panel ────────────────────────────────────────── */
          <>
            {/* Header */}
            <div
              className="px-3 py-2 text-[9px] font-bold tracking-[0.25em] flex items-center gap-2 shrink-0"
              style={{
                color:        'var(--hud-text-dim)',
                background:   'rgba(0,0,0,0.2)',
                borderBottom: '1px solid var(--hud-border)',
              }}
            >
              <span>── CONVERSATION</span>

              {/* Live / msg count badge */}
              <span
                className="px-1.5 py-0.5"
                style={{
                  fontSize: 8,
                  color:    speaking ? 'var(--color-jarvis)' : 'var(--hud-text-dim)',
                  border:   `1px solid ${speaking ? 'var(--color-jarvis)' : 'var(--hud-border)'}`,
                }}
              >
                {speaking ? 'LIVE' : `${messages.length} MSG`}
              </span>

              <div className="flex-1" />

              {/* Voice auto-play toggle */}
              <button
                onClick={() => setTtsEnabled((v) => !v)}
                className="flex items-center gap-1 cursor-pointer px-1.5 py-0.5"
                style={{
                  fontSize:      8,
                  fontWeight:    700,
                  letterSpacing: '0.15em',
                  color:         ttsEnabled ? 'var(--color-jarvis)' : 'var(--hud-text-dim)',
                  border:        `1px solid ${ttsEnabled ? 'var(--color-jarvis)' : 'var(--hud-border)'}`,
                  background:    ttsEnabled ? 'rgba(0,255,136,0.06)' : 'transparent',
                  transition:    'all 0.2s',
                }}
                title={ttsEnabled ? 'Désactiver la voix automatique' : 'Activer la voix automatique'}
              >
                {ttsEnabled ? <Volume2 size={9} /> : <VolumeX size={9} />}
                <span>{ttsEnabled ? 'VOIX' : 'OFF'}</span>
              </button>

              {/* Collapse button */}
              <button
                onClick={() => setSidebarOpen(false)}
                title="Réduire"
                className="flex items-center justify-center cursor-pointer shrink-0"
                style={{ color: 'var(--hud-text-dim)', width: 16, height: 16 }}
                onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-jarvis)')}
                onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
              >
                <ChevronRight size={14} />
              </button>
            </div>

            {/* Message list */}
            <div ref={listRef} className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-1">
              {empty ? (
                <div
                  className="m-auto text-center px-4 text-[10px] tracking-[0.22em] leading-relaxed"
                  style={{ color: 'var(--hud-text-dim)' }}
                >
                  AUCUN MESSAGE<br />PARLE OU ÉCRIS À JARVIS
                </div>
              ) : (
                <>
                  {messages.map((m) => {
                    const isAssistant = m.role === 'assistant';
                    const charCount   = m.content?.length ?? 0;
                    const isPlaying   = playingMsgId === m.id && ttsPlaying;
                    return (
                      <div key={m.id}>
                        <MessageBubble message={m} />

                        {/* Char count + play button for each assistant message */}
                        {isAssistant && charCount > 0 && (
                          <div
                            className="flex items-center gap-2 mb-2 ml-1"
                            style={{ justifyContent: 'flex-start' }}
                          >
                            {/* Char count badge */}
                            <span
                              className="text-[8px] font-bold tracking-[0.15em] px-1.5 py-0.5"
                              style={{
                                color:      'var(--hud-text-dim)',
                                border:     '1px solid var(--hud-border)',
                                background: 'rgba(0,0,0,0.2)',
                              }}
                            >
                              {charCount} chars
                            </span>

                            {/* Play / Stop button */}
                            <button
                              onClick={() => isPlaying ? stopTts() : speakText(m.content ?? '', m.id)}
                              className="flex items-center gap-1 text-[8px] font-bold tracking-[0.15em] px-1.5 py-0.5 cursor-pointer"
                              style={{
                                color:      isPlaying ? 'var(--color-jarvis)' : 'var(--hud-text-dim)',
                                border:     `1px solid ${isPlaying ? 'var(--color-jarvis)' : 'var(--hud-border)'}`,
                                background: isPlaying ? 'rgba(0,255,136,0.06)' : 'transparent',
                                transition: 'all 0.2s',
                              }}
                              title={isPlaying ? 'Arrêter' : 'Écouter ce message'}
                            >
                              {isPlaying ? <VolumeX size={8} /> : <Volume2 size={8} />}
                              <span>{isPlaying ? 'STOP' : '▶'}</span>
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Live streaming message */}
                  {streamState.isStreaming && (
                    <div>
                      {streamState.content === '' ? (
                        <div className="flex justify-start mb-2">
                          <StreamingDots phase={streamState.phase} />
                        </div>
                      ) : (
                        <div
                          className="text-[12px] leading-relaxed px-3 py-2 mb-1"
                          style={{
                            color:      'var(--hud-text)',
                            background: 'rgba(0,255,136,0.04)',
                            border:     '1px solid var(--color-jarvis)',
                            whiteSpace: 'pre-wrap',
                            wordBreak:  'break-word',
                          }}
                        >
                          {streamState.content}
                          <span
                            className="animate-pulse"
                            style={{ color: 'var(--color-jarvis)', marginLeft: 1 }}
                          >▊</span>
                        </div>
                      )}

                      {/* Live char count during stream */}
                      {streamState.content.length > 0 && (
                        <div className="flex items-center gap-2 ml-1 mb-2">
                          <span
                            className="text-[8px] font-bold tracking-[0.15em] px-1.5 py-0.5 animate-pulse"
                            style={{
                              color:      'var(--color-jarvis)',
                              border:     '1px solid var(--color-jarvis)',
                              background: 'rgba(0,255,136,0.06)',
                            }}
                          >
                            {streamState.content.length} chars · ~{estTokens} tok
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </aside>
    </div>
  );
}

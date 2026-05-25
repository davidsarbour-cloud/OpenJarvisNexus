import { useRef, useEffect, useState, useCallback } from 'react';
import { ChevronRight, ChevronLeft, ChevronUp, ChevronDown, Cpu, Volume2, VolumeX } from 'lucide-react';
import { useAppStore } from '../lib/store';
import { getBase } from '../lib/api';
import { MessageBubble } from '../components/Chat/MessageBubble';
import { InputArea } from '../components/Chat/InputArea';
import { StreamingDots } from '../components/Chat/StreamingDots';
import { JarvisOrb } from '../components/Chat/JarvisOrb';

/**
 * JarvisChatPage — route `/chat`.
 *
 * Layout:
 *   ┌─────────────────────────────────────────────┬──────┐
 *   │  [model badge ▾]                             │  ◀   │
 *   │                                             │  C   │
 *   │          JarvisOrb  (speaks / idle)         │  O   │
 *   │                                             │  N   │
 *   │   [▲ RÉPONSE — 1ère ligne…  42 chars]       │  V   │
 *   │   ─── ou panel ouvert ─────────────────     │  E   │
 *   │   │  live token stream / last reply  │       │  R   │
 *   │   │  [▼ RÉDUIRE]  [VOIX AUTO] [▶]   │       │  S   │
 *   │   └──────────────────────────────────┘       │  A   │
 *   │              [ InputArea ]                  │      │
 *   └─────────────────────────────────────────────┴──────┘
 *
 * Transcript panel : collapsed (strip) par défaut.
 *   • S'ouvre automatiquement quand JARVIS commence à répondre.
 *   • Cliquable pour expand / collapse à tout moment.
 *   • Sidebar conversation : même comportement, collapsed par défaut.
 */
export function JarvisChatPage() {
  const messages         = useAppStore((s) => s.messages);
  const streamState      = useAppStore((s) => s.streamState);
  const selectedModel    = useAppStore((s) => s.selectedModel);
  const models           = useAppStore((s) => s.models);
  const setSelectedModel = useAppStore((s) => s.setSelectedModel);

  const speaking      = streamState.isStreaming;
  const listRef       = useRef<HTMLDivElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  // ── Panel states (both start collapsed) ────────────────────────────────
  const [sidebarOpen,     setSidebarOpen]     = useState(false);
  const [transcriptOpen,  setTranscriptOpen]  = useState(false);
  const [modelPickerOpen, setModelPickerOpen] = useState(false);
  const [ttsPlaying,      setTtsPlaying]      = useState(false);
  const [ttsEnabled,      setTtsEnabled]      = useState(true);

  const ttsAudioRef  = useRef<HTMLAudioElement | null>(null);
  const ttsUrlRef    = useRef<string | null>(null);
  const prevStreaming = useRef(false);

  const empty        = messages.length === 0 && !streamState.isStreaming;
  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant' && m.content);
  const liveText     = speaking ? streamState.content : (lastAssistant?.content ?? '');
  const estTokens    = Math.round((streamState.content?.length ?? 0) / 4);

  const _CLOUD  = ['gpt-', 'o1-', 'o3-', 'claude-', 'gemini-', 'openrouter/'];
  const isLocal = selectedModel ? !_CLOUD.some((p) => selectedModel.startsWith(p)) : false;
  const modelLabel = selectedModel
    ? (selectedModel.split('/').pop() ?? selectedModel)
    : 'NO MODEL';

  // ── Auto-open transcript when JARVIS starts streaming ──────────────────
  useEffect(() => {
    if (speaking) setTranscriptOpen(true);
  }, [speaking]);

  // ── Auto-scroll transcript ──────────────────────────────────────────────
  useEffect(() => {
    if (transcriptRef.current && speaking && transcriptOpen) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [streamState.content, speaking, transcriptOpen]);

  // ── Auto-scroll sidebar ────────────────────────────────────────────────
  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, streamState.content, sidebarOpen]);

  // ── Close model picker on outside click ────────────────────────────────
  useEffect(() => {
    if (!modelPickerOpen) return;
    const handler = () => setModelPickerOpen(false);
    window.addEventListener('click', handler);
    return () => window.removeEventListener('click', handler);
  }, [modelPickerOpen]);

  // ── TTS ────────────────────────────────────────────────────────────────
  const speakText = useCallback(async (text: string) => {
    if (!text.trim()) return;
    ttsAudioRef.current?.pause();
    if (ttsUrlRef.current) { URL.revokeObjectURL(ttsUrlRef.current); ttsUrlRef.current = null; }
    ttsAudioRef.current = null;
    const clean = text
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`[^`]+`/g, '')
      .replace(/#{1,6}\s/g, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .trim()
      .slice(0, 2000);
    if (!clean) return;
    setTtsPlaying(true);
    try {
      const res = await fetch(`${getBase()}/v1/tts?text=${encodeURIComponent(clean)}`);
      if (!res.ok) throw new Error(`TTS ${res.status}`);
      const blob  = await res.blob();
      const url   = URL.createObjectURL(blob);
      ttsUrlRef.current = url;
      const audio = new Audio(url);
      ttsAudioRef.current = audio;
      audio.onended = () => { URL.revokeObjectURL(url); ttsUrlRef.current = null; ttsAudioRef.current = null; setTtsPlaying(false); };
      audio.onerror = () => { if (ttsUrlRef.current) { URL.revokeObjectURL(ttsUrlRef.current); ttsUrlRef.current = null; } ttsAudioRef.current = null; setTtsPlaying(false); };
      await audio.play();
    } catch { setTtsPlaying(false); }
  }, []);

  const stopTts = useCallback(() => {
    ttsAudioRef.current?.pause();
    if (ttsUrlRef.current) { URL.revokeObjectURL(ttsUrlRef.current); ttsUrlRef.current = null; }
    ttsAudioRef.current = null;
    setTtsPlaying(false);
  }, []);

  // ── Auto-play TTS on stream end ────────────────────────────────────────
  useEffect(() => {
    const wasStreaming = prevStreaming.current;
    prevStreaming.current = speaking;
    if (wasStreaming && !speaking && ttsEnabled) {
      const last = [...messages].reverse().find((m) => m.role === 'assistant' && m.content);
      if (last?.content) speakText(last.content);
    }
  }, [speaking, messages, ttsEnabled, speakText]);

  // ── Collapsed transcript strip (preview of response) ───────────────────
  const transcriptStrip = liveText ? (
    <button
      onClick={() => setTranscriptOpen(true)}
      className="w-full shrink-0 flex items-center gap-2 px-3 py-2 cursor-pointer"
      style={{
        maxWidth:   700,
        background: 'rgba(0,0,0,0.22)',
        border:     `1px solid ${speaking ? 'var(--color-jarvis)' : 'var(--hud-border)'}`,
        transition: 'border-color 0.3s',
      }}
      title="Afficher la réponse"
    >
      <ChevronUp size={10} style={{ color: speaking ? 'var(--color-jarvis)' : 'var(--hud-text-dim)', flexShrink: 0 }} />
      <span
        className="text-[10px] flex-1 text-left truncate"
        style={{ color: speaking ? 'var(--color-jarvis)' : 'var(--hud-text)', fontFamily: 'inherit' }}
      >
        {liveText.replace(/\n/g, ' ').slice(0, 90)}
        {speaking && <span className="animate-pulse ml-0.5" style={{ color: 'var(--color-jarvis)' }}>▊</span>}
      </span>
      <span className="text-[8px] shrink-0" style={{ color: 'var(--hud-text-dim)' }}>
        {liveText.length} chars
      </span>
    </button>
  ) : speaking ? (
    <StreamingDots phase={streamState.phase} />
  ) : null;

  // ── Expanded transcript panel ───────────────────────────────────────────
  const transcriptPanel = (
    <div className="w-full flex flex-col gap-0 shrink-0" style={{ maxWidth: 700 }}>
      {/* Header bar: collapse btn + TTS controls */}
      <div
        className="flex items-center gap-2 px-3 py-1.5 shrink-0"
        style={{
          background:   'rgba(0,0,0,0.22)',
          border:       `1px solid ${speaking ? 'var(--color-jarvis)' : ttsPlaying ? 'var(--color-jarvis)' : 'var(--hud-border)'}`,
          borderBottom: 'none',
          transition:   'border-color 0.3s',
        }}
      >
        {/* Collapse button */}
        <button
          onClick={() => setTranscriptOpen(false)}
          className="flex items-center gap-1 text-[8px] font-bold tracking-[0.2em] cursor-pointer shrink-0"
          style={{ color: 'var(--hud-text-dim)' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-jarvis)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--hud-text-dim)')}
          title="Réduire"
        >
          <ChevronDown size={9} />
          <span>RÉDUIRE</span>
        </button>

        <span
          className="text-[8px] font-bold tracking-[0.2em] ml-1"
          style={{ color: speaking ? 'var(--color-jarvis)' : 'var(--hud-text-dim)' }}
        >
          {speaking ? `${(streamState.elapsedMs / 1000).toFixed(1)}s · ~${estTokens} tok` : `${liveText.length} chars`}
        </span>

        <div className="flex-1" />

        {/* TTS toggle */}
        <button
          onClick={() => setTtsEnabled((v) => !v)}
          className="flex items-center gap-1 text-[8px] font-bold tracking-[0.2em] cursor-pointer"
          style={{ color: ttsEnabled ? 'var(--color-jarvis)' : 'var(--hud-text-dim)' }}
          title={ttsEnabled ? 'Désactiver auto-voix' : 'Activer auto-voix'}
        >
          {ttsEnabled ? <Volume2 size={9} /> : <VolumeX size={9} />}
          <span>{ttsEnabled ? 'VOIX' : 'OFF'}</span>
        </button>

        {/* Play / Stop TTS */}
        {!speaking && liveText && (
          <button
            onClick={() => ttsPlaying ? stopTts() : speakText(liveText)}
            className="flex items-center gap-1 text-[8px] font-bold tracking-[0.2em] cursor-pointer"
            style={{ color: ttsPlaying ? 'var(--color-jarvis)' : 'var(--hud-text-dim)' }}
            title={ttsPlaying ? 'Arrêter' : 'Écouter'}
          >
            {ttsPlaying ? <VolumeX size={9} /> : <Volume2 size={9} />}
            <span>{ttsPlaying ? 'STOP' : '▶'}</span>
          </button>
        )}
      </div>

      {/* Transcript body */}
      <div
        ref={transcriptRef}
        className="w-full overflow-y-auto px-4 py-3 text-[13px] leading-relaxed"
        style={{
          maxHeight:  240,
          background: 'rgba(0,0,0,0.28)',
          border:     `1px solid ${speaking ? 'var(--color-jarvis)' : ttsPlaying ? 'var(--color-jarvis)' : 'var(--hud-border)'}`,
          color:      'var(--hud-text)',
          fontFamily: 'inherit',
          whiteSpace: 'pre-wrap',
          wordBreak:  'break-word',
          transition: 'border-color 0.3s ease',
        }}
      >
        {liveText}
        {speaking && (
          <span className="animate-pulse" style={{ color: 'var(--color-jarvis)', marginLeft: 1 }}>▊</span>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex h-full" style={{ background: 'var(--hud-bg)' }}>

      {/* ══ Centre stage ════════════════════════════════════════════════════ */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* ── Model selector pill ─────────────────────────────────────────── */}
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

        {/* ── Orb + status + transcript (collapsed or expanded) ───────────── */}
        <div className="flex-1 flex flex-col items-center justify-center gap-4 min-h-0 px-6 overflow-hidden">

          {/* Orb — taille fixe */}
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

          {/* Transcript — collapsed strip OR expanded panel */}
          {transcriptOpen
            ? transcriptPanel
            : empty
              ? (
                <div className="text-[9px] tracking-[0.2em] text-center" style={{ color: 'var(--hud-text-dim)' }}>
                  PARLE OU ÉCRIS À JARVIS
                </div>
              )
              : transcriptStrip
          }
        </div>

        <InputArea />
      </main>

      {/* ══ Conversation sidebar (right) — collapsible ══════════════════════ */}
      <aside
        className="flex flex-col shrink-0 overflow-hidden"
        style={{
          width:      sidebarOpen ? 400 : 46,
          background: 'var(--hud-bg-elev)',
          borderLeft: '1px solid var(--hud-border)',
          transition: 'width 0.22s ease',
        }}
      >
        {!sidebarOpen ? (
          <button
            onClick={() => setSidebarOpen(true)}
            title="Afficher la conversation complète"
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
              <span className="text-[8px] px-1 py-0.5" style={{ border: '1px solid var(--hud-border)', color: 'var(--hud-text-dim)' }}>
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
                  color:    speaking ? 'var(--color-jarvis)' : 'var(--hud-text-dim)',
                  border:   `1px solid ${speaking ? 'var(--color-jarvis)' : 'var(--hud-border)'}`,
                }}
              >
                {speaking ? 'LIVE' : `${messages.length} MSG`}
              </span>
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

            <div ref={listRef} className="flex-1 overflow-y-auto px-3 py-3 flex flex-col">
              {empty ? (
                <div
                  className="m-auto text-center px-4 text-[10px] tracking-[0.22em] leading-relaxed"
                  style={{ color: 'var(--hud-text-dim)' }}
                >
                  AUCUN MESSAGE<br />PARLE OU ÉCRIS À JARVIS
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

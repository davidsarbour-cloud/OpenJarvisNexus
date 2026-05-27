/**
 * Nexus9 — NexusBootIntro.
 *
 * Full-screen splash overlay that plays once per backend boot. The
 * frontend compares `boot_id` from `GET /v1/boot/info` with whatever
 * it last persisted in localStorage:
 *   - identical → resolves immediately (no flash, no skip needed),
 *   - different (or no record yet) → renders the overlay until the
 *     video ends, the user clicks SKIP, or hits Esc/click anywhere.
 *
 * Asset resolution:
 *   1. Try `/intro/boot.mp4` (then `.webm` as fallback). If the file
 *      404s the placeholder HUD takes over — no manual config needed.
 *   2. Placeholder = self-contained styled boot sequence (wordmark,
 *      scan lines, terminal trace, progress bar). Ships in the bundle
 *      so the overlay never shows a broken-image state.
 */
import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { getBase } from '../../lib/api';

const STORAGE_KEY = 'nexus9.intro.boot-id';

interface NexusBootIntroProps {
  /** Called when the intro is done (video ended, user skipped, or no
   *  intro needed because boot_id matched the cached one). The HUD
   *  is wrapped in a sibling and remains mounted underneath. */
  onComplete: () => void;
}

type Phase = 'checking' | 'video' | 'placeholder' | 'done';

export function NexusBootIntro({ onComplete }: NexusBootIntroProps) {
  const [phase, setPhase] = useState<Phase>('checking');
  const [bootId, setBootId] = useState<string>('');
  const videoRef = useRef<HTMLVideoElement>(null);
  const completedRef = useRef(false);

  // Step 1 — fetch the backend boot_id and decide whether to play.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      let serverBootId = '';
      try {
        const r = await fetch(`${getBase()}/v1/boot/info`);
        if (r.ok) {
          const data = (await r.json()) as { boot_id?: string };
          serverBootId = data.boot_id ?? '';
        }
      } catch {
        // Backend unreachable → don't block the UI behind the intro,
        // just resolve so the SPA loads normally.
        if (!cancelled) finish();
        return;
      }
      if (cancelled) return;

      const cached = (() => {
        try { return localStorage.getItem(STORAGE_KEY) ?? ''; }
        catch { return ''; }
      })();

      if (serverBootId && serverBootId !== cached) {
        setBootId(serverBootId);
        setPhase('video');     // try video first; falls through to placeholder onError
      } else {
        finish();              // same boot_id → skip
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function finish() {
    if (completedRef.current) return;
    completedRef.current = true;
    if (bootId) {
      try { localStorage.setItem(STORAGE_KEY, bootId); }
      catch { /* private mode — silently ignore */ }
    }
    setPhase('done');
    onComplete();
  }

  // Esc + click to skip — only while overlay is visible.
  useEffect(() => {
    if (phase === 'done' || phase === 'checking') return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        finish();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  // While we haven't decided yet, render nothing — fetch is fast and the
  // HUD underneath is already mounting. Showing a flicker of overlay
  // before knowing whether we need it is worse than waiting one tick.
  if (phase === 'checking' || phase === 'done') {
    return <AnimatePresence />;
  }

  return (
    <AnimatePresence>
      <motion.div
        key="boot-overlay"
        role="dialog"
        aria-label="Nexus9 boot sequence"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{    opacity: 0 }}
        transition={{ duration: 0.4 }}
        onClick={finish}
        className="fixed inset-0 z-[9999] flex items-center justify-center overflow-hidden"
        style={{
          background: '#02050b',
          cursor: 'pointer',
          fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
        }}
      >
        {phase === 'video' ? (
          <video
            ref={videoRef}
            src="/intro/boot.mp4"
            autoPlay
            muted
            playsInline
            onEnded={finish}
            onError={() => setPhase('placeholder')}
            className="absolute inset-0 w-full h-full"
            style={{ objectFit: 'cover' }}
          />
        ) : (
          <PlaceholderSequence onDone={finish} />
        )}

        {/* SKIP hint (top-right) — kept low-key so the cinematic feel
            stays intact, but always reachable. */}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); finish(); }}
          className="absolute top-4 right-5 px-2 py-1 text-[9px] tracking-[0.3em] transition-colors"
          style={{
            color: 'var(--hud-text-dim)',
            border: '1px solid var(--hud-border)',
            background: 'rgba(0,0,0,0.45)',
            backdropFilter: 'blur(2px)',
            borderRadius: 2,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = 'var(--color-jarvis)';
            e.currentTarget.style.borderColor = 'var(--color-jarvis)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--hud-text-dim)';
            e.currentTarget.style.borderColor = 'var(--hud-border)';
          }}
        >
          SKIP · ESC
        </button>
      </motion.div>
    </AnimatePresence>
  );
}

// ── Placeholder boot sequence ───────────────────────────────────────────────
//
// Self-contained HUD aesthetic: NEXUS9 wordmark fade-in, animated scan
// lines, a fake terminal trace that types out boot lines, and a progress
// bar that ramps to 100% in ~4 seconds. Plays once, then calls onDone.
// No external asset required — this is the fallback when boot.mp4 is
// missing or fails to load.

const TRACE_LINES = [
  '> NEXUS9 BOOT SEQUENCE INITIATED',
  '> mounting orbital subsystems         [ok]',
  '> handshake jarvis · ultron · forge   [ok]',
  '> warming qwen3:14b on local gpu      [ok]',
  '> chromadb vector store online        [ok]',
  '> hud telemetry stream connected      [ok]',
  '> WELCOME, DAVID.',
];

function PlaceholderSequence({ onDone }: { onDone: () => void }) {
  const [traceIdx, setTraceIdx] = useState(0);
  const [progress, setProgress] = useState(0);
  const totalMs = 4200;

  useEffect(() => {
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / totalMs);
      setProgress(p);
      const desiredIdx = Math.min(
        TRACE_LINES.length,
        Math.floor(p * (TRACE_LINES.length + 0.2)),
      );
      setTraceIdx(desiredIdx);
      if (p < 1) raf = requestAnimationFrame(tick);
      else setTimeout(onDone, 350);  // hold finished frame briefly
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [onDone]);

  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
      {/* Backdrop tint */}
      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at 50% 50%, rgba(0,212,255,0.05) 0%, transparent 70%), #02050b',
        }}
      />

      {/* Low-amplitude CRT scan lines */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(0,212,255,0.03) 3px, rgba(0,212,255,0.03) 4px)',
          mixBlendMode: 'overlay',
        }}
      />

      {/* Wordmark + trace + progress, stacked center */}
      <div className="relative flex flex-col items-center gap-8 px-8 max-w-[640px] w-full">
        <motion.div
          initial={{ opacity: 0, letterSpacing: '0.1em' }}
          animate={{ opacity: 1, letterSpacing: '0.55em' }}
          transition={{ duration: 1.4, ease: 'easeOut' }}
          className="text-4xl sm:text-5xl font-bold"
          style={{
            color: 'var(--color-jarvis)',
            textShadow: '0 0 24px rgba(0,212,255,0.55), 0 0 60px rgba(0,212,255,0.25)',
          }}
        >
          NEXUS9
        </motion.div>

        <div className="text-[10px] tracking-[0.32em]"
             style={{ color: 'var(--hud-text-dim)' }}>
          ◆ OPENJARVIS COMMAND CENTER ◆
        </div>

        {/* Terminal trace */}
        <div
          className="w-full flex flex-col gap-1 px-3 py-2 text-[10.5px] leading-relaxed"
          style={{
            color: 'var(--hud-text)',
            background: 'rgba(0,0,0,0.4)',
            border: '1px solid var(--hud-border)',
            borderLeft: '2px solid var(--color-jarvis)',
            minHeight: 132,
            borderRadius: 3,
          }}
        >
          {TRACE_LINES.slice(0, traceIdx).map((line, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25 }}
              style={{
                color: i === TRACE_LINES.length - 1
                  ? 'var(--color-docker)'
                  : 'var(--hud-text)',
                fontWeight: i === TRACE_LINES.length - 1 ? 700 : 400,
              }}
            >
              {line}
            </motion.div>
          ))}
          {traceIdx < TRACE_LINES.length && (
            <span
              aria-hidden
              style={{
                display: 'inline-block',
                width: 7, height: 12,
                background: 'var(--color-jarvis)',
                animation: 'boot-caret 0.9s steps(2) infinite',
                alignSelf: 'flex-start',
              }}
            />
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full flex flex-col gap-1">
          <div className="flex justify-between text-[9px] tracking-[0.25em]"
               style={{ color: 'var(--hud-text-dim)' }}>
            <span>INITIALIZATION</span>
            <span style={{ color: 'var(--color-jarvis)' }}>
              {Math.round(progress * 100).toString().padStart(3, '0')} %
            </span>
          </div>
          <div
            className="w-full overflow-hidden"
            style={{
              height: 4,
              background: 'rgba(0,212,255,0.08)',
              border: '1px solid var(--hud-border)',
              borderRadius: 2,
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${progress * 100}%`,
                background: 'linear-gradient(90deg, var(--color-jarvis) 0%, var(--color-docker) 100%)',
                boxShadow: '0 0 8px rgba(0,212,255,0.7)',
                transition: 'width 80ms linear',
              }}
            />
          </div>
        </div>
      </div>

      <style>{`
        @keyframes boot-caret {
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}

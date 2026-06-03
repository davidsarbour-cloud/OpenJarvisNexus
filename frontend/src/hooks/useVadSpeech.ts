import { useCallback, useRef, useState } from 'react';
import { transcribeAudio } from '../lib/api';

/**
 * useVadSpeech — hands-free single utterance capture with Voice Activity
 * Detection. listenOnce() opens the mic, waits for the user to speak, then
 * auto-stops after a short silence, transcribes, and resolves the text.
 * Resolves '' if no speech was detected (timeout) or if aborted.
 *
 * Pure Web Audio (AnalyserNode RMS) — no extra dependency.
 */
const SPEECH_RMS = 0.018;     // above this = voice
const SILENCE_MS = 1200;      // silence after speech ends the turn
const NO_SPEECH_MS = 8000;    // give up if the user never speaks
const MAX_TURN_MS = 20000;    // hard cap on one utterance

export type VadState = 'idle' | 'listening' | 'speaking' | 'transcribing';

export function useVadSpeech() {
  const [state, setState] = useState<VadState>('idle');
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef   = useRef<MediaStream | null>(null);
  const ctxRef      = useRef<AudioContext | null>(null);
  const rafRef      = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortedRef  = useRef(false);

  const cleanup = useCallback(() => {
    if (rafRef.current) { clearInterval(rafRef.current); rafRef.current = null; }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    ctxRef.current?.close().catch(() => {});
    ctxRef.current = null;
    recorderRef.current = null;
  }, []);

  const listenOnce = useCallback(async (): Promise<string> => {
    abortedRef.current = false;
    if (!navigator.mediaDevices?.getUserMedia) return '';

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      return '';
    }
    streamRef.current = stream;

    const mimes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    const mimeType = mimes.find((m) => MediaRecorder.isTypeSupported(m)) ?? '';
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorderRef.current = recorder;
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

    // Web Audio analyser for RMS-based VAD
    const ctx = new AudioContext();
    ctxRef.current = ctx;
    const src = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    src.connect(analyser);
    const buf = new Uint8Array(analyser.fftSize);

    setState('listening');

    return new Promise<string>((resolve) => {
      let settled = false;
      const startTime = Date.now();
      let speechDetected = false;
      let lastVoice = startTime;

      const finish = (transcribeIt: boolean) => {
        if (settled) return;
        settled = true;
        if (rafRef.current) { clearInterval(rafRef.current); rafRef.current = null; }
        recorder.onstop = async () => {
          if (abortedRef.current || !transcribeIt || chunks.length === 0) {
            cleanup(); setState('idle'); resolve(''); return;
          }
          setState('transcribing');
          try {
            const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
            const r = await transcribeAudio(blob);
            cleanup(); setState('idle'); resolve((r.text || '').trim());
          } catch {
            cleanup(); setState('idle'); resolve('');
          }
        };
        try { recorder.stop(); } catch { cleanup(); setState('idle'); resolve(''); }
      };

      rafRef.current = setInterval(() => {
        if (abortedRef.current) { finish(false); return; }
        analyser.getByteTimeDomainData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v; }
        const rms = Math.sqrt(sum / buf.length);
        const now = Date.now();

        if (rms > SPEECH_RMS) {
          if (!speechDetected) { speechDetected = true; setState('speaking'); }
          lastVoice = now;
        }
        if (speechDetected && now - lastVoice > SILENCE_MS) { finish(true); return; }
        if (!speechDetected && now - startTime > NO_SPEECH_MS) { finish(false); return; }
        if (now - startTime > MAX_TURN_MS) { finish(speechDetected); return; }
      }, 80);

      recorder.start();
    });
  }, [cleanup]);

  const abort = useCallback(() => {
    abortedRef.current = true;
    try { recorderRef.current?.stop(); } catch { /* ignore */ }
    cleanup();
    setState('idle');
  }, [cleanup]);

  return { state, listenOnce, abort, listening: state !== 'idle' };
}

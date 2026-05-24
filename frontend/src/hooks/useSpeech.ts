import { useState, useCallback, useRef, useEffect } from 'react';
import { transcribeAudio, fetchSpeechHealth } from '../lib/api';

export type SpeechState = 'idle' | 'recording' | 'transcribing';

export function useSpeech() {
  const [state, setState] = useState<SpeechState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [available, setAvailable] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);
  const streamRef        = useRef<MediaStream | null>(null);

  /** Set to true by cancelRecording() — onstop checks this flag. */
  const cancelledRef = useRef(false);

  /**
   * resolve/reject for the Promise returned by stopRecording().
   * Declared early (before startRecording) to avoid any closure ordering ambiguity.
   */
  const resolveRef = useRef<((text: string) => void) | null>(null);
  const rejectRef  = useRef<((err: unknown) => void) | null>(null);

  /** Clean up pending stopRecording promise (cancel or error path). */
  const rejectPending = useCallback((reason: string) => {
    if (rejectRef.current) {
      rejectRef.current(new Error(reason));
      resolveRef.current = null;
      rejectRef.current  = null;
    }
  }, []);

  // Check if speech backend is available on mount
  useEffect(() => {
    fetchSpeechHealth()
      .then((health) => setAvailable(health.available))
      .catch(() => setAvailable(false));
  }, []);

  const startRecording = useCallback(async (): Promise<void> => {
    // Bug 2 fix: guard against re-entry
    if (mediaRecorderRef.current?.state === 'recording') return;

    setError(null);
    cancelledRef.current = false;

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone not supported in this browser');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Pick the best supported MIME type (Bug 4 partial fix: prefer opus)
      const preferredMimes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
      const mimeType = preferredMimes.find((m) => MediaRecorder.isTypeSupported(m)) ?? '';

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        // Stop all audio tracks regardless of cancel/confirm
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        if (cancelledRef.current) {
          // Bug 3 fix: clean up pending promise before discarding
          rejectPending('Recording cancelled');
          chunksRef.current  = [];
          cancelledRef.current = false;
          setState('idle');
          return;
        }

        setState('transcribing');
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        chunksRef.current = [];

        try {
          const result = await transcribeAudio(blob);
          setState('idle');
          resolveRef.current?.(result.text);
        } catch (err) {
          setState('idle');
          const msg = err instanceof Error ? err.message : 'Transcription failed';
          setError(msg);
          rejectRef.current?.(err);
        } finally {
          resolveRef.current = null;
          rejectRef.current  = null;
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setState('recording');
    } catch {
      setError('Microphone access denied');
      setState('idle');
    }
  }, [rejectPending]);

  const stopRecording = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state !== 'recording') {
        reject(new Error('Not recording'));
        return;
      }
      resolveRef.current   = resolve;
      rejectRef.current    = reject;
      cancelledRef.current = false;
      recorder.stop();
    });
  }, []);

  /** Stop the recorder and discard the audio — no transcription call. */
  const cancelRecording = useCallback((): void => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state !== 'recording') return;
    cancelledRef.current = true;
    recorder.stop();
  }, []);

  return {
    state,
    error,
    available,
    startRecording,
    stopRecording,
    cancelRecording,
    isRecording:    state === 'recording',
    isTranscribing: state === 'transcribing',
  };
}

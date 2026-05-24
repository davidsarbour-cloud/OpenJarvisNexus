import { useState, useCallback, useRef, useEffect } from 'react';
import { transcribeAudio, fetchSpeechHealth } from '../lib/api';

export type SpeechState = 'idle' | 'recording' | 'transcribing';

export function useSpeech() {
  const [state, setState] = useState<SpeechState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [available, setAvailable] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  // When true, the next `onstop` event discards audio instead of transcribing.
  const cancelledRef = useRef(false);

  // Check if speech backend is available on mount
  useEffect(() => {
    fetchSpeechHealth()
      .then((health) => setAvailable(health.available))
      .catch(() => setAvailable(false));
  }, []);

  const startRecording = useCallback(async (): Promise<void> => {
    setError(null);
    cancelledRef.current = false;

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone not supported in this browser');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        // Stop all audio tracks regardless of cancel/confirm
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        if (cancelledRef.current) {
          // Discard audio, return to idle without calling backend
          chunksRef.current = [];
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
          // Resolved via the stopRecording promise
          resolveRef.current?.(result.text);
        } catch (err) {
          setState('idle');
          const msg = err instanceof Error ? err.message : 'Transcription failed';
          setError(msg);
          rejectRef.current?.(err);
        } finally {
          resolveRef.current = null;
          rejectRef.current = null;
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setState('recording');
    } catch {
      setError('Microphone access denied');
      setState('idle');
    }
  }, []);

  // Refs to pass resolve/reject out of the onstop closure
  const resolveRef = useRef<((text: string) => void) | null>(null);
  const rejectRef  = useRef<((err: unknown) => void) | null>(null);

  const stopRecording = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state !== 'recording') {
        reject(new Error('Not recording'));
        return;
      }
      resolveRef.current = resolve;
      rejectRef.current  = reject;
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
    isRecording:     state === 'recording',
    isTranscribing:  state === 'transcribing',
  };
}

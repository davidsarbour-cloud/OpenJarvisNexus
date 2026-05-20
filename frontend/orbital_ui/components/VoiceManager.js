/**
 * VoiceManager — mic input (Whisper STT) + TTS output (edge-tts).
 * Exact same endpoints as the legacy Nexus9 system.
 * /v1/speech/transcribe  — Whisper local
 * /v1/tts                — edge-tts
 */

const BACKEND = 'http://localhost:8000';

export class VoiceManager {
  constructor({ onTranscript, onTTSStart, onTTSEnd, onStatus }) {
    this.onTranscript = onTranscript;
    this.onTTSStart   = onTTSStart;
    this.onTTSEnd     = onTTSEnd;
    this.onStatus     = onStatus;

    this.micStream   = null;
    this.recorder    = null;
    this.chunks      = [];
    this.recording   = false;
    this.cancelled   = false;
    this.startTime   = 0;

    this.ttsEnabled  = localStorage.getItem('nexus9_tts') !== 'off';
    this.ttsAudio    = null;
    this._ttsQueue   = [];
    this._micStream  = null;

    this.available   = !!(navigator.mediaDevices?.getUserMedia) && location.protocol !== 'file:';

    // Cleanup propre à la fermeture de page
    window.addEventListener('beforeunload', () => this.destroy());
  }

  // ── TTS ──────────────────────────────────────────────

  async speak(text, agent = 'JARVIS') {
    if (!this.ttsEnabled || !text.trim()) return;

    // Si une lecture est déjà en cours, on met en queue
    if (this.ttsAudio) {
      this._ttsQueue.push({ text, agent });
      return;
    }

    // Voice mapping (same as legacy jvSay)
    const voiceMap = {
      JARVIS:  'en-US-GuyNeural',
      ULTRON:  'en-US-ChristopherNeural',
      QWEN:    'en-US-EricNeural',
      CORTANA: 'en-US-SteffanNeural',
      BRUCE:   'en-US-BrianNeural',
    };
    const voice = voiceMap[agent] || voiceMap.JARVIS;

    // Sanitize (same as legacy)
    let t = text
      .replace(/<think>[\s\S]*?<\/think>/gi, '')
      .replace(/```[\s\S]*?```/g, '')
      .replace(/`[^`\n]+`/g, '')
      .replace(/[*_]{1,3}([^*_]+)[*_]{1,3}/g, '$1')
      .replace(/\n+/g, ' ')
      .trim();
    const parts = t.split(/(?<=[.!?])\s+/).filter(Boolean);
    if (parts.length > 2) t = parts.slice(0, 2).join(' ');
    if (!t) return;

    try {
      this.onTTSStart?.(agent);
      const params = new URLSearchParams({ text: t, voice });
      const r = await fetch(`${BACKEND}/v1/tts?${params}`, {
        signal: AbortSignal.timeout(15000),
      });
      if (!r.ok) throw new Error('TTS HTTP ' + r.status);
      const blob = await r.blob();
      const url  = URL.createObjectURL(blob);
      this.ttsAudio = new Audio(url);
      this.ttsAudio.onended = () => {
        URL.revokeObjectURL(url);
        this.ttsAudio = null;
        this.onTTSEnd?.(agent);
        // Joue le prochain élément de la queue si présent
        if (this._ttsQueue.length > 0) {
          const next = this._ttsQueue.shift();
          this.speak(next.text, next.agent);
        }
      };
      this.ttsAudio.onerror = () => {
        URL.revokeObjectURL(url);
        this.ttsAudio = null;
        this.onTTSEnd?.(agent);
        // Joue le prochain même en cas d'erreur
        if (this._ttsQueue.length > 0) {
          const next = this._ttsQueue.shift();
          this.speak(next.text, next.agent);
        }
      };
      await this.ttsAudio.play();
    } catch (e) {
      console.warn('[TTS] failed:', e.message);
      this.ttsAudio = null;
      this.onTTSEnd?.(agent);
      // Joue le prochain même en cas d'erreur fetch
      if (this._ttsQueue.length > 0) {
        const next = this._ttsQueue.shift();
        this.speak(next.text, next.agent);
      }
    }
  }

  stopSpeaking() {
    if (this.ttsAudio) {
      this.ttsAudio.pause();
      this.ttsAudio = null;
    }
    this._ttsQueue = [];
  }

  setTTS(enabled) {
    this.ttsEnabled = enabled;
    localStorage.setItem('nexus9_tts', enabled ? 'on' : 'off');
    if (!enabled) this.stopSpeaking();
  }

  // ── Cleanup global ────────────────────────────────────

  destroy() {
    this.stopSpeaking();
    this.cancelRecording();
    this._micStream?.getTracks().forEach(t => t.stop());
    this._micStream = null;
  }

  // ── Mic / STT ─────────────────────────────────────────

  async startRecording() {
    if (!this.available) {
      this.onStatus?.('mic_unavailable');
      return;
    }
    if (this.recording) { await this.stopRecording(); return; }

    try {
      this.micStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 },
      });
      this._micStream = this.micStream; // alias pour destroy()
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus' : 'audio/webm';

      this.recorder = new MediaRecorder(this.micStream, { mimeType });
      this.chunks   = [];
      this.cancelled = false;
      this.startTime = Date.now();

      this.recorder.ondataavailable = e => { if (e.data.size > 0) this.chunks.push(e.data); };
      this.recorder.onstop = () => this._onStop(mimeType);
      this.recorder.start();
      this.recording = true;
      this.onStatus?.('recording');
    } catch (e) {
      this.recording = false;
      if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') {
        this.available = false;
        this.onStatus?.('mic_blocked');
      } else {
        this.onStatus?.('mic_error', e.message);
      }
    }
  }

  async stopRecording() {
    if (!this.recording || !this.recorder) return;
    const elapsed = Date.now() - this.startTime;
    if (elapsed < 1200) await new Promise(r => setTimeout(r, 1200 - elapsed));
    this.recorder.stop();
    this.recording = false;
    this._cleanup();
  }

  cancelRecording() {
    this.cancelled = true;
    if (this.recorder?.state === 'recording') this.recorder.stop();
    this.recording = false;
    this._cleanup();
    this.onStatus?.('cancelled');
  }

  _cleanup() {
    this.micStream?.getTracks().forEach(t => t.stop());
    this.micStream = null;
    this._micStream = null;
  }

  async _onStop(mimeType) {
    if (this.cancelled) { this.chunks = []; return; }
    const blob = new Blob(this.chunks.length ? this.chunks : [new Uint8Array(0)], { type: mimeType });
    this.chunks = [];
    this.onStatus?.('transcribing');
    try {
      const fd = new FormData();
      fd.append('file', blob, 'recording.webm');
      const r = await fetch(`${BACKEND}/v1/speech/transcribe`, {
        method: 'POST', body: fd, signal: AbortSignal.timeout(25000),
      });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const d = await r.json();
      if (d.text?.trim()) {
        this.onTranscript?.(d.text.trim());
        this.onStatus?.('idle');
      } else {
        this.onStatus?.('nothing_heard');
      }
    } catch (e) {
      this.onStatus?.('transcribe_error', e.message);
    }
  }
}

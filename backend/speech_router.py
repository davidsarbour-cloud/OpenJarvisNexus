"""Speech endpoints — text-to-speech (Edge/Kokoro) and speech-to-text (Whisper).

Extracted from main.py. Self-contained: owns its Kokoro/Whisper model caches;
no shared app state.
"""

import os
import tempfile

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from memory import load_config

router = APIRouter(tags=["speech"])

# ── Kokoro pipeline cache (un par lang_code, chargé une seule fois) ─────────
_kokoro_pipelines: dict = {}


def _get_kokoro_pipeline(lang_code: str):
    """Retourne le KPipeline mis en cache pour ce lang_code."""
    if lang_code not in _kokoro_pipelines:
        from kokoro import KPipeline
        _kokoro_pipelines[lang_code] = KPipeline(lang_code=lang_code)
    return _kokoro_pipelines[lang_code]


def _run_kokoro_sync(text: str, tts_voice: str) -> bytes:
    """Inference Kokoro synchrone — à appeler via asyncio.to_thread()."""
    import io as _io

    import numpy as np
    import soundfile as sf
    lang_code = tts_voice[0] if tts_voice else "b"
    pipeline = _get_kokoro_pipeline(lang_code)
    chunks = []
    for _, _, audio in pipeline(text, voice=tts_voice, speed=1.0):
        chunks.append(audio)
    if not chunks:
        raise RuntimeError("Kokoro n'a produit aucun audio")
    full_audio = np.concatenate(chunks)
    buf = _io.BytesIO()
    sf.write(buf, full_audio, 24000, format="WAV")
    return buf.getvalue()


@router.get("/v1/tts")
async def text_to_speech(
    text: str = Query(..., description="Texte à lire"),
    voice: str = Query(None, description="Override voix (défaut: config.json)"),
    engine: str = Query(None, description="Override moteur: 'edge' ou 'kokoro' (défaut: config.json)"),
):
    """Synthèse vocale — Edge TTS (gratuit, cloud) ou Kokoro (local, offline)."""
    import asyncio

    cfg = load_config().get("jarvis", {})

    tts_engine = engine or cfg.get("tts_engine", "edge")
    text = text[:4000].strip()   # Bug fix: limite portée à 4000 chars
    if not text:
        raise HTTPException(400, "Texte vide")

    # ── Kokoro (local, offline) ──────────────────────────────────────────────
    if tts_engine == "kokoro":
        tts_voice = voice or cfg.get("tts_voice_kokoro", "bm_george")
        try:
            import kokoro  # noqa: F401
            import soundfile  # noqa: F401
        except ImportError:
            raise HTTPException(503, "Kokoro non installé — lance: pip install kokoro soundfile")

        try:
            # Bug fix: asyncio.to_thread évite de bloquer l'event loop FastAPI
            audio_bytes = await asyncio.to_thread(_run_kokoro_sync, text, tts_voice)
        except RuntimeError as e:
            raise HTTPException(503, str(e))

        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=jarvis.wav"},
        )

    # ── Edge TTS (cloud Microsoft, gratuit) ─────────────────────────────────
    tts_voice = voice or cfg.get("tts_voice_edge", "fr-CA-JeanNeural")
    try:
        import edge_tts
    except ImportError:
        raise HTTPException(503, "edge-tts non installé — lance: pip install edge-tts")

    communicate = edge_tts.Communicate(text, tts_voice)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")  # NOSONAR
    tmp_path = tmp.name
    tmp.close()

    await communicate.save(tmp_path)

    async def stream_and_delete():
        try:
            with open(tmp_path, "rb") as f:  # NOSONAR
                while chunk := f.read(8192):
                    yield chunk
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return StreamingResponse(
        stream_and_delete(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=jarvis.mp3"},
    )


# ── Whisper local (faster-whisper, chargé une seule fois) ───────────────────
_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # "small" = bien meilleure précision que "base", ~2-4s sur CPU
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
        print("🎙 Whisper small chargé sur CPU (int8)")
    return _whisper_model


@router.get("/v1/speech/health")
async def speech_health():
    try:
        import faster_whisper  # noqa: F401
        return {"available": True, "backend": "faster-whisper-local"}
    except ImportError:
        return {"available": False, "backend": None, "error": "faster-whisper not installed"}


@router.post("/v1/speech/transcribe")
async def speech_transcribe(
    file: UploadFile = File(...),
    language: str | None = None,   # "fr" | "en" | None = auto-detect
):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(400, "Fichier audio vide")

    # Resolve language: explicit param > config > default "fr"
    # Forcing a language prevents auto-detect bugs like "allo" → Arabic "هلو"
    _cfg_lang = load_config().get("jarvis", {}).get("language", "Français")
    _lang_map  = {"Français": "fr", "French": "fr", "English": "en", "fr": "fr", "en": "en"}
    resolved_lang = language or _lang_map.get(_cfg_lang, "fr")

    suffix = ".webm"
    tmp_f  = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)  # NOSONAR
    tmp_f.write(audio_bytes)
    tmp_f.close()

    def _run(path: str):
        model = _get_whisper()
        segments, info = model.transcribe(
            path,
            language=resolved_lang,            # FIX: force language — prevents "allo"→"هلو"
            task="transcribe",
            beam_size=5,
            no_speech_threshold=0.6,           # ignore silence/background noise
            condition_on_previous_text=False,  # prevents hallucinated repetitions
            repetition_penalty=1.2,            # extra guard against echo loops
            temperature=0,                     # deterministic output
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text, info

    try:
        import asyncio
        import traceback
        loop = asyncio.get_running_loop()   # fix: get_event_loop() déprécié Python 3.10+
        try:
            text, info = await loop.run_in_executor(None, _run, tmp_f.name)
        except Exception as e:
            print(f"[SPEECH] Erreur transcription: {traceback.format_exc()}")
            raise HTTPException(500, f"Transcription échouée: {e}")
        return {
            "text":             text,
            "language":         info.language,
            "confidence":       float(info.language_probability),
            "duration_seconds": float(info.duration),
        }
    finally:
        try:
            os.unlink(tmp_f.name)
        except OSError:
            pass

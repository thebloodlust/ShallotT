"""
Speech-to-Text module for ShallotT.
Uses faster-whisper (CTranslate2 backend) for local, offline transcription.
Models are downloaded automatically from HuggingFace on first use.
"""

import threading
import numpy as np
import os

# Use a subdirectory inside the config folder for model caching
from src.config import CONFIG_DIR

WHISPER_CACHE = os.path.join(CONFIG_DIR, "whisper_models")
_LOADED_MODELS: dict = {}          # model_size → WhisperModel
_LOAD_LOCK = threading.Lock()

# ── Model loading (lazy, cached) ──────────────────────────────────

def _get_model(model_size: str = "tiny"):
    """Return a cached faster-whisper model, downloading on first call."""
    key = model_size.lower()
    if key in _LOADED_MODELS:
        return _LOADED_MODELS[key]

    with _LOAD_LOCK:
        if key in _LOADED_MODELS:
            return _LOADED_MODELS[key]

        from faster_whisper import WhisperModel

        os.makedirs(WHISPER_CACHE, exist_ok=True)

        # Map user-friendly names to HuggingFace model IDs
        model_id_map = {
            "tiny":    "Systran/faster-whisper-tiny",
            "tiny.en": "Systran/faster-whisper-tiny.en",
            "small":   "Systran/faster-whisper-small",
            "medium":  "Systran/faster-whisper-medium",
        }
        model_id = model_id_map.get(key, key)

        # Prefer GPU if available (int8_float16), else CPU (int8)
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
        except ImportError:
            device = "cpu"
            compute_type = "int8"

        model = WhisperModel(
            model_id,
            device=device,
            compute_type=compute_type,
            download_root=WHISPER_CACHE,
            local_files_only=False,
        )
        _LOADED_MODELS[key] = model
        return model


# ── Transcription worker ──────────────────────────────────────────

class STTWorker(threading.Thread):
    """Runs transcription on an audio chunk in a background thread."""

    def __init__(self, audio: np.ndarray, sample_rate: int = 16000,
                 model_size: str = "tiny", language: str = None,
                 on_done=None, on_error=None):
        super().__init__(daemon=True)
        self.audio = audio
        self.sample_rate = sample_rate
        self.model_size = model_size
        self.language = language
        self._on_done = on_done
        self._on_error = on_error

    def run(self):
        try:
            if self.audio is None or len(self.audio) < self.sample_rate * 0.3:
                # Less than 0.3 s — probably silence, skip
                if self._on_done:
                    self._on_done("")
                return

            model = _get_model(self.model_size)

            # Ensure float32
            audio = self.audio.astype(np.float32)
            if audio.ndim > 1:
                audio = audio.mean(axis=1)  # mono

            segments, _ = model.transcribe(
                audio,
                language=self.language,
                beam_size=5,
                vad_filter=True,          # filter out silence
                condition_on_previous_text=False,
            )

            # Collect all segment texts
            texts = []
            for seg in segments:
                if seg.text.strip():
                    texts.append(seg.text.strip())

            result = " ".join(texts)
            if self._on_done:
                self._on_done(result)

        except Exception as e:
            if self._on_error:
                self._on_error(str(e))
            else:
                print(f"[stt] error: {e}")


# ── Convenience function ──────────────────────────────────────────

def transcribe_async(audio: np.ndarray, sample_rate: int = 16000,
                     model_size: str = "tiny", language: str = None,
                     on_done=None, on_error=None) -> STTWorker:
    """Launch transcription in a background thread. Returns the worker."""
    worker = STTWorker(
        audio=audio,
        sample_rate=sample_rate,
        model_size=model_size,
        language=language,
        on_done=on_done,
        on_error=on_error,
    )
    worker.start()
    return worker

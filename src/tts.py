"""
Text-to-Speech module for ShallotT.
Uses pyttsx3 (offline, multi-platform) for reading translations aloud.
Supports language-specific voice selection where available.
"""

import threading
import sys


# ── Lazy pyttsx3 engine (avoid import cost until first use) ───────

_ENGINE = None
_ENGINE_LOCK = threading.Lock()


def _get_engine():
    """Return the singleton pyttsx3 engine, initialised on first call."""
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is not None:
            return _ENGINE
        import pyttsx3
        _ENGINE = pyttsx3.init()
        # Default rate (words per minute)
        _ENGINE.setProperty('rate', 165)
        _ENGINE.setProperty('volume', 0.9)
    return _ENGINE


# ── Language → voice name hint ────────────────────────────────────

_LANG_VOICE_HINTS = {
    "french":     ["french", "francais", "français"],
    "english":    ["english", "anglais"],
    "spanish":    ["spanish", "espanol", "espagnol"],
    "german":     ["german", "deutsch", "allemand"],
    "italian":    ["italian", "italiano", "italien"],
    "portuguese": ["portuguese", "portugues", "português"],
    "chinese":    ["chinese", "chinois"],
    "japanese":   ["japanese", "japonais"],
    "russian":    ["russian", "russe"],
}


def _find_voice_for_language(target_lang: str) -> str | None:
    """Try to find a TTS voice matching the target language."""
    try:
        engine = _get_engine()
        voices = engine.getProperty('voices')
        hints = _LANG_VOICE_HINTS.get(target_lang.lower(), [target_lang.lower()])

        # First pass: match any hint in voice name or id
        for voice in voices:
            name_lower = (voice.name + voice.id).lower()
            for hint in hints:
                if hint in name_lower:
                    return voice.id

        # Second pass: on macOS, try to match language tag in id
        # e.g. "com.apple.voice.compact.fr-FR.Amelie"
        lang_tags = {
            "french": "fr", "english": "en", "spanish": "es",
            "german": "de", "italian": "it", "portuguese": "pt",
            "chinese": "zh", "japanese": "ja", "russian": "ru",
        }
        tag = lang_tags.get(target_lang.lower())
        if tag:
            for voice in voices:
                if tag in voice.id.lower():
                    return voice.id

        return None
    except Exception:
        return None


# ── Public API ────────────────────────────────────────────────────

def speak(text: str, target_lang: str = "English",
           on_start=None, on_done=None, on_error=None):
    """Speak `text` aloud using a voice appropriate for `target_lang`.

    Runs on a background thread so the UI stays responsive.
    """
    if not text or not text.strip():
        return

    def _run():
        try:
            engine = _get_engine()

            # Try to match voice to language
            voice_id = _find_voice_for_language(target_lang)
            if voice_id:
                engine.setProperty('voice', voice_id)

            if on_start:
                on_start()

            engine.say(text)
            engine.runAndWait()

            if on_done:
                on_done()

        except Exception as e:
            if on_error:
                on_error(str(e))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def stop():
    """Interrupt any ongoing speech."""
    try:
        engine = _get_engine()
        engine.stop()
    except Exception:
        pass


def list_voices() -> list[str]:
    """Return a list of available voice names."""
    try:
        engine = _get_engine()
        return [v.name for v in engine.getProperty('voices')]
    except Exception:
        return []

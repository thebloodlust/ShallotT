"""
Audio capture module for ShallotT.
Supports WASAPI loopback (system audio) and microphone capture on Windows 11.
Uses the sounddevice library for cross-platform audio I/O.
"""

import sounddevice as sd
import numpy as np
import threading


class AudioCapture:
    """Captures audio from system loopback (WASAPI) or microphone."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._stream = None
        self._recording = threading.Event()
        self._buffer: list = []
        self._level = 0.0
        self._lock = threading.Lock()

    # ── device discovery ──────────────────────────────────────────

    @staticmethod
    def list_all_devices() -> list[dict]:
        """Return every audio device visible to PortAudio / WASAPI."""
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        result = []
        for idx, dev in enumerate(devices):
            api_name = hostapis[dev['hostapi']]['name']
            result.append({
                'id': idx,
                'name': dev['name'],
                'channels_in': dev['max_input_channels'],
                'channels_out': dev['max_output_channels'],
                'hostapi': api_name,
                'is_loopback': 'loopback' in dev['name'].lower(),
            })
        return result

    @staticmethod
    def find_wasapi_loopback_device() -> tuple[int | None, str]:
        """Return (device_id, name) of the first WASAPI loopback device,
        or the default WASAPI input device if no loopback is available."""
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()

        wasapi_idx = None
        for i, api in enumerate(hostapis):
            if 'wasapi' in api['name'].lower():
                wasapi_idx = i
                break

        if wasapi_idx is None:
            # Fallback: use default input
            default = sd.default.device[0]
            return default, "Default Input"

        # Prefer loopback devices
        for didx, dev in enumerate(devices):
            if dev['hostapi'] == wasapi_idx and dev['max_input_channels'] > 0:
                if 'loopback' in dev['name'].lower():
                    return didx, dev['name']

        # Fallback to any WASAPI input
        for didx, dev in enumerate(devices):
            if dev['hostapi'] == wasapi_idx and dev['max_input_channels'] > 0:
                return didx, dev['name']

        return None, "No WASAPI device found"

    @staticmethod
    def find_microphone_device() -> tuple[int | None, str]:
        """Return (device_id, name) of the default microphone / input device."""
        devices = sd.query_devices()
        # Try default input first
        default_input = sd.default.device[0]
        if default_input is not None and default_input < len(devices):
            dev = devices[default_input]
            if dev['max_input_channels'] > 0:
                return default_input, dev['name']

        # Scan for any input-capable device
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                return idx, dev['name']

        return None, "No microphone found"

    # ── recording ─────────────────────────────────────────────────

    @property
    def level(self) -> float:
        """Current RMS audio level (0.0 – 1.0), updated in audio callback."""
        with self._lock:
            return self._level

    @property
    def recording(self) -> bool:
        return self._recording.is_set()

    def start(self, device_id: int | None = None,
              level_callback=None) -> None:
        """Start capturing audio on a background PortAudio stream."""
        if self._recording.is_set():
            return  # Already running

        self._buffer.clear()
        self._recording.set()

        def _callback(indata: np.ndarray, frames: int,
                      time_info, status: sd.CallbackFlags):
            if status:
                print(f"[audio_capture] status: {status}")
            if not self._recording.is_set():
                return
            # Keep a ring buffer of the last N seconds (we'll accumulate
            # chunks and let the STT worker drain them).
            self._buffer.append(indata.copy())
            with self._lock:
                self._level = float(np.abs(indata).mean())
            if level_callback:
                level_callback(self._level)

        self._stream = sd.InputStream(
            device=device_id,
            channels=1,
            samplerate=self.sample_rate,
            callback=_callback,
            dtype='float32',
        )
        self._stream.start()

    def stop(self) -> np.ndarray | None:
        """Stop recording and return the concatenated audio data."""
        self._recording.clear()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._buffer:
            return None
        audio = np.concatenate(self._buffer, axis=0)
        self._buffer.clear()
        return audio

    def drain_chunk(self) -> np.ndarray | None:
        """Non-blocking: return audio accumulated since last call (or start).
        Returns None when nothing new is available."""
        if not self._buffer:
            return None
        # Thread-safe swap
        chunk = self._buffer.copy()
        self._buffer.clear()
        if not chunk:
            return None
        return np.concatenate(chunk, axis=0)

    def flush(self) -> np.ndarray | None:
        """Alias for stop() — convenience helper."""
        return self.stop()

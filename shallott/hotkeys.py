"""Global hotkey manager for ShallotT.

Registers system-wide keyboard shortcuts using the *pynput* library.

Supported hotkeys (configurable via config.json):
  translate_clipboard  – default: Ctrl+C+C  (press C twice while Ctrl is held)
  translate_ocr        – default: Ctrl+F8
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any, Callable

from pynput import keyboard

logger = logging.getLogger(__name__)

# Alias so callers can import Key directly from this module
Key = keyboard.Key
KeyCode = keyboard.KeyCode


def _parse_hotkey(hotkey_str: str) -> frozenset:
    """Parse a hotkey string like '<ctrl>+c+c' into a frozenset of pynput keys.

    For double-key sequences (e.g. c+c) the set contains the key once —
    the double-press detection is handled by the combo tracker.
    """
    parts = [p.strip() for p in hotkey_str.lower().split("+")]
    keys: set = set()
    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            name = part[1:-1]
            try:
                keys.add(getattr(Key, name))
            except AttributeError:
                logger.warning("Unknown special key: %s", name)
        else:
            keys.add(KeyCode.from_char(part))
    return frozenset(keys)


class _DoublePressTracker:
    """Detect a key being pressed twice within *window* seconds."""

    def __init__(self, key, window: float = 0.5) -> None:
        self._key = key
        self._window = window
        self._last_press: float = 0.0

    def register(self, key) -> bool:
        """Return True if this press qualifies as a double-press."""
        if key != self._key:
            return False
        now = time.monotonic()
        if now - self._last_press <= self._window:
            self._last_press = 0.0  # reset so triple-press is not counted
            return True
        self._last_press = now
        return False


class HotkeyManager:
    """Registers and dispatches global keyboard shortcuts."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        hk_cfg = cfg.get("hotkeys", {})

        # Ctrl+C+C  → translate clipboard (Ctrl held, C pressed twice)
        self._clipboard_hotkey_str: str = hk_cfg.get(
            "translate_clipboard", "<ctrl>+c+c"
        )
        # Ctrl+F8   → OCR translate
        self._ocr_hotkey_str: str = hk_cfg.get("translate_ocr", "<ctrl>+<f8>")

        # Parse ocr hotkey as a simple combo
        self._ocr_combo: frozenset = _parse_hotkey(self._ocr_hotkey_str)

        # Ctrl+C+C is special: Ctrl held AND C pressed twice
        self._ctrl_c_tracker = _DoublePressTracker(KeyCode.from_char("c"), window=0.5)

        self._currently_pressed: set = set()
        self._callbacks: dict[str, Callable] = {}
        self._listener: keyboard.Listener | None = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def register(self, action: str, callback: Callable) -> None:
        """Register *callback* to fire when *action* hotkey is triggered.

        Supported actions: 'translate_clipboard', 'translate_ocr'.
        """
        self._callbacks[action] = callback

    def start(self) -> None:
        """Start listening for global hotkeys (non-blocking)."""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        logger.info(
            "Hotkeys registered – clipboard: %s | OCR: %s",
            self._clipboard_hotkey_str,
            self._ocr_hotkey_str,
        )

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_press(self, key) -> None:
        self._currently_pressed.add(key)

        # --- Ctrl+F8 (simple combo) ---
        if self._ocr_combo.issubset(self._currently_pressed):
            self._fire("translate_ocr")

        # --- Ctrl+C+C (Ctrl held, C double-pressed) ---
        ctrl_held = (
            Key.ctrl_l in self._currently_pressed
            or Key.ctrl_r in self._currently_pressed
            or Key.ctrl in self._currently_pressed
        )
        if ctrl_held and self._ctrl_c_tracker.register(key):
            self._fire("translate_clipboard")

    def _on_release(self, key) -> None:
        self._currently_pressed.discard(key)

    def _fire(self, action: str) -> None:
        callback = self._callbacks.get(action)
        if callback is None:
            return
        # Run in a daemon thread so the listener is never blocked
        t = threading.Thread(target=callback, daemon=True)
        t.start()

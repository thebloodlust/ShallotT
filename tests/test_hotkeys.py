"""Tests for shallott.hotkeys (HotkeyManager)."""

import threading
import time

import pytest
from unittest.mock import MagicMock, patch

# We need to monkey-patch pynput before importing HotkeyManager
# because pynput may not be installed in CI / headless environments.

pynput_mock = MagicMock()
keyboard_mock = MagicMock()

# Build realistic Key / KeyCode stubs
class _Key:
    ctrl = object()
    ctrl_l = object()
    ctrl_r = object()
    f8 = object()

class _KeyCode:
    def __init__(self, char):
        self.char = char

    @classmethod
    def from_char(cls, c):
        return cls(c)

    def __eq__(self, other):
        return isinstance(other, _KeyCode) and self.char == other.char

    def __hash__(self):
        return hash(self.char)

    def __repr__(self):
        return f"KeyCode({self.char!r})"

keyboard_mock.Key = _Key
keyboard_mock.KeyCode = _KeyCode

import sys
sys.modules.setdefault("pynput", pynput_mock)
sys.modules.setdefault("pynput.keyboard", keyboard_mock)
pynput_mock.keyboard = keyboard_mock

# Now we can import – must happen after the mock is in sys.modules
from shallott.hotkeys import HotkeyManager, _DoublePressTracker, _parse_hotkey


# ─── _DoublePressTracker ──────────────────────────────────────────────────────

def test_double_press_detected():
    key = _KeyCode.from_char("c")
    tracker = _DoublePressTracker(key, window=0.5)
    assert tracker.register(key) is False   # first press
    assert tracker.register(key) is True    # second press within window


def test_double_press_too_slow():
    key = _KeyCode.from_char("c")
    tracker = _DoublePressTracker(key, window=0.01)
    tracker.register(key)
    time.sleep(0.05)
    assert tracker.register(key) is False   # too slow → not a double press


def test_double_press_wrong_key():
    key_c = _KeyCode.from_char("c")
    key_x = _KeyCode.from_char("x")
    tracker = _DoublePressTracker(key_c, window=0.5)
    assert tracker.register(key_x) is False


# ─── _parse_hotkey ────────────────────────────────────────────────────────────

def test_parse_hotkey_special_key():
    keys = _parse_hotkey("<ctrl>+<f8>")
    # Should contain the Key.ctrl object (via getattr)
    assert _Key.ctrl in keys or _Key.f8 in keys


def test_parse_hotkey_char():
    keys = _parse_hotkey("<ctrl>+c+c")
    # After dedup, 'c' appears once
    c_key = _KeyCode.from_char("c")
    assert c_key in keys


# ─── HotkeyManager callback dispatch ─────────────────────────────────────────

def _make_manager():
    cfg = {
        "hotkeys": {
            "translate_clipboard": "<ctrl>+c+c",
            "translate_ocr": "<ctrl>+<f8>",
        }
    }
    # Patch keyboard.Listener to a no-op
    keyboard_mock.Listener = MagicMock(return_value=MagicMock())
    return HotkeyManager(cfg)


def test_register_callback_fires_on_translate_clipboard():
    mgr = _make_manager()
    fired = threading.Event()
    mgr.register("translate_clipboard", lambda: fired.set())

    # Simulate: Ctrl held, then C pressed twice
    mgr._currently_pressed.add(_Key.ctrl_l)
    key_c = _KeyCode.from_char("c")
    mgr._on_press(key_c)   # first C
    mgr._on_press(key_c)   # second C → should fire

    fired.wait(timeout=1.0)
    assert fired.is_set()


def test_unregistered_action_does_not_raise():
    mgr = _make_manager()
    # No callback registered – should silently do nothing
    mgr._fire("translate_clipboard")
    mgr._fire("translate_ocr")

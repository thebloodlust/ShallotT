import time
from pynput import keyboard

class ShortcutManager:
    def __init__(self, on_translate_trigger, on_ocr_trigger, config_provider=None,
                 on_quicklang_trigger=None):
        self.on_translate_trigger = on_translate_trigger
        self.on_ocr_trigger = on_ocr_trigger
        self.on_quicklang_trigger = on_quicklang_trigger
        self.config_provider = config_provider

        self.last_c_press_time = 0
        self.listener = None
        self.pressed_keys = set()
        # When the quick-lang combo is pressed we "arm" for a few seconds,
        # waiting for the next letter to pick the target language.
        self.quicklang_armed_until = 0

    @staticmethod
    def parse_quick_lang_map(raw):
        """Parse 'E=English, F=French' into {'e':'English','f':'French'}."""
        mapping = {}
        if raw:
            for pair in str(raw).split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if len(k) == 1 and v:
                        mapping[k] = v
        return mapping

    def start(self):
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()

    def get_key_name(self, key):
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            return "ctrl"
        if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            return "alt"
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            return "shift"
        if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            return "cmd"
        
        # Check F keys
        for i in range(1, 13):
            if key == getattr(keyboard.Key, f'f{i}', None):
                return f"f{i}"
                
        if hasattr(key, 'char') and key.char:
            return key.char.lower()
            
        try:
            name = key.name
            if name:
                return name.lower()
        except AttributeError:
            pass
            
        return None

    def on_press(self, key):
        try:
            name = self.get_key_name(key)
            if name:
                self.pressed_keys.add(name)
                
            # Load latest config dynamically to support hot-swapping shortcuts!
            config = self.config_provider() if self.config_provider else {}
            trans_shortcut = config.get("shortcut_translate", "ctrl+c+c").lower().strip()
            ocr_shortcut = config.get("shortcut_ocr", "ctrl+f8").lower().strip()

            # 0. Quick-lang: if armed, the next single letter picks the language.
            if self.on_quicklang_trigger and time.time() < self.quicklang_armed_until:
                if name and len(name) == 1 and name.isalpha():
                    mapping = self.parse_quick_lang_map(config.get("quick_lang_map", ""))
                    lang = mapping.get(name.lower())
                    self.quicklang_armed_until = 0
                    self.pressed_keys.clear()  # avoid stuck keys / double-trigger
                    if lang:
                        self.on_quicklang_trigger(lang)
                    return

            # 0b. Detect the quick-lang combo to arm letter capture.
            if self.on_quicklang_trigger:
                ql_shortcut = config.get("shortcut_quicklang", "ctrl+f9").lower().strip()
                ql_keys = set(ql_shortcut.split("+")) if ql_shortcut else set()
                if ql_keys and ql_keys.issubset(self.pressed_keys):
                    self.quicklang_armed_until = time.time() + 5.0
                    self.pressed_keys.clear()
                    return

            # 1. Translate action trigger checks
            if trans_shortcut == "ctrl+c+c":
                if "ctrl" in self.pressed_keys and name == "c":
                    current_time = time.time()
                    if current_time - self.last_c_press_time < 0.5:
                        self.pressed_keys.clear()  # Clear to avoid stuck keys
                        self.on_translate_trigger()
                        self.last_c_press_time = 0
                    else:
                        self.last_c_press_time = current_time
            else:
                target_keys = set(trans_shortcut.split("+"))
                if target_keys and target_keys.issubset(self.pressed_keys):
                    self.pressed_keys.clear()  # Clear to avoid stuck keys
                    self.on_translate_trigger()

            # 2. OCR action trigger checks
            target_ocr_keys = set(ocr_shortcut.split("+"))
            if target_ocr_keys and target_ocr_keys.issubset(self.pressed_keys):
                self.pressed_keys.clear()  # Clear to avoid stuck keys
                self.on_ocr_trigger()
        except Exception as e:
            print(f"Error in shortcuts on_press: {e}")

    def on_release(self, key):
        try:
            name = self.get_key_name(key)
            if name and name in self.pressed_keys:
                self.pressed_keys.discard(name)
        except Exception as e:
            print(f"Error in shortcuts on_release: {e}")

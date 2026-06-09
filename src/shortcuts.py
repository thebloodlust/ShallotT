import time
from pynput import keyboard

class ShortcutManager:
    def __init__(self, on_translate_trigger, on_ocr_trigger, config_provider=None):
        self.on_translate_trigger = on_translate_trigger
        self.on_ocr_trigger = on_ocr_trigger
        self.config_provider = config_provider
        
        self.last_c_press_time = 0
        self.listener = None
        self.pressed_keys = set()

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

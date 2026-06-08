import time
from pynput import keyboard

class ShortcutManager:
    def __init__(self, on_translate_trigger, on_ocr_trigger):
        self.on_translate_trigger = on_translate_trigger
        self.on_ocr_trigger = on_ocr_trigger
        
        self.ctrl_pressed = False
        self.last_c_press_time = 0
        self.c_press_count = 0
        
        self.listener = None
        self.active_keys = set()

    def start(self):
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()

    def on_press(self, key):
        # We track modifier keys
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl_pressed = True
            
        try:
            # Handle Ctrl + C + C (Double C press while Ctrl is held or rapid Ctrl+C + Ctrl+C)
            if self.ctrl_pressed:
                # key.char represents the character
                if hasattr(key, 'char') and (key.char == 'c' or key.char == 'C' or ord(key.char) == 3): # 3 is copy character code in some layouts
                    current_time = time.time()
                    # It's a second 'C' press within 0.5 seconds while holding ctrl
                    if current_time - self.last_c_press_time < 0.5:
                        self.on_translate_trigger()
                        # Reset
                        self.last_c_press_time = 0
                    else:
                        self.last_c_press_time = current_time

            # Handle Ctrl + F8 (Global shortcut for OCR)
            if self.ctrl_pressed and key == keyboard.Key.f8:
                self.on_ocr_trigger()
                
        except AttributeError:
            # For special keys like F8 when ctrl is pressed, sometimes attributes differ
            if self.ctrl_pressed and key == keyboard.Key.f8:
                self.on_ocr_trigger()
            pass

    def on_release(self, key):
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl_pressed = False

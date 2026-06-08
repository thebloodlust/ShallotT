import sys
import os
from PyQt6.QtWidgets import QApplication
from src.ui import ShallotTApp
from src.shortcuts import ShortcutManager

def main():
    app = QApplication(sys.argv)
    
    app.setApplicationName("ShallotT")
    app.setApplicationVersion("1.0.0")
    
    # Create main GUI window
    window = ShallotTApp()
    
    # Check command-line arguments (useful for Linux Wayland custom global keyboard shortcuts)
    args = sys.argv[1:]
    
    if "--translate" in args or "-t" in args:
        # Trigger immediate translation of current clipboard and show
        window.show_normal()
        window.handle_global_translate_shortcut()
    elif "--ocr" in args or "-o" in args:
        # Trigger immediate layout selection for OCR and translate, window remains hidden initially
        window.handle_global_ocr_shortcut()
    else:
        # Normal background/foreground mode
        window.show()
        
        # Setup global shortcuts listener (works out of the box in X11 and most hybrid systems)
        shortcuts = ShortcutManager(
            on_translate_trigger=lambda: window.trigger_translate_shortcut.emit(),
            on_ocr_trigger=lambda: window.trigger_ocr_shortcut.emit(),
            config_provider=lambda: window.config
        )
        shortcuts.start()
        
        # Safe exit routine to shut down the background listener thread properly
        def cleanup():
            print("Stopping background shortcut listeners...")
            shortcuts.stop()
            
        app.aboutToQuit.connect(cleanup)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

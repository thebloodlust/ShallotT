import sys
import os
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject
from src.ui import ShallotTApp
from src.shortcuts import ShortcutManager
from src.ocr_server import start_server, set_ocr_callback

# Signal bridge: OCR server (HTTP thread) → main window (Qt thread)
class _OCRBridge(QObject):
    trigger = pyqtSignal()
    result_ready = pyqtSignal(str, str)  # (text, error)

_OCR_BRIDGE = _OCRBridge()

def main():
    app = QApplication(sys.argv)

    app.setApplicationName("ShallotT")
    app.setApplicationVersion("1.0.6")

    # Start the OCR bridge HTTP server
    _ocr_pending = threading.Event()
    _ocr_result = [None, None]  # [text, error]

    def on_ocr_request():
        """Called from HTTP thread — signal Qt to start OCR."""
        _ocr_pending.clear()
        _ocr_result[0] = None
        _ocr_result[1] = None
        _OCR_BRIDGE.trigger.emit()

    def on_ocr_done(text: str, error: str):
        _ocr_result[0] = text
        _ocr_result[1] = error
        _ocr_pending.set()

    _OCR_BRIDGE.result_ready.connect(on_ocr_done)

    def ocr_callback():
        """Blocking call used by the HTTP server."""
        on_ocr_request()
        _ocr_pending.wait(timeout=30)  # 30 s max for user to select area
        if _ocr_result[1]:
            raise RuntimeError(_ocr_result[1])
        return _ocr_result[0] or ""

    set_ocr_callback(ocr_callback)
    start_server(port=11435)
    print("[ocr_server] Listening on http://127.0.0.1:11435/ocr")

    # Create main GUI window
    window = ShallotTApp()

    # Wire the OCR bridge: HTTP request → window OCR → result back
    def _on_ocr_bridge_trigger():
        from src.ocr import run_ocr_capture
        run_ocr_capture(
            lambda text: _OCR_BRIDGE.result_ready.emit(
                "" if (text or "").startswith("[OCR Error]") else (text or ""),
                text if (text or "").startswith("[OCR Error]") else ""
            ),
            window.config.get("ocr_engine", "tesseract")
        )

    _OCR_BRIDGE.trigger.connect(_on_ocr_bridge_trigger)
    
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
            on_quicklang_trigger=lambda lang: window.trigger_quicklang_shortcut.emit(lang),
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

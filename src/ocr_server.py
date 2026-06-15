"""
Mini HTTP server that lets the browser extension trigger OCR captures.
Listens on localhost:11435. The extension calls GET /ocr and gets back
the recognised text as JSON: {"text": "...", "error": null}
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


_OCR_CALLBACK = None  # set by main.py to the app window for dispatching


def set_ocr_callback(fn):
    """Register the function that triggers OCR capture and returns text."""
    global _OCR_CALLBACK
    _OCR_CALLBACK = fn


class _OCRHandler(BaseHTTPRequestHandler):
    """Minimal CORS-enabled handler for extension requests."""

    def do_GET(self):
        if self.path != "/ocr":
            self.send_error(404)
            return

        if _OCR_CALLBACK is None:
            self._json({"text": "", "error": "OCR server not ready"})
            return

        # Trigger OCR and wait for the result (blocking call is fine here,
        # the server runs on its own thread).
        try:
            text = _OCR_CALLBACK()
            self._json({"text": text or "", "error": None})
        except Exception as e:
            self._json({"text": "", "error": str(e)})

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def log_message(self, fmt, *args):
        pass  # silent — avoid console noise


def start_server(port: int = 11435):
    """Launch the OCR bridge server on a daemon thread."""
    server = HTTPServer(("127.0.0.1", port), _OCRHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

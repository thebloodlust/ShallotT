"""ShallotT – main application entry point.

Wires together:
  - Config loader
  - Ollama client
  - Hotkey manager (Ctrl+C+C  and  Ctrl+F8)
  - OCR module
  - Translation overlay
  - System tray
"""

from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from typing import Any

import pyperclip

from . import config as cfg_module
from .hotkeys import HotkeyManager
from .ocr import capture_and_extract, select_region_interactively
from .overlay import TranslationOverlay
from .translator import OllamaClient
from .tray import TrayIcon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class ShallotTApp:
    """Main application controller."""

    def __init__(self, config_path: str | None = None) -> None:
        self.cfg: dict[str, Any] = cfg_module.load(config_path)
        self.client = OllamaClient(self.cfg)
        self.overlay = TranslationOverlay(self.cfg)
        self.hotkeys = HotkeyManager(self.cfg)
        self.tray = TrayIcon(self.cfg, on_quit=self.stop)
        self._running = threading.Event()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        logger.info("ShallotT starting…")

        # Check Ollama connectivity
        if self.client.is_reachable():
            logger.info("Ollama is reachable at %s", self.client.host)
            self.tray.set_status("Connected")
        else:
            logger.warning(
                "Ollama not reachable at %s – translations will fail until "
                "the host is accessible (check VPN / network settings)",
                self.client.host,
            )
            self.tray.set_status("Ollama unreachable")

        # Register hotkey callbacks
        self.hotkeys.register("translate_clipboard", self._on_translate_clipboard)
        self.hotkeys.register("translate_ocr", self._on_translate_ocr)
        self.hotkeys.start()

        # Start tray (daemon thread)
        self.tray.run_async()

        self._running.set()
        logger.info(
            "Ready.  Clipboard shortcut: %s | OCR shortcut: %s",
            self.cfg["hotkeys"]["translate_clipboard"],
            self.cfg["hotkeys"]["translate_ocr"],
        )

        # Block main thread until stop() is called
        try:
            while self._running.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        logger.info("ShallotT shutting down…")
        self._running.clear()
        self.hotkeys.stop()

    # ------------------------------------------------------------------
    # Hotkey handlers
    # ------------------------------------------------------------------

    def _on_translate_clipboard(self) -> None:
        """Triggered by Ctrl+C+C – translate clipboard contents."""
        try:
            text = pyperclip.paste()
        except Exception as exc:
            logger.error("Could not read clipboard: %s", exc)
            self.overlay.show_error("Could not read clipboard")
            return

        text = text.strip()
        if not text:
            self.overlay.show_error("Clipboard is empty")
            return

        logger.info("Translate clipboard (%d chars)", len(text))
        self.overlay.show_loading()
        self._do_translate(text)

    def _on_translate_ocr(self) -> None:
        """Triggered by Ctrl+F8 – capture a screen region, OCR it, translate."""
        logger.info("OCR translation triggered")
        self.overlay.show_loading()

        try:
            region = select_region_interactively()
        except Exception as exc:
            logger.error("Region selection failed: %s", exc)
            self.overlay.show_error("Region selection failed")
            return

        if region is None:
            self.overlay.close()
            return

        try:
            text = capture_and_extract(self.cfg, region=region)
        except Exception as exc:
            logger.error("OCR failed: %s", exc)
            self.overlay.show_error(f"OCR error: {exc}")
            return

        if not text:
            self.overlay.show_error("No text found in selected region")
            return

        logger.info("OCR extracted: %.60s…", text)
        self._do_translate(text)

    def _do_translate(self, text: str) -> None:
        target = self.cfg["translation"].get("target_language", "en")
        try:
            result = self.client.translate(text, target_language=target)
        except Exception as exc:
            logger.error("Translation failed: %s", exc)
            self.overlay.show_error(f"Translation error: {exc}")
            return

        self.overlay.show_result(result, original=text)
        # Also put the translation on the clipboard (optional convenience)
        try:
            pyperclip.copy(result)
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="shallott",
        description="ShallotT – AI-powered translation via keyboard shortcuts",
    )
    parser.add_argument(
        "--config", "-c",
        metavar="PATH",
        help="Path to config.json (default: auto-detected)",
    )
    parser.add_argument(
        "--version", "-V",
        action="store_true",
        help="Print version and exit",
    )
    args = parser.parse_args(argv)

    if args.version:
        from . import __version__
        print(__version__)
        return 0

    app = ShallotTApp(config_path=args.config)

    def _sigterm(_sig, _frame):
        app.stop()

    signal.signal(signal.SIGTERM, _sigterm)

    app.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())

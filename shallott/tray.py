"""System-tray icon for ShallotT.

Provides a persistent tray icon with a context menu to:
  - Show current status / Ollama connectivity
  - Open settings (config file)
  - Quit the application
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from typing import Any

logger = logging.getLogger(__name__)


def _make_icon():
    """Create a simple onion-coloured tray icon using Pillow."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Outer circle – purple/violet (onion skin colour)
    draw.ellipse([4, 4, 60, 60], fill=(148, 103, 189, 230))
    # Inner highlight
    draw.ellipse([18, 14, 46, 42], fill=(200, 170, 230, 180))
    # Letter T
    draw.rectangle([24, 44, 40, 48], fill=(255, 255, 255, 240))
    draw.rectangle([30, 32, 34, 50], fill=(255, 255, 255, 240))
    return img


class TrayIcon:
    """Wraps pystray to provide a system-tray icon."""

    def __init__(self, cfg: dict[str, Any], on_quit: callable) -> None:
        self._cfg = cfg
        self._on_quit = on_quit
        self._icon = None
        self._status = "Idle"

    def set_status(self, status: str) -> None:
        self._status = status
        if self._icon:
            self._icon.title = f"ShallotT – {status}"

    def run(self) -> None:
        """Start the tray icon (blocks until quit)."""
        import pystray  # noqa: PLC0415
        from pystray import MenuItem as Item, Menu  # noqa: PLC0415

        icon_image = _make_icon()

        def open_config(_icon, _item):
            cfg_path = os.path.join(os.getcwd(), "config.json")
            if not os.path.exists(cfg_path):
                cfg_path = os.path.join(os.getcwd(), "config.example.json")
            if sys.platform == "win32":
                os.startfile(cfg_path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", cfg_path])  # noqa: S603,S607
            else:
                subprocess.Popen(["xdg-open", cfg_path])  # noqa: S603,S607

        def quit_app(_icon, _item):
            _icon.stop()
            self._on_quit()

        menu = Menu(
            Item("ShallotT", None, enabled=False),
            Menu.SEPARATOR,
            Item("Open config", open_config),
            Menu.SEPARATOR,
            Item("Quit", quit_app),
        )

        self._icon = pystray.Icon(
            "ShallotT",
            icon_image,
            f"ShallotT – {self._status}",
            menu,
        )
        self._icon.run()

    def run_async(self) -> threading.Thread:
        """Start the tray icon in a background daemon thread."""
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        return t

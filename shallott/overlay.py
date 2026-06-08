"""Overlay window that displays a translation result to the user.

Uses tkinter (stdlib) so no extra dependencies are needed for the UI.
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any

logger = logging.getLogger(__name__)

_OVERLAY_BG = "#1e1e2e"
_OVERLAY_FG = "#cdd6f4"
_ACCENT = "#89b4fa"
_ERROR_FG = "#f38ba8"


class TranslationOverlay:
    """Small floating window that shows translation progress and result."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        ui_cfg = cfg.get("ui", {})
        self._duration: int = int(ui_cfg.get("overlay_duration", 8))
        self._position: str = ui_cfg.get("overlay_position", "bottom-right")
        self._root: tk.Tk | None = None
        self._text_var: tk.StringVar | None = None
        self._after_id: str | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_loading(self) -> None:
        """Display a 'Translating…' placeholder."""
        self._schedule(self._show_loading)

    def show_result(self, translation: str, original: str = "") -> None:
        """Display the finished translation."""
        self._schedule(lambda: self._show_result(translation, original))

    def show_error(self, message: str) -> None:
        """Display an error message."""
        self._schedule(lambda: self._show_error(message))

    def close(self) -> None:
        """Close the overlay immediately."""
        self._schedule(self._close)

    # ------------------------------------------------------------------
    # Private – must only be called from the Tk main thread
    # ------------------------------------------------------------------

    def _schedule(self, fn) -> None:
        """Run *fn* on the Tk thread."""
        if self._root is None or not self._root.winfo_exists():
            self._root = None
            t = threading.Thread(target=self._run_in_new_root(fn), daemon=True)
            t.start()
        else:
            self._root.after(0, fn)

    def _run_in_new_root(self, initial_fn):
        def _runner():
            self._build_window()
            self._root.after(0, initial_fn)
            self._root.mainloop()
        return _runner

    def _build_window(self) -> None:
        root = tk.Tk()
        root.title("ShallotT")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=_OVERLAY_BG)
        root.attributes("-alpha", 0.92)

        frame = tk.Frame(root, bg=_OVERLAY_BG, padx=12, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        header = tk.Label(
            frame, text="🧅 ShallotT", bg=_OVERLAY_BG, fg=_ACCENT,
            font=("Helvetica", 10, "bold"),
        )
        header.pack(anchor="w")

        self._text_var = tk.StringVar(value="Translating…")
        label = tk.Label(
            frame,
            textvariable=self._text_var,
            bg=_OVERLAY_BG, fg=_OVERLAY_FG,
            font=("Helvetica", 12),
            wraplength=480,
            justify=tk.LEFT,
        )
        label.pack(anchor="w", pady=(4, 0))

        close_btn = tk.Button(
            frame,
            text="✕",
            command=self._close,
            bg=_OVERLAY_BG, fg=_OVERLAY_FG,
            relief=tk.FLAT, cursor="hand2",
            font=("Helvetica", 9),
        )
        close_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-4, y=4)

        root.update_idletasks()
        self._position_window(root)
        self._root = root

    def _position_window(self, root: tk.Tk) -> None:
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w = root.winfo_reqwidth()
        h = root.winfo_reqheight()
        margin = 20
        pos = self._position

        if "right" in pos:
            x = sw - w - margin
        else:
            x = margin

        if "bottom" in pos:
            y = sh - h - margin - 40  # leave space for taskbar
        else:
            y = margin

        root.geometry(f"+{x}+{y}")

    def _show_loading(self) -> None:
        if self._text_var:
            self._text_var.set("⏳ Translating…")
        self._reset_timer()

    def _show_result(self, translation: str, original: str) -> None:
        if self._text_var:
            if original:
                self._text_var.set(f"📝 {original[:80]}…\n\n➡  {translation}")
            else:
                self._text_var.set(translation)
        self._reset_timer()

    def _show_error(self, message: str) -> None:
        if self._root and self._text_var:
            self._text_var.set(f"⚠ {message}")
            # Temporarily change colour to error red
            for widget in self._root.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and child.cget("textvariable"):
                            child.configure(fg=_ERROR_FG)
        self._reset_timer()

    def _reset_timer(self) -> None:
        if self._after_id and self._root:
            self._root.after_cancel(self._after_id)
        if self._root:
            self._after_id = self._root.after(self._duration * 1000, self._close)

    def _close(self) -> None:
        if self._root:
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            finally:
                self._root = None

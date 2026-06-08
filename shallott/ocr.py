"""OCR module for ShallotT.

Captures a screen region (or the full screen) and extracts text using
Tesseract OCR (via pytesseract).  The caller can then pass that text to
the translation engine.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _configure_tesseract(tesseract_cmd: str | None) -> None:
    """Point pytesseract at a custom Tesseract binary if configured."""
    if tesseract_cmd:
        import pytesseract  # noqa: PLC0415 – lazy import
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def capture_screen(region: tuple[int, int, int, int] | None = None):
    """Capture the screen (or a sub-region) and return a PIL Image.

    *region* – (left, top, width, height).  If None the full primary screen
    is captured.
    """
    import PIL.ImageGrab  # noqa: PLC0415

    if region is not None:
        left, top, width, height = region
        bbox = (left, top, left + width, top + height)
        return PIL.ImageGrab.grab(bbox=bbox)
    return PIL.ImageGrab.grab()


def image_to_text(image, lang: str = "eng") -> str:
    """Run Tesseract OCR on *image* and return the extracted text."""
    import pytesseract  # noqa: PLC0415

    return pytesseract.image_to_string(image, lang=lang).strip()


def capture_and_extract(
    cfg: dict[str, Any],
    region: tuple[int, int, int, int] | None = None,
) -> str:
    """One-shot helper: capture screen → OCR → return text.

    Reads OCR settings from *cfg["ocr"]*.
    """
    ocr_cfg = cfg.get("ocr", {})
    _configure_tesseract(ocr_cfg.get("tesseract_cmd"))
    lang = ocr_cfg.get("lang", "eng")

    image = capture_screen(region)
    text = image_to_text(image, lang=lang)
    logger.debug("OCR extracted %d chars", len(text))
    return text


def select_region_interactively() -> tuple[int, int, int, int] | None:
    """Open a simple full-screen overlay and let the user drag a rectangle.

    Returns (left, top, width, height) or None if the user cancelled.

    Requires tkinter (stdlib) and PIL.
    """
    import tkinter as tk  # noqa: PLC0415
    from PIL import ImageTk  # noqa: PLC0415
    import PIL.ImageGrab  # noqa: PLC0415

    screenshot = PIL.ImageGrab.grab()
    result: list[tuple[int, int, int, int] | None] = [None]

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.4)
    root.configure(background="black")
    root.attributes("-topmost", True)

    canvas = tk.Canvas(root, cursor="crosshair", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # Show the screenshot faintly under the overlay
    tk_img = ImageTk.PhotoImage(screenshot)
    canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

    start_x = start_y = 0
    rect_id = None

    def on_press(event: tk.Event) -> None:
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        rect_id = canvas.create_rectangle(
            start_x, start_y, start_x, start_y,
            outline="red", width=2,
        )

    def on_drag(event: tk.Event) -> None:
        if rect_id is not None:
            canvas.coords(rect_id, start_x, start_y, event.x, event.y)

    def on_release(event: tk.Event) -> None:
        x0, y0 = min(start_x, event.x), min(start_y, event.y)
        x1, y1 = max(start_x, event.x), max(start_y, event.y)
        if x1 - x0 > 5 and y1 - y0 > 5:
            result[0] = (x0, y0, x1 - x0, y1 - y0)
        root.destroy()

    def on_escape(event: tk.Event) -> None:  # noqa: ARG001
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_escape)

    root.mainloop()
    return result[0]

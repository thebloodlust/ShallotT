"""
Clipboard monitor + Desktop translation overlay for ShallotT.

Watches the system clipboard for new text and can display an
always-on-top floating translation popup on the desktop.
"""

import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer, QPoint
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QApplication
)
from PyQt6.QtGui import QFont, QColor, QPalette


class ClipboardWorker(QObject):
    """Background watcher: polls clipboard, emits signal on new text."""

    new_text = pyqtSignal(str)

    def __init__(self, interval_ms: int = 800):
        super().__init__()
        self._interval = interval_ms / 1000.0
        self._running = threading.Event()
        self._last_text = ""
        self._thread = None

    @property
    def running(self) -> bool:
        return self._running.is_set()

    def start(self):
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()

    def _poll(self):
        # Initialise with current clipboard so we don't re-trigger on old text
        try:
            app = QApplication.instance()
            if app:
                self._last_text = app.clipboard().text() or ""
        except Exception:
            pass

        while self._running.is_set():
            time.sleep(self._interval)
            try:
                app = QApplication.instance()
                if not app:
                    continue
                text = app.clipboard().text()
                if text and text != self._last_text:
                    self._last_text = text
                    self.new_text.emit(text)
            except Exception:
                pass


# ── Desktop translation popup ─────────────────────────────────────

class DesktopTranslationPopup(QWidget):
    """Small always-on-top floating window showing a translation result.

    Usage:
        popup = DesktopTranslationPopup()
        popup.show_translation("Hola", "Hello", "Spanish → English")
        popup.hide()
    """

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._setup_ui()
        self.resize(380, 200)

    def _setup_ui(self):
        self.setStyleSheet("""
            DesktopTranslationPopup {
                background-color: #181825;
                border: 2px solid #ffaa33;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        self._title_label = QLabel("ShallotT Translation 🧅")
        self._title_label.setStyleSheet(
            "color: #ffaa33; font-weight: bold; font-size: 12px; border: none; background: transparent;"
        )
        header.addWidget(self._title_label)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #cdd6f4; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #f38ba8; }"
        )
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Source text (italic, muted, truncated)
        self._source_label = QLabel("")
        self._source_label.setWordWrap(True)
        self._source_label.setMaximumHeight(35)
        self._source_label.setStyleSheet(
            "color: #707a8a; font-style: italic; font-size: 11px; border: none; background: transparent;"
        )
        layout.addWidget(self._source_label)

        # Translation result
        self._result_edit = QTextEdit()
        self._result_edit.setReadOnly(True)
        self._result_edit.setStyleSheet(
            "QTextEdit { background: #1e1e2e; color: #a6e3a1; border: 1px solid #313244; "
            "border-radius: 6px; padding: 6px; font-size: 12px; }"
        )
        self._result_edit.setMaximumHeight(100)
        layout.addWidget(self._result_edit)

        # Actions row
        actions = QHBoxLayout()
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setStyleSheet(
            "QPushButton { background: #585b70; color: #cdd6f4; border: none; "
            "border-radius: 3px; padding: 3px 10px; font-size: 10px; }"
            "QPushButton:hover { background: #6c7086; }"
        )
        copy_btn.clicked.connect(self._copy_result)
        actions.addWidget(copy_btn)
        actions.addStretch()

        self._lang_label = QLabel("")
        self._lang_label.setStyleSheet("color: #707a8a; font-size: 9px; border: none; background: transparent;")
        actions.addWidget(self._lang_label)
        layout.addLayout(actions)

    def show_translation(self, source: str, result: str, lang_info: str = ""):
        """Display a translation in the popup."""
        self._source_label.setText(
            f'"{source[:120]}{"…" if len(source) > 120 else ""}"'
        )
        self._result_edit.setPlainText(result)
        self._lang_label.setText(lang_info)
        self._position_near_cursor()
        self.show()

    def _position_near_cursor(self):
        """Place popup near the current mouse cursor position."""
        from PyQt6.QtGui import QCursor
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if screen:
            geom = screen.availableGeometry()
            x = min(cursor_pos.x() + 20, geom.right() - self.width() - 20)
            y = min(cursor_pos.y() + 20, geom.bottom() - self.height() - 20)
            self.move(max(x, geom.left() + 10), max(y, geom.top() + 10))
        else:
            self.move(cursor_pos.x() + 20, cursor_pos.y() + 20)

    def _copy_result(self):
        text = self._result_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self._title_label.setText("✓ Copied!")
            QTimer.singleShot(1500, lambda: self._title_label.setText("ShallotT Translation 🧅"))

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

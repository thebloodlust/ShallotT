import sys
import threading
import re
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QComboBox, QPushButton, QLabel, QLineEdit, QCheckBox, 
    QMessageBox, QSystemTrayIcon, QMenu, QGroupBox, QTabWidget,
    QApplication
)
from PyQt6.QtGui import QFont, QIcon, QAction, QColor, QPalette, QKeySequence, QPixmap
import pyperclip

from src.config import load_config, save_config, CONFIG_PATH
from src.ollama_client import OllamaTranslator

LANGUAGES = [
    "French", "English", "Spanish", "German", 
    "Italian", "Portuguese", "Chinese", "Japanese", "Russian"
]

SOURCE_LANGUAGES = ["Auto Detection"] + LANGUAGES

class TranslationWorker(threading.Thread):
    """Worker thread to run translation without freezing the Qt UI."""
    def __init__(self, translator, text, src_lang, target_lang, callback, lamba_err):
        super().__init__()
        self.translator = translator
        self.text = text
        self.src_lang = src_lang
        self.target_lang = target_lang
        self.callback = callback
        self.lambda_err = lamba_err

    def run(self):
        try:
            translation = self.translator.translate(self.text, self.src_lang, self.target_lang)
            self.callback(translation)
        except Exception as e:
            self.lambda_err(str(e))


class ShallotTApp(QMainWindow):
    # Signals for safe communication between threads and main PyQt UI
    translation_done = pyqtSignal(str)
    translation_failed = pyqtSignal(str)
    trigger_translate_shortcut = pyqtSignal()
    trigger_ocr_shortcut = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.translator = OllamaTranslator(
            base_url=self.config["ollama_url"],
            model=self.config["ollama_model"],
            api_key=self.config.get("ollama_api_key", "")
        )
        
        self.init_timer = QTimer()
        self.init_timer.setSingleShot(True)
        self.init_timer.timeout.connect(self.trigger_automagic_translation)
        
        # UI setup
        self.setWindowTitle("ShallotT - DeepL AI Local")
        self.resize(750, 480)
        
        # Load custom Shallot icon
        import os
        icon_path = os.path.join(os.path.dirname(__file__), "shallot.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.setup_dark_theme()
        
        self.init_ui()
        self.setup_system_tray()
        
        # Connect signals
        self.translation_done.connect(self.on_translation_success)
        self.translation_failed.connect(self.on_translation_error)
        self.trigger_translate_shortcut.connect(self.handle_global_translate_shortcut)
        self.trigger_ocr_shortcut.connect(self.handle_global_ocr_shortcut)
        
        # Keep loading models in background
        QTimer.singleShot(100, self.refresh_ollama_models)

    def setup_dark_theme(self):
        """Sets an incredibly sleek, dark theme for the application (similar to DeepL/Modern Dark)."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(24, 24, 37))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(205, 214, 244))
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 46))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(17, 17, 27))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(205, 214, 244))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(17, 17, 27))
        palette.setColor(QPalette.ColorRole.Text, QColor(205, 214, 244))
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 47, 72))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(205, 214, 244))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(137, 180, 250))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(137, 180, 250))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(17, 17, 27))
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #181825;
            }
            QWidget {
                color: #cdd6f4;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 10px;
                color: #cdd6f4;
            }
            QTextEdit:focus {
                border: 1px solid #89b4fa;
            }
            QComboBox, QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 5px 10px;
                color: #cdd6f4;
                min-height: 25px;
            }
            QComboBox:focus, QLineEdit:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                border: none;
                border-radius: 5px;
                padding: 6px 15px;
                font-weight: bold;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:pressed {
                background-color: #74c7ec;
            }
            QPushButton#secondaryBtn {
                background-color: #45475a;
                color: #cdd6f4;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #585b70;
            }
            QTabWidget::pane {
                border: 1px solid #313244;
                border-radius: 6px;
                background-color: #1e1e2e;
            }
            QTabBar::tab {
                background: #11111b;
                border: 1px solid #313244;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #1e1e2e;
                font-weight: bold;
            }
            QStatusBar {
                background: #11111b;
                color: #a6adc8;
            }
        """)

    def init_ui(self):
        # Central Widget & Tab system
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # --- TAB 1: TRANSLATOR SIDE ---
        translator_widget = QWidget()
        trans_layout = QVBoxLayout(translator_widget)
        trans_layout.setContentsMargins(8, 8, 8, 8)
        
        # Language Selectors bar
        lang_bar = QHBoxLayout()
        
        self.src_lang_box = QComboBox()
        self.src_lang_box.addItems(SOURCE_LANGUAGES)
        self.src_lang_box.setCurrentText(self.config["source_lang"])
        self.src_lang_box.currentTextChanged.connect(self.on_lang_changed)
        
        swap_btn = QPushButton("⇄")
        swap_btn.setObjectName("secondaryBtn")
        swap_btn.setFixedWidth(40)
        swap_btn.clicked.connect(self.swap_languages)
        
        self.target_lang_box = QComboBox()
        self.target_lang_box.addItems(LANGUAGES)
        self.target_lang_box.setCurrentText(self.config["target_lang"])
        self.target_lang_box.currentTextChanged.connect(self.on_lang_changed)
        
        self.auto_translate_cb = QCheckBox("Auto Translate")
        self.auto_translate_cb.setChecked(True)
        
        lang_bar.addWidget(QLabel("From:"))
        lang_bar.addWidget(self.src_lang_box)
        lang_bar.addWidget(swap_btn)
        lang_bar.addWidget(QLabel("To:"))
        lang_bar.addWidget(self.target_lang_box)
        lang_bar.addStretch()
        lang_bar.addWidget(self.auto_translate_cb)
        
        trans_layout.addLayout(lang_bar)
        
        # Double text area
        text_layout = QHBoxLayout()
        
        # Source panel
        src_vbox = QVBoxLayout()
        self.src_text_edit = QTextEdit()
        self.src_text_edit.setPlaceholderText("Type or paste text to translate... (Ctrl+C+C to translate selection globally)")
        self.src_text_edit.textChanged.connect(self.on_source_text_changed)
        self.src_text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.src_text_edit.customContextMenuRequested.connect(self.show_custom_context_menu)
        
        src_bottom = QHBoxLayout()
        self.char_count_lbl = QLabel("0 characters")
        src_bottom.addWidget(self.char_count_lbl)
        src_bottom.addStretch()
        
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.clicked.connect(self.src_text_edit.clear)
        src_bottom.addWidget(clear_btn)
        src_vbox.addWidget(self.src_text_edit)
        src_vbox.addLayout(src_bottom)
        
        # Cible panel
        target_vbox = QVBoxLayout()
        self.target_text_edit = QTextEdit()
        self.target_text_edit.setReadOnly(True)
        self.target_text_edit.setPlaceholderText("Translation will appear here...")
        self.target_text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.target_text_edit.customContextMenuRequested.connect(self.show_custom_context_menu)
        
        target_bottom = QHBoxLayout()
        self.status_lbl = QLabel("Ready")
        target_bottom.addWidget(self.status_lbl)
        target_bottom.addStretch()
        
        self.copy_btn = QPushButton("Copy Text")
        self.copy_btn.clicked.connect(self.copy_translation_to_clipboard)
        target_bottom.addWidget(self.copy_btn)
        
        target_vbox.addWidget(self.target_text_edit)
        target_vbox.addLayout(target_bottom)
        
        text_layout.addLayout(src_vbox, 1)
        text_layout.addLayout(target_vbox, 1)
        
        trans_layout.addLayout(text_layout)
        
        # Manual Translate Button at bottom
        self.translate_btn = QPushButton("Translate (Enter)")
        self.translate_btn.clicked.connect(self.trigger_manual_translation)
        trans_layout.addWidget(self.translate_btn)
        
        self.tabs.addTab(translator_widget, "Translator")
        
        # --- TAB 2: SETTINGS SIDE ---
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        
        # Ollama parameters
        ollama_group = QGroupBox("Ollama Configuration")
        og_layout = QVBoxLayout(ollama_group)
        
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Ollama URL:"))
        self.url_input = QLineEdit(self.config["ollama_url"])
        url_layout.addWidget(self.url_input)
        og_layout.addLayout(url_layout)
        
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API Key/Bearer Token (Optional):"))
        self.key_input = QLineEdit(self.config.get("ollama_api_key", ""))
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Paste token to bypass remote reverse proxy auth")
        key_layout.addWidget(self.key_input)
        og_layout.addLayout(key_layout)
        
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItem(self.config["ollama_model"])
        model_layout.addWidget(self.model_combo)
        
        self.check_conn_btn = QPushButton("Check Connection & Fetch Models")
        self.check_conn_btn.setObjectName("secondaryBtn")
        self.check_conn_btn.clicked.connect(self.refresh_ollama_models)
        model_layout.addWidget(self.check_conn_btn)
        og_layout.addLayout(model_layout)
        
        settings_layout.addWidget(ollama_group)
        
        # Shortcuts Info & Customization
        shortcuts_group = QGroupBox("Keyboard Shortcuts (Raccourcis globaux)")
        sg_layout = QVBoxLayout(shortcuts_group)
        
        # Translate shortcut input
        trans_sh_layout = QHBoxLayout()
        trans_sh_layout.addWidget(QLabel("Translate Selection Shortcut:"))
        self.shortcut_translate_input = QLineEdit(self.config.get("shortcut_translate", "ctrl+c+c"))
        self.shortcut_translate_input.setPlaceholderText("e.g. ctrl+c+c or ctrl+alt+t")
        trans_sh_layout.addWidget(self.shortcut_translate_input)
        sg_layout.addLayout(trans_sh_layout)
        
        # OCR shortcut input
        ocr_sh_layout = QHBoxLayout()
        ocr_sh_layout.addWidget(QLabel("OCR Screenshot Shortcut:"))
        self.shortcut_ocr_input = QLineEdit(self.config.get("shortcut_ocr", "ctrl+f8"))
        self.shortcut_ocr_input.setPlaceholderText("e.g. ctrl+f8 or ctrl+alt+o")
        ocr_sh_layout.addWidget(self.shortcut_ocr_input)
        sg_layout.addLayout(ocr_sh_layout)
        
        sg_layout.addWidget(QLabel("<i>Tips: Use <b>ctrl+c+c</b> for double-C press gesture. Other shortcuts can be formatted like <b>ctrl+alt+t</b>.</i>"))
        sg_layout.addWidget(QLabel("<i>Note: On Linux, if Wayland blocks background shortcuts, register them in your desktop hotkey settings using application flags <b>--translate</b> or <b>--ocr</b>.</i>"))
        settings_layout.addWidget(shortcuts_group)
        
        settings_layout.addStretch()
        
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_app_settings)
        save_layout.addWidget(save_btn)
        settings_layout.addLayout(save_layout)
        
        self.tabs.addTab(settings_widget, "Settings")
        
        # Status Bar
        self.statusBar().showMessage(f"Connected to {self.config['ollama_url']} ({self.config['ollama_model']})")

    def setup_system_tray(self):
        """Sets up the icon in the system menu bar for background running."""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Simple native looking drawing or fallback to simple icon
        import os
        icon_path = os.path.join(os.path.dirname(__file__), "shallot.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Create a tiny custom 64x64 pixmap fallback for ShallotT
            pixmap = QPixmap(64, 64)
            pixmap.fill(QColor(137, 180, 250)) # matching light blue accent
            self.tray_icon.setIcon(QIcon(pixmap))
        
        # Create context menu
        tray_menu = QMenu()
        show_action = QAction("Open Translator", self)
        show_action.triggered.connect(self.show_normal)
        
        self.auto_start_tray_action = QAction("Run in Tray", self)
        self.auto_start_tray_action.setCheckable(True)
        self.auto_start_tray_action.setChecked(True)
        
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(QApplication.quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(self.auto_start_tray_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def show_normal(self):
        """Shows window, restores from minimized/tray state, brings to front."""
        self.show()
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.activateWindow()
        self.raise_()
        self.src_text_edit.setFocus()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def closeEvent(self, event):
        """Override close event so closing window minimizes to system tray."""
        if self.tray_icon.isVisible() and self.auto_start_tray_action.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "ShallotT Running",
                "ShallotT is running in the background. Use Ctrl+C+C to translate anytime.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            event.accept()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized() and self.auto_start_tray_action.isChecked():
                QTimer.singleShot(0, self.hide)
                event.ignore()
        super().changeEvent(event)

    def contextMenuEvent(self, event):
        self.show_custom_context_menu(global_pos=event.globalPos())

    def show_custom_context_menu(self, pos=None, global_pos=None):
        menu = QMenu(self)
        menu.setTitle("ShallotT Quick Actions")
        
        # Add basic text actions if triggered from text edit
        sender = self.sender()
        if isinstance(sender, QTextEdit):
            std_menu = sender.createStandardContextMenu()
            for action in std_menu.actions():
                menu.addAction(action)
            menu.addSeparator()
            
        # Target language force submenu
        lang_submenu = menu.addMenu("Force Output Language (Forcer la langue)")
        for lang in LANGUAGES:
            action = lang_submenu.addAction(lang)
            action.triggered.connect(lambda checked, l=lang: self.force_output_language(l))
            
        # Reposition submenu
        pos_submenu = menu.addMenu("Reposition Window (Repositionner la fenêtre)")
        positions = [
            ("Top-Left (Haut-Gauche)", "top-left"),
            ("Top-Right (Haut-Droite)", "top-right"),
            ("Bottom-Left (Bas-Gauche)", "bottom-left"),
            ("Bottom-Right (Bas-Droite)", "bottom-right"),
            ("Center (Centrer)", "center")
        ]
        for label, pos_code in positions:
            action = pos_submenu.addAction(label)
            action.triggered.connect(lambda checked, p=pos_code: self.reposition_window(p))
            
        # Execute menu
        if global_pos:
            menu.exec(global_pos)
        elif pos and isinstance(sender, QWidget):
            menu.exec(sender.mapToGlobal(pos))
        else:
            menu.exec(self.cursor().pos())

    def force_output_language(self, language_name):
        self.target_lang_box.setCurrentText(language_name)
        self.statusBar().showMessage(f"Language forced to: {language_name}", 3000)
        self.translate_text()

    def reposition_window(self, position):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geom = screen.availableGeometry()
        width = self.width()
        height = self.height()
        
        if position == "top-left":
            self.move(geom.left() + 20, geom.top() + 20)
        elif position == "top-right":
            self.move(geom.right() - width - 20, geom.top() + 20)
        elif position == "bottom-left":
            self.move(geom.left() + 20, geom.bottom() - height - 20)
        elif position == "bottom-right":
            self.move(geom.right() - width - 20, geom.bottom() - height - 20)
        elif position == "center":
            self.move(
                geom.left() + (geom.width() - width) // 2,
                geom.top() + (geom.height() - height) // 2
            )
        self.statusBar().showMessage(f"Window moved to: {position}", 2000)

    def detect_text_language(self, text):
        if not text:
            return "unknown"
        words = re.findall(r'\b[a-zA-Z]{2,12}\b', text.lower())
        if not words:
            return "unknown"
            
        english_stopwords = {"the", "and", "of", "to", "is", "that", "it", "for", "on", "was", "with", "as", "at", "by", "an", "be", "this", "are", "you", "from", "have", "not", "or", "but"}
        french_stopwords = {"le", "la", "les", "et", "est", "dans", "pour", "une", "des", "qui", "que", "un", "du", "en", "pour", "par", "sur", "avec", "mais", "ou", "ce", "cette"}
        
        eng_count = sum(1 for w in words if w in english_stopwords)
        fre_count = sum(1 for w in words if w in french_stopwords)
        
        if eng_count > fre_count:
            return "English"
        elif fre_count > eng_count:
            return "French"
        return "unknown"

    # --- ACTIONS ---

    def on_source_text_changed(self):
        text = self.src_text_edit.toPlainText()
        self.char_count_lbl.setText(f"{len(text)} characters")
        
        # Auto-translate after 650ms of inactivity
        if self.auto_translate_cb.isChecked() and text.strip():
            self.init_timer.start(650)

    def on_lang_changed(self):
        # Trigger immediate translation if there is source text
        if self.src_text_edit.toPlainText().strip():
            self.trigger_automagic_translation()

    def swap_languages(self):
        src = self.src_lang_box.currentText()
        target = self.target_lang_box.currentText()
        
        # If source is Auto Detection, we can't fully swap cleanly back, but we can set default
        if src == "Auto Detection":
            self.src_lang_box.setCurrentText("English")
            self.target_lang_box.setCurrentText("French")
        else:
            self.src_lang_box.setCurrentText(target)
            self.target_lang_box.setCurrentText(src)

    def trigger_automagic_translation(self):
        self.translate_text()

    def trigger_manual_translation(self):
        self.init_timer.stop()
        self.translate_text()

    def translate_text(self):
        text = self.src_text_edit.toPlainText().strip()
        if not text:
            self.target_text_edit.clear()
            return
            
        src_lang = self.src_lang_box.currentText()
        target_lang = self.target_lang_box.currentText()
        
        # Smart target language auto-swap if source text matches target language
        detected_lang = self.detect_text_language(text)
        if detected_lang == "English" and target_lang == "English":
            self.target_lang_box.blockSignals(True)
            self.target_lang_box.setCurrentText("French")
            self.target_lang_box.blockSignals(False)
            target_lang = "French"
        elif detected_lang == "French" and target_lang == "French":
            self.target_lang_box.blockSignals(True)
            self.target_lang_box.setCurrentText("English")
            self.target_lang_box.blockSignals(False)
            target_lang = "English"
        
        self.status_lbl.setText("Decoding / Connecting to Ollama...")
        self.statusBar().showMessage("Translating...")
        
        # Deploy worker thread
        worker = TranslationWorker(
            self.translator, text, src_lang, target_lang, 
            self.translation_done.emit, self.translation_failed.emit
        )
        worker.start()

    def on_translation_success(self, text):
        self.target_text_edit.setPlainText(text)
        self.status_lbl.setText("Success")
        self.statusBar().showMessage("Translation complete.", 3000)

    def on_translation_error(self, err_msg):
        self.status_lbl.setText("Error")
        self.statusBar().showMessage("Translation failed.", 3000)
        # Display visual error notice
        self.target_text_edit.setPlainText(f"❌ Error:\n{err_msg}")

    def copy_translation_to_clipboard(self):
        text = self.target_text_edit.toPlainText()
        if text:
            pyperclip.copy(text)
            self.statusBar().showMessage("Translation copied to clipboard!", 2000)

    def refresh_ollama_models(self):
        """Fetch available models from the Ollama server."""
        self.check_conn_btn.setText("Connecting...")
        
        # Perform check in a safe non-blocking way using QTimer / Threading if required, 
        # but a simple thread is cleaner.
        def fetch_task():
            # Update translator settings first
            url = self.url_input.text().strip()
            key = self.key_input.text().strip()
            self.translator.base_url = url.rstrip('/')
            self.translator.api_key = key
            
            connected, models = self.translator.check_connection()
            
            def update_ui():
                if connected:
                    current_model = self.config["ollama_model"]
                    self.model_combo.clear()
                    
                    # Fill available models
                    for m in models:
                        self.model_combo.addItem(m)
                    
                    if current_model in models:
                        self.model_combo.setCurrentText(current_model)
                    elif models:
                        self.model_combo.setCurrentIndex(0)
                        
                    self.statusBar().showMessage(f"Connected to Ollama! Found {len(models)} models.", 4000)
                    self.check_conn_btn.setText("Connected ✓")
                else:
                    self.statusBar().showMessage("Could not connect to Ollama server.", 4000)
                    self.check_conn_btn.setText("Failed ✗")
            
            QTimer.singleShot(0, update_ui)
            
        threading.Thread(target=fetch_task, daemon=True).start()

    def save_app_settings(self):
        url = self.url_input.text().strip()
        model = self.model_combo.currentText().strip()
        key = self.key_input.text().strip()
        
        if not url or not model:
            QMessageBox.warning(self, "Invalid Inputs", "URL and Model fields cannot be empty.")
            return
            
        self.config["ollama_url"] = url
        self.config["ollama_model"] = model
        self.config["ollama_api_key"] = key
        self.config["source_lang"] = self.src_lang_box.currentText()
        self.config["target_lang"] = self.target_lang_box.currentText()
        
        # Save custom shortcuts
        self.config["shortcut_translate"] = self.shortcut_translate_input.text().strip().lower()
        self.config["shortcut_ocr"] = self.shortcut_ocr_input.text().strip().lower()
        
        save_config(self.config)
        
        # Re-initialize translator
        self.translator = OllamaTranslator(base_url=url, model=model, api_key=key)
        
        QMessageBox.information(self, "Settings Saved", f"Configuration updated and saved to:\n{CONFIG_PATH}")
        self.statusBar().showMessage(f"Active configuration: {model}@{url}", 4000)

    # --- INCOMING EXTERNAL TRIGGERS (from shortcuts) ---

    def handle_global_translate_shortcut(self):
        """
        Called when Ctrl+C+C is detected.
        Reads selected text from clipboard, opens window and translates immediately!
        """
        # Sleep slightly to let the clipboard copy event complete
        QTimer.singleShot(80, self._process_clipboard_translation)

    def _process_clipboard_translation(self):
        try:
            copied_text = pyperclip.paste()
            if copied_text and copied_text.strip():
                # Display window immediately
                self.show_normal()
                self.src_text_edit.setPlainText(copied_text)
                # Auto translation is triggered via on_source_text_changed or we force it:
                self.translate_text()
        except Exception as e:
            self.statusBar().showMessage(f"Clipboard read error: {e}", 3000)

    def handle_global_ocr_shortcut(self):
        """
        Called when Ctrl+F8 is detected.
        Triggers Screen selection for OCR.
        """
        # We must call the OCR utility. Since we are in the main GUI thread, we can run it safely.
        from src.ocr import run_ocr_capture
        
        def on_ocr_text_ready(text):
            if text:
                if text.startswith("[OCR Error]"):
                    self.show_normal()
                    self.src_text_edit.setPlainText(text)
                else:
                    self.show_normal()
                    self.src_text_edit.setPlainText(text)
                    self.translate_text()
                    
        # Launch capture overlay
        run_ocr_capture(on_ocr_text_ready)

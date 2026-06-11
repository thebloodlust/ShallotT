import sys
import threading
import re
from string import Template
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QComboBox, QPushButton, QLabel, QLineEdit, QCheckBox, 
    QMessageBox, QSystemTrayIcon, QMenu, QGroupBox, QTabWidget,
    QApplication, QSpinBox
)
from PyQt6.QtGui import QFont, QIcon, QAction, QColor, QPalette, QKeySequence, QPixmap

from src.config import load_config, save_config, CONFIG_PATH
from src.ollama_client import OllamaTranslator

LANGUAGES = [
    "French", "English", "Spanish", "German", 
    "Italian", "Portuguese", "Chinese", "Japanese", "Russian"
]

SOURCE_LANGUAGES = ["Auto Detection"] + LANGUAGES

# Color tokens for each available skin. "pal_*" entries feed the QPalette,
# the rest feed the QSS template in ShallotTApp.apply_theme().
THEMES = {
    "dark": {
        "pal_window": "#181825", "pal_windowtext": "#cdd6f4", "pal_base": "#1e1e2e",
        "pal_alternatebase": "#11111b", "pal_tooltipbase": "#cdd6f4", "pal_tooltiptext": "#11111b",
        "pal_text": "#cdd6f4", "pal_button": "#2d2f48", "pal_buttontext": "#cdd6f4",
        "pal_brighttext": "#89b4fa", "pal_highlight": "#89b4fa", "pal_highlightedtext": "#11111b",
        "window_bg": "#181825", "text": "#cdd6f4",
        "textedit_bg": "#1e1e2e", "textedit_border": "#313244", "focus_border": "#89b4fa",
        "input_bg": "#313244", "input_border": "#45475a",
        "combo_view_bg": "#1e1e2e", "combo_view_text": "#cdd6f4",
        "combo_view_sel_bg": "#313244", "combo_view_sel_text": "#89b4fa",
        "groupbox_border": "#45475a",
        "accent_bg": "#89b4fa", "accent_text": "#11111b", "accent_hover": "#b4befe", "accent_pressed": "#74c7ec",
        "secondary_bg": "#45475a", "secondary_text": "#cdd6f4", "secondary_border": "#45475a", "secondary_hover": "#585b70",
        "tab_pane_bg": "#1e1e2e", "tab_pane_border": "#313244",
        "tabbar_bg": "#11111b", "tabbar_border": "#313244", "tabbar_text": "#cdd6f4",
        "tab_selected_bg": "#1e1e2e", "tab_selected_text": "#cdd6f4",
        "statusbar_bg": "#11111b", "statusbar_text": "#a6adc8",
    },
    "light": {
        "pal_window": "#f0f0f5", "pal_windowtext": "#1e1e2e", "pal_base": "#ffffff",
        "pal_alternatebase": "#e1e1e6", "pal_tooltipbase": "#1e1e2e", "pal_tooltiptext": "#ffffff",
        "pal_text": "#1e1e2e", "pal_button": "#dcdce1", "pal_buttontext": "#1e1e2e",
        "pal_brighttext": "#2563eb", "pal_highlight": "#2563eb", "pal_highlightedtext": "#ffffff",
        "window_bg": "#f0f0f5", "text": "#1e1e2e",
        "textedit_bg": "#ffffff", "textedit_border": "#cccccc", "focus_border": "#2563eb",
        "input_bg": "#ffffff", "input_border": "#cccccc",
        "combo_view_bg": "#ffffff", "combo_view_text": "#1e1e2e",
        "combo_view_sel_bg": "#e5e5ea", "combo_view_sel_text": "#2563eb",
        "groupbox_border": "#cccccc",
        "accent_bg": "#2563eb", "accent_text": "#ffffff", "accent_hover": "#1d4ed8", "accent_pressed": "#1e40af",
        "secondary_bg": "#e5e5ea", "secondary_text": "#1e1e2e", "secondary_border": "#cccccc", "secondary_hover": "#d1d1d6",
        "tab_pane_bg": "#ffffff", "tab_pane_border": "#cccccc",
        "tabbar_bg": "#e5e5ea", "tabbar_border": "#cccccc", "tabbar_text": "#1e1e2e",
        "tab_selected_bg": "#ffffff", "tab_selected_text": "#1e1e2e",
        "statusbar_bg": "#f0f0f5", "statusbar_text": "#555555",
    },
    "nord": {
        "pal_window": "#2e3440", "pal_windowtext": "#eceff4", "pal_base": "#3b4252",
        "pal_alternatebase": "#2e3440", "pal_tooltipbase": "#eceff4", "pal_tooltiptext": "#2e3440",
        "pal_text": "#e5e9f0", "pal_button": "#434c5e", "pal_buttontext": "#eceff4",
        "pal_brighttext": "#88c0d0", "pal_highlight": "#88c0d0", "pal_highlightedtext": "#2e3440",
        "window_bg": "#2e3440", "text": "#e5e9f0",
        "textedit_bg": "#3b4252", "textedit_border": "#4c566a", "focus_border": "#88c0d0",
        "input_bg": "#434c5e", "input_border": "#4c566a",
        "combo_view_bg": "#3b4252", "combo_view_text": "#e5e9f0",
        "combo_view_sel_bg": "#434c5e", "combo_view_sel_text": "#88c0d0",
        "groupbox_border": "#4c566a",
        "accent_bg": "#88c0d0", "accent_text": "#2e3440", "accent_hover": "#8fbcbb", "accent_pressed": "#81a1c1",
        "secondary_bg": "#4c566a", "secondary_text": "#eceff4", "secondary_border": "#4c566a", "secondary_hover": "#5e6a82",
        "tab_pane_bg": "#3b4252", "tab_pane_border": "#434c5e",
        "tabbar_bg": "#242933", "tabbar_border": "#434c5e", "tabbar_text": "#d8dee9",
        "tab_selected_bg": "#3b4252", "tab_selected_text": "#eceff4",
        "statusbar_bg": "#242933", "statusbar_text": "#9ca7b8",
    },
    "solarized": {
        "pal_window": "#fdf6e3", "pal_windowtext": "#073642", "pal_base": "#eee8d5",
        "pal_alternatebase": "#fdf6e3", "pal_tooltipbase": "#073642", "pal_tooltiptext": "#fdf6e3",
        "pal_text": "#073642", "pal_button": "#eee8d5", "pal_buttontext": "#073642",
        "pal_brighttext": "#268bd2", "pal_highlight": "#268bd2", "pal_highlightedtext": "#fdf6e3",
        "window_bg": "#fdf6e3", "text": "#073642",
        "textedit_bg": "#fffbef", "textedit_border": "#93a1a1", "focus_border": "#268bd2",
        "input_bg": "#eee8d5", "input_border": "#93a1a1",
        "combo_view_bg": "#eee8d5", "combo_view_text": "#073642",
        "combo_view_sel_bg": "#d8d2bf", "combo_view_sel_text": "#268bd2",
        "groupbox_border": "#93a1a1",
        "accent_bg": "#268bd2", "accent_text": "#fdf6e3", "accent_hover": "#2aa198", "accent_pressed": "#6c71c4",
        "secondary_bg": "#eee8d5", "secondary_text": "#586e75", "secondary_border": "#93a1a1", "secondary_hover": "#e4ddc8",
        "tab_pane_bg": "#fffbef", "tab_pane_border": "#93a1a1",
        "tabbar_bg": "#eee8d5", "tabbar_border": "#93a1a1", "tabbar_text": "#586e75",
        "tab_selected_bg": "#fffbef", "tab_selected_text": "#073642",
        "statusbar_bg": "#eee8d5", "statusbar_text": "#657b83",
    },
    "sepia": {
        "pal_window": "#f4ecd8", "pal_windowtext": "#5b4636", "pal_base": "#fbf1e0",
        "pal_alternatebase": "#ece0c8", "pal_tooltipbase": "#5b4636", "pal_tooltiptext": "#fbf1e0",
        "pal_text": "#5b4636", "pal_button": "#e8dcc5", "pal_buttontext": "#5b4636",
        "pal_brighttext": "#a9744f", "pal_highlight": "#a9744f", "pal_highlightedtext": "#fbf1e0",
        "window_bg": "#f4ecd8", "text": "#5b4636",
        "textedit_bg": "#fbf1e0", "textedit_border": "#d8c3a5", "focus_border": "#a9744f",
        "input_bg": "#fbf1e0", "input_border": "#d8c3a5",
        "combo_view_bg": "#fbf1e0", "combo_view_text": "#5b4636",
        "combo_view_sel_bg": "#e8dcc5", "combo_view_sel_text": "#a9744f",
        "groupbox_border": "#d8c3a5",
        "accent_bg": "#a9744f", "accent_text": "#fdf6ec", "accent_hover": "#bf8b66", "accent_pressed": "#8f5f3d",
        "secondary_bg": "#e8dcc5", "secondary_text": "#5b4636", "secondary_border": "#d8c3a5", "secondary_hover": "#ddcdae",
        "tab_pane_bg": "#fbf1e0", "tab_pane_border": "#d8c3a5",
        "tabbar_bg": "#e8dcc5", "tabbar_border": "#d8c3a5", "tabbar_text": "#5b4636",
        "tab_selected_bg": "#fbf1e0", "tab_selected_text": "#5b4636",
        "statusbar_bg": "#e8dcc5", "statusbar_text": "#7a6450",
    },
    "contrast": {
        "pal_window": "#000000", "pal_windowtext": "#ffff00", "pal_base": "#000000",
        "pal_alternatebase": "#1a1a1a", "pal_tooltipbase": "#ffff00", "pal_tooltiptext": "#000000",
        "pal_text": "#ffff00", "pal_button": "#1a1a1a", "pal_buttontext": "#ffff00",
        "pal_brighttext": "#00ffff", "pal_highlight": "#ffff00", "pal_highlightedtext": "#000000",
        "window_bg": "#000000", "text": "#ffff00",
        "textedit_bg": "#000000", "textedit_border": "#ffff00", "focus_border": "#00ffff",
        "input_bg": "#000000", "input_border": "#ffff00",
        "combo_view_bg": "#000000", "combo_view_text": "#ffff00",
        "combo_view_sel_bg": "#ffff00", "combo_view_sel_text": "#000000",
        "groupbox_border": "#ffff00",
        "accent_bg": "#ffff00", "accent_text": "#000000", "accent_hover": "#ffffff", "accent_pressed": "#cccc00",
        "secondary_bg": "#1a1a1a", "secondary_text": "#ffff00", "secondary_border": "#ffff00", "secondary_hover": "#333300",
        "tab_pane_bg": "#000000", "tab_pane_border": "#ffff00",
        "tabbar_bg": "#000000", "tabbar_border": "#ffff00", "tabbar_text": "#ffff00",
        "tab_selected_bg": "#1a1a1a", "tab_selected_text": "#00ffff",
        "statusbar_bg": "#000000", "statusbar_text": "#ffff00",
    },
}

# Display labels shown in the theme picker, in display order.
THEME_LABELS = {
    "dark": "Dark Theme (Sombre)",
    "light": "Light Theme (Clair)",
    "nord": "Nord (Bleu glacial)",
    "solarized": "Solarized Light (Lecture)",
    "sepia": "Sépia (Confort visuel)",
    "contrast": "Contraste élevé (Accessibilité)",
}

_STYLESHEET_TEMPLATE = Template("""
    QMainWindow {
        background-color: $window_bg;
    }
    QWidget {
        color: $text;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    QGroupBox {
        border: 1px solid $groupbox_border;
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
        background-color: $textedit_bg;
        border: 1px solid $textedit_border;
        border-radius: 6px;
        padding: 10px;
        color: $text;
    }
    QTextEdit:focus {
        border: 1px solid $focus_border;
    }
    QComboBox, QLineEdit {
        background-color: $input_bg;
        border: 1px solid $input_border;
        border-radius: 4px;
        padding: 5px 10px;
        color: $text;
        min-height: 25px;
    }
    QComboBox QAbstractItemView {
        background-color: $combo_view_bg;
        color: $combo_view_text;
        selection-background-color: $combo_view_sel_bg;
        selection-color: $combo_view_sel_text;
        border: 1px solid $input_border;
    }
    QSpinBox {
        background-color: $input_bg;
        border: 1px solid $input_border;
        border-radius: 4px;
        padding: 5px;
        color: $text;
        min-height: 25px;
    }
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus {
        border: 1px solid $focus_border;
    }
    QPushButton {
        background-color: $accent_bg;
        color: $accent_text;
        border: none;
        border-radius: 5px;
        padding: 6px 15px;
        font-weight: bold;
        min-height: 28px;
    }
    QPushButton:hover {
        background-color: $accent_hover;
    }
    QPushButton:pressed {
        background-color: $accent_pressed;
    }
    QPushButton#secondaryBtn {
        background-color: $secondary_bg;
        color: $secondary_text;
        border: 1px solid $secondary_border;
    }
    QPushButton#secondaryBtn:hover {
        background-color: $secondary_hover;
    }
    QTabWidget::pane {
        border: 1px solid $tab_pane_border;
        border-radius: 6px;
        background-color: $tab_pane_bg;
    }
    QTabBar::tab {
        background: $tabbar_bg;
        border: 1px solid $tabbar_border;
        padding: 8px 16px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        color: $tabbar_text;
    }
    QTabBar::tab:selected, QTabBar::tab:hover {
        background: $tab_selected_bg;
        font-weight: bold;
        color: $tab_selected_text;
    }
    QStatusBar {
        background: $statusbar_bg;
        color: $statusbar_text;
    }
""")

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
    connection_checked = pyqtSignal(bool, list)
    
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
        self.setWindowTitle("ShallotT - Traducteur IA Local")
        self.resize(750, 480)
        
        # Load custom Shallot icon
        import os
        icon_path = os.path.join(os.path.dirname(__file__), "shallot.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        theme = self.config.get("ui_theme", "dark")
        self.apply_theme(theme if theme in THEMES else "dark")

        self.init_ui()
        self.apply_font_preferences()
        self.setup_system_tray()
        
        # Connect signals
        self.translation_done.connect(self.on_translation_success)
        self.translation_failed.connect(self.on_translation_error)
        self.trigger_translate_shortcut.connect(self.handle_global_translate_shortcut)
        self.trigger_ocr_shortcut.connect(self.handle_global_ocr_shortcut)
        self.connection_checked.connect(self.on_connection_checked)
        
        # Keep loading models in background
        QTimer.singleShot(100, self.refresh_ollama_models)

    def apply_theme(self, theme_key):
        """Applies one of the THEMES skins (palette + stylesheet) to the application."""
        tokens = THEMES.get(theme_key, THEMES["dark"])

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(tokens["pal_window"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(tokens["pal_windowtext"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(tokens["pal_base"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens["pal_alternatebase"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(tokens["pal_tooltipbase"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(tokens["pal_tooltiptext"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(tokens["pal_text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(tokens["pal_button"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(tokens["pal_buttontext"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(tokens["pal_brighttext"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(tokens["pal_highlight"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(tokens["pal_highlightedtext"]))
        self.setPalette(palette)

        self.setStyleSheet(_STYLESHEET_TEMPLATE.substitute(tokens))

    def apply_font_preferences(self):
        """Applies configured font type, size guidelines, and accessibility adjustments."""
        size = self.config.get("font_size", 13)
        family = self.config.get("font_family", "Segoe UI")
        is_dyslexic = self.config.get("dyslexic_mode", False)
        
        # High contrast/visually impaired/Dyslexic style overriding font selection
        if is_dyslexic:
            # Comic Sans or OpenDyslexic or generic high readability serif/sans-serif
            family = "Comic Sans MS" if sys.platform != "darwin" else "Chalkboard SE"
            size = max(16, size) # Force minimum font size of 16 for ease of access
            
        font = QFont(family, size)
        
        # Apply to text edit fields
        self.src_text_edit.setFont(font)
        self.target_text_edit.setFont(font)
        
        # Accessibility focus high contrast outline indicator if dyslexic mode activated
        if is_dyslexic:
            # Let's adjust text edits slightly for high contrast helper layout
            theme = self.config.get("ui_theme", "dark")
            if theme in ("light", "solarized", "sepia"):
                contrast_css = f"background-color: #ffffff; border: 3px solid #000000; color: #000000; font-family: '{family}'; font-size: {size}px; font-weight: bold; padding: 10px;"
            else:
                contrast_css = f"background-color: #000000; border: 3px solid #ffff00; color: #ffffff; font-family: '{family}'; font-size: {size}px; font-weight: bold; padding: 10px;"
            self.src_text_edit.setStyleSheet(contrast_css)
            self.target_text_edit.setStyleSheet(contrast_css)
        else:
            # Restore standard styles
            self.src_text_edit.setStyleSheet("")
            self.target_text_edit.setStyleSheet("")

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
        
        self.replace_btn = QPushButton("Replace Selection")
        self.replace_btn.clicked.connect(self.replace_active_selection_with_translation)
        self.replace_btn.setToolTip("Remplacer le texte d'origine sélectionné dans l'autre application par ce texte traduit")
        target_bottom.addWidget(self.replace_btn)
        
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
        
        # Interface Theme Preference Row
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Interface Theme (Thème de l'application) :"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEME_LABELS.values()))
        current_key = self.config.get("ui_theme", "dark")
        if current_key not in THEME_LABELS:
            current_key = "dark"
        self.theme_combo.setCurrentText(THEME_LABELS[current_key])
        theme_layout.addWidget(self.theme_combo)
        og_layout.addLayout(theme_layout)
        
        # Character Limit row
        char_limit_layout = QHBoxLayout()
        char_limit_layout.addWidget(QLabel("Max Character Limit (Limite de caractères) :"))
        self.char_limit_spin = QSpinBox()
        self.char_limit_spin.setRange(100, 1000000)
        self.char_limit_spin.setSingleStep(1000)
        self.char_limit_spin.setValue(self.config.get("max_characters", 10000))
        char_limit_layout.addWidget(self.char_limit_spin)
        og_layout.addLayout(char_limit_layout)
        
        # Font Configuration group
        font_group = QGroupBox("Reading & Font Preferences (Options de lecture)")
        fg_layout = QVBoxLayout(font_group)
        
        f_row = QHBoxLayout()
        f_row.addWidget(QLabel("Font Family (Police) :"))
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems([
            "Segoe UI", "Arial", "Calibri", "Comic Sans MS", "Courier New", "Verdana", "Times New Roman"
        ])
        self.font_family_combo.setCurrentText(self.config.get("font_family", "Segoe UI"))
        f_row.addWidget(self.font_family_combo)
        
        f_row.addWidget(QLabel("Font Size (Taille) :"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setValue(self.config.get("font_size", 13))
        f_row.addWidget(self.font_size_spin)
        fg_layout.addLayout(f_row)
        
        # Visually Impaired / High Contrast / Dyslexic checkbox
        accessibility_row = QHBoxLayout()
        self.dyslexic_cb = QCheckBox("High Contrast / Visually Impaired Large Font (Mode Malvoyant - Facilité de lecture)")
        self.dyslexic_cb.setDescription = "Forces a thick, highly-legible 16pt font with high-contrast outlines to read easily."
        self.dyslexic_cb.setChecked(self.config.get("dyslexic_mode", False))
        accessibility_row.addWidget(self.dyslexic_cb)
        fg_layout.addLayout(accessibility_row)
        
        settings_layout.addWidget(ollama_group)
        settings_layout.addWidget(font_group)
        
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
        
        # OCR Engine selection
        ocr_eng_layout = QHBoxLayout()
        ocr_eng_layout.addWidget(QLabel("OCR Engine (Moteur de reconnaissance) :"))
        self.ocr_engine_combo = QComboBox()
        self.ocr_engine_combo.addItems(["Tesseract OCR (Interne)", "PowerToys Text Extractor (Windows)"])
        current_eng = "PowerToys Text Extractor (Windows)" if self.config.get("ocr_engine", "tesseract") == "powertoys" else "Tesseract OCR (Interne)"
        self.ocr_engine_combo.setCurrentText(current_eng)
        ocr_eng_layout.addWidget(self.ocr_engine_combo)
        sg_layout.addLayout(ocr_eng_layout)
        
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
            
        max_chars = self.config.get("max_characters", 10000)
        self.pending_truncation_note = ""
        if len(text) > max_chars:
            text = text[:max_chars]
            self.pending_truncation_note = f"\n\n--- [Note: Traduction limitée à {max_chars} caractères pour optimiser la vitesse de traitement] ---"
            self.statusBar().showMessage(f"Text truncated to {max_chars} characters to maintain high performance.", 5000)
            
        src_lang = self.src_lang_box.currentText()
        target_lang = self.target_lang_box.currentText()
        
        # Smart target language auto-swap if source text matches target language
        # ONLY swap them if the source language box is set to "Auto Detection"
        # and the user hasn't explicitly set the same language. This prevents the combobox snapping bugs.
        if src_lang == "Auto Detection":
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
        note = getattr(self, "pending_truncation_note", "")
        self.target_text_edit.setPlainText(text + note)
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
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.statusBar().showMessage("Translation copied to clipboard!", 2000)

    def replace_active_selection_with_translation(self):
        """
        Copies the translated text, simulates releasing all modifier keys,
        and simulates standard pasting command (Ctrl+V) into the previously active application
        to instantly swap the original selection with the new translation!
        """
        translated_text = self.target_text_edit.toPlainText()
        if not translated_text:
            return
            
        try:
            # 1. Store translated text in system clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(translated_text)
            
            # Hide or minimize the translator window first to restore focus to the target app!
            self.hide() # Hide window to automatically yield OS focus to the previously active text area
            
            # Allow target application to regain keyboard focus
            QTimer.singleShot(150, self._dispatch_paste_sequence)
        except Exception as e:
            self.statusBar().showMessage(f"Replacement failed: {str(e)}", 3000)

    def _dispatch_paste_sequence(self):
        try:
            from pynput.keyboard import Key, Controller
            kb = Controller()
            
            # Release any physical modifier keys to avoid contaminations
            for modifier in [Key.ctrl, Key.ctrl_l, Key.ctrl_r, Key.shift, Key.shift_l, Key.shift_r, Key.alt, Key.alt_l, Key.alt_r, Key.cmd, Key.cmd_l, Key.cmd_r]:
                try:
                    kb.release(modifier)
                except Exception:
                    pass
            for i in range(1, 13):
                try:
                    f_key = getattr(Key, f'f{i}', None)
                    if f_key:
                        kb.release(f_key)
                except Exception:
                    pass
            
            # Simulate Paste action: Ctrl+V (works on all OS including Linux/Windows)
            kb.press(Key.ctrl)
            kb.press('v')
            kb.release('v')
            kb.release(Key.ctrl)
            
            # Restore window visibility in tray mode
            self.statusBar().showMessage("Selection replaced successfully!", 3000)
        except Exception as e:
            print(f"Error executing paste replacement sequence: {e}")

    def refresh_ollama_models(self):
        """Fetch available models from the Ollama server."""
        self.check_conn_btn.setText("Connecting...")
        
        # Perform check in a safe non-blocking way using QThread/threading + PyQt Signals
        def fetch_task():
            # Update translator settings first
            url = self.url_input.text().strip()
            key = self.key_input.text().strip()
            self.translator.base_url = url.rstrip('/')
            self.translator.api_key = key
            
            connected, models = self.translator.check_connection()
            self.connection_checked.emit(connected, models)
            
        threading.Thread(target=fetch_task, daemon=True).start()

    def on_connection_checked(self, connected, models):
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
        self.config["ocr_engine"] = "powertoys" if "powertoys" in self.ocr_engine_combo.currentText().lower() else "tesseract"
        
        # Save max characters limit
        self.config["max_characters"] = self.char_limit_spin.value()
        
        # Save Font Preferences
        self.config["font_family"] = self.font_family_combo.currentText()
        self.config["font_size"] = self.font_size_spin.value()
        self.config["dyslexic_mode"] = self.dyslexic_cb.isChecked()
        self.apply_font_preferences()
        
        # Save app Theme selection
        selected_label = self.theme_combo.currentText()
        theme_sel = next((key for key, label in THEME_LABELS.items() if label == selected_label), "dark")
        self.config["ui_theme"] = theme_sel
        self.apply_theme(theme_sel)

        save_config(self.config)
        
        # Re-initialize translator
        self.translator = OllamaTranslator(base_url=url, model=model, api_key=key)
        
        QMessageBox.information(self, "Settings Saved", f"Configuration updated and saved to:\n{CONFIG_PATH}")
        self.statusBar().showMessage(f"Active configuration: {model}@{url}", 4000)

    # --- INCOMING EXTERNAL TRIGGERS (from shortcuts) ---

    def handle_global_translate_shortcut(self):
        """
        Reads selected text from clipboard (simulating a copy action if needed),
        opens window and translates immediately!
        """
        try:
            from pynput.keyboard import Key, Controller
            kb = Controller()
            # Release any physically held modifiers/keys of our shortcut to prevent conflicts
            for modifier in [Key.ctrl, Key.ctrl_l, Key.ctrl_r, Key.shift, Key.shift_l, Key.shift_r, Key.alt, Key.alt_l, Key.alt_r, Key.cmd, Key.cmd_l, Key.cmd_r]:
                try:
                    kb.release(modifier)
                except Exception:
                    pass
            for i in range(1, 13):
                try:
                    f_key = getattr(Key, f'f{i}', None)
                    if f_key:
                        kb.release(f_key)
                except Exception:
                    pass
            
            # Now safely perform the copy simulation Ctrl+C
            kb.press(Key.ctrl)
            kb.press('c')
            kb.release('c')
            kb.release(Key.ctrl)
        except Exception as e:
            print(f"Error simulating copy keypress check: {e}")
            
        # Sleep slightly longer to let the clipboard copy event write and complete safely
        QTimer.singleShot(150, self._process_clipboard_translation)

    def _process_clipboard_translation(self):
        try:
            clipboard = QApplication.clipboard()
            copied_text = clipboard.text()
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
        run_ocr_capture(on_ocr_text_ready, self.config.get("ocr_engine", "tesseract"))

import sys
import os
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
from PyQt6.QtGui import QFont, QIcon, QAction, QColor, QPalette, QKeySequence, QPixmap, QPainter

from src.config import load_config, save_config, CONFIG_PATH
from src.ollama_client import OllamaTranslator
from src.translation_cache import lookup as cache_lookup, store as cache_store, stats as cache_stats, clear as cache_clear
from src.glossary import load_glossary, save_glossary, inject_glossary_into_prompt
from src.tts import speak as tts_speak, stop as tts_stop
from src.clipboard_monitor import ClipboardWorker, DesktopTranslationPopup
from src.doc_import import extract_text as doc_extract_text

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
        "font_family": "'Segoe UI', Arial, sans-serif",
        "border_radius_small": "6px",
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
        "font_family": "'Segoe UI', Arial, sans-serif",
        "border_radius_small": "6px",
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
        "font_family": "'Segoe UI', Arial, sans-serif",
        "border_radius_small": "6px",
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
        "font_family": "'Segoe UI', Arial, sans-serif",
        "border_radius_small": "6px",
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
        "font_family": "'Segoe UI', Arial, sans-serif",
        "border_radius_small": "6px",
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
        "font_family": "'Segoe UI', Arial, sans-serif",
        "border_radius_small": "6px",
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
    # ── New creative themes ──
    "hacker": {
        "pal_window": "#000000", "pal_windowtext": "#00ff41", "pal_base": "#0a0f0a",
        "pal_alternatebase": "#000000", "pal_tooltipbase": "#00ff41", "pal_tooltiptext": "#000000",
        "pal_text": "#00ff41", "pal_button": "#0d1a0d", "pal_buttontext": "#00ff41",
        "pal_brighttext": "#00ff41", "pal_highlight": "#00ff41", "pal_highlightedtext": "#000000",
        "font_family": "'Courier New', 'Consolas', 'Fira Code', monospace",
        "border_radius_small": "0px",
        "background_image": "url(src/backgrounds/scanlines.svg)",
        "window_bg": "#000000", "text": "#00ff41",
        "textedit_bg": "#0a0f0a", "textedit_border": "#00ff41", "focus_border": "#39ff14",
        "input_bg": "#0a0f0a", "input_border": "#00cc33",
        "combo_view_bg": "#0a0f0a", "combo_view_text": "#00ff41",
        "combo_view_sel_bg": "#003300", "combo_view_sel_text": "#00ff41",
        "groupbox_border": "#00ff41",
        "accent_bg": "#00ff41", "accent_text": "#000000", "accent_hover": "#39ff14", "accent_pressed": "#00cc33",
        "secondary_bg": "#0d1a0d", "secondary_text": "#00ff41", "secondary_border": "#00cc33", "secondary_hover": "#153015",
        "tab_pane_bg": "#0a0f0a", "tab_pane_border": "#00ff41",
        "tabbar_bg": "#000000", "tabbar_border": "#00cc33", "tabbar_text": "#00ff41",
        "tab_selected_bg": "#0a0f0a", "tab_selected_text": "#39ff14",
        "statusbar_bg": "#000000", "statusbar_text": "#00cc33",
    },
    "dragon": {
        "pal_window": "#1a0f0a", "pal_windowtext": "#f5c6a0", "pal_base": "#241410",
        "pal_alternatebase": "#1a0f0a", "pal_tooltipbase": "#f5c6a0", "pal_tooltiptext": "#1a0f0a",
        "pal_text": "#e8d5c4", "pal_button": "#3d1f0f", "pal_buttontext": "#ffb380",
        "pal_brighttext": "#ff6b35", "pal_highlight": "#ff8c42", "pal_highlightedtext": "#1a0f0a",
        "font_family": "'Segoe UI', 'Georgia', serif",
        "border_radius_small": "4px",
        "background_image": "url(src/backgrounds/dragonscales.svg)",
        "window_bg": "#1a0f0a", "text": "#e8d5c4",
        "textedit_bg": "#241410", "textedit_border": "#8b4513", "focus_border": "#ff8c42",
        "input_bg": "#241410", "input_border": "#6b3418",
        "combo_view_bg": "#241410", "combo_view_text": "#e8d5c4",
        "combo_view_sel_bg": "#3d1f0f", "combo_view_sel_text": "#ffb380",
        "groupbox_border": "#8b4513",
        "accent_bg": "#ff6b35", "accent_text": "#1a0f0a", "accent_hover": "#ff8c42", "accent_pressed": "#e55a2b",
        "secondary_bg": "#3d1f0f", "secondary_text": "#e8d5c4", "secondary_border": "#6b3418", "secondary_hover": "#4d2815",
        "tab_pane_bg": "#241410", "tab_pane_border": "#6b3418",
        "tabbar_bg": "#1a0f0a", "tabbar_border": "#6b3418", "tabbar_text": "#d4b896",
        "tab_selected_bg": "#241410", "tab_selected_text": "#ffb380",
        "statusbar_bg": "#0d0805", "statusbar_text": "#b8906a",
    },
    "classic_mac": {
        "pal_window": "#ddddcc", "pal_windowtext": "#1a1a1a", "pal_base": "#ffffff",
        "pal_alternatebase": "#e0e0d5", "pal_tooltipbase": "#1a1a1a", "pal_tooltiptext": "#ffffff",
        "pal_text": "#1a1a1a", "pal_button": "#c8c8b8", "pal_buttontext": "#1a1a1a",
        "pal_brighttext": "#0000aa", "pal_highlight": "#0000aa", "pal_highlightedtext": "#ffffff",
        "font_family": "'Chicago', 'Charcoal', 'MS Sans Serif', 'Segoe UI', sans-serif",
        "border_radius_small": "2px",
        "window_bg": "#ddddcc", "text": "#1a1a1a",
        "textedit_bg": "#ffffff", "textedit_border": "#999999", "focus_border": "#0000aa",
        "input_bg": "#ffffff", "input_border": "#999999",
        "combo_view_bg": "#ffffff", "combo_view_text": "#1a1a1a",
        "combo_view_sel_bg": "#0000aa", "combo_view_sel_text": "#ffffff",
        "groupbox_border": "#999999",
        "accent_bg": "#0000aa", "accent_text": "#ffffff", "accent_hover": "#0000ee", "accent_pressed": "#000088",
        "secondary_bg": "#c8c8b8", "secondary_text": "#1a1a1a", "secondary_border": "#999999", "secondary_hover": "#b8b8aa",
        "tab_pane_bg": "#ffffff", "tab_pane_border": "#999999",
        "tabbar_bg": "#ddddcc", "tabbar_border": "#999999", "tabbar_text": "#1a1a1a",
        "tab_selected_bg": "#ffffff", "tab_selected_text": "#1a1a1a",
        "statusbar_bg": "#ddddcc", "statusbar_text": "#555555",
    },
    "retro_amber": {
        "pal_window": "#1a1800", "pal_windowtext": "#ffb000", "pal_base": "#0f0e00",
        "pal_alternatebase": "#1a1800", "pal_tooltipbase": "#ffb000", "pal_tooltiptext": "#0f0e00",
        "pal_text": "#ffb000", "pal_button": "#2a2500", "pal_buttontext": "#ffb000",
        "pal_brighttext": "#ffcc00", "pal_highlight": "#ffb000", "pal_highlightedtext": "#0f0e00",
        "font_family": "'Courier New', 'Consolas', 'IBM Plex Mono', monospace",
        "border_radius_small": "0px",
        "background_image": "url(src/backgrounds/crt_mask.svg)",
        "window_bg": "#0f0e00", "text": "#ffb000",
        "textedit_bg": "#0a0900", "textedit_border": "#ffb000", "focus_border": "#ffcc00",
        "input_bg": "#0a0900", "input_border": "#cc8800",
        "combo_view_bg": "#0a0900", "combo_view_text": "#ffb000",
        "combo_view_sel_bg": "#332800", "combo_view_sel_text": "#ffcc00",
        "groupbox_border": "#cc8800",
        "accent_bg": "#ffb000", "accent_text": "#0f0e00", "accent_hover": "#ffcc00", "accent_pressed": "#cc8800",
        "secondary_bg": "#2a2500", "secondary_text": "#ffb000", "secondary_border": "#cc8800", "secondary_hover": "#3d3500",
        "tab_pane_bg": "#0a0900", "tab_pane_border": "#cc8800",
        "tabbar_bg": "#0f0e00", "tabbar_border": "#cc8800", "tabbar_text": "#ffb000",
        "tab_selected_bg": "#0a0900", "tab_selected_text": "#ffcc00",
        "statusbar_bg": "#050400", "statusbar_text": "#cc8800",
    },
    "retro_green": {
        "pal_window": "#001a00", "pal_windowtext": "#33ff33", "pal_base": "#000f00",
        "pal_alternatebase": "#001a00", "pal_tooltipbase": "#33ff33", "pal_tooltiptext": "#000f00",
        "pal_text": "#33ff33", "pal_button": "#002200", "pal_buttontext": "#33ff33",
        "pal_brighttext": "#66ff66", "pal_highlight": "#33ff33", "pal_highlightedtext": "#000f00",
        "font_family": "'Courier New', 'Consolas', 'IBM Plex Mono', monospace",
        "border_radius_small": "0px",
        "background_image": "url(src/backgrounds/scanlines.svg)",
        "window_bg": "#000f00", "text": "#33ff33",
        "textedit_bg": "#000800", "textedit_border": "#33ff33", "focus_border": "#66ff66",
        "input_bg": "#000800", "input_border": "#229922",
        "combo_view_bg": "#000800", "combo_view_text": "#33ff33",
        "combo_view_sel_bg": "#003300", "combo_view_sel_text": "#66ff66",
        "groupbox_border": "#229922",
        "accent_bg": "#33ff33", "accent_text": "#000f00", "accent_hover": "#66ff66", "accent_pressed": "#229922",
        "secondary_bg": "#002200", "secondary_text": "#33ff33", "secondary_border": "#229922", "secondary_hover": "#003300",
        "tab_pane_bg": "#000800", "tab_pane_border": "#229922",
        "tabbar_bg": "#000f00", "tabbar_border": "#229922", "tabbar_text": "#33ff33",
        "tab_selected_bg": "#000800", "tab_selected_text": "#66ff66",
        "statusbar_bg": "#000500", "statusbar_text": "#229922",
    },
    "dracula": {
        "pal_window": "#282a36", "pal_windowtext": "#f8f8f2", "pal_base": "#1e1f29",
        "pal_alternatebase": "#282a36", "pal_tooltipbase": "#f8f8f2", "pal_tooltiptext": "#282a36",
        "pal_text": "#f8f8f2", "pal_button": "#44475a", "pal_buttontext": "#f8f8f2",
        "pal_brighttext": "#ff79c6", "pal_highlight": "#bd93f9", "pal_highlightedtext": "#282a36",
        "font_family": "'Segoe UI', 'Fira Code', 'JetBrains Mono', sans-serif",
        "border_radius_small": "6px",
        "window_bg": "#282a36", "text": "#f8f8f2",
        "textedit_bg": "#1e1f29", "textedit_border": "#44475a", "focus_border": "#bd93f9",
        "input_bg": "#1e1f29", "input_border": "#44475a",
        "combo_view_bg": "#1e1f29", "combo_view_text": "#f8f8f2",
        "combo_view_sel_bg": "#44475a", "combo_view_sel_text": "#ff79c6",
        "groupbox_border": "#44475a",
        "accent_bg": "#bd93f9", "accent_text": "#282a36", "accent_hover": "#ff79c6", "accent_pressed": "#9580c4",
        "secondary_bg": "#44475a", "secondary_text": "#f8f8f2", "secondary_border": "#44475a", "secondary_hover": "#5a5d7a",
        "tab_pane_bg": "#1e1f29", "tab_pane_border": "#44475a",
        "tabbar_bg": "#21222c", "tabbar_border": "#44475a", "tabbar_text": "#d6d4ce",
        "tab_selected_bg": "#1e1f29", "tab_selected_text": "#f8f8f2",
        "statusbar_bg": "#191a21", "statusbar_text": "#6272a4",
    },
    "synthwave": {
        "pal_window": "#1a0033", "pal_windowtext": "#f0e6ff", "pal_base": "#240047",
        "pal_alternatebase": "#1a0033", "pal_tooltipbase": "#ff66ff", "pal_tooltiptext": "#1a0033",
        "pal_text": "#e0d0ff", "pal_button": "#330066", "pal_buttontext": "#f0e6ff",
        "pal_brighttext": "#ff66ff", "pal_highlight": "#00ffff", "pal_highlightedtext": "#1a0033",
        "font_family": "'Segoe UI', 'Orbitron', 'Rajdhani', sans-serif",
        "border_radius_small": "6px",
        "background_image": "url(src/backgrounds/neongrid.svg)",
        "window_bg": "#1a0033", "text": "#e0d0ff",
        "textedit_bg": "#240047", "textedit_border": "#9933ff", "focus_border": "#ff66ff",
        "input_bg": "#240047", "input_border": "#661199",
        "combo_view_bg": "#240047", "combo_view_text": "#e0d0ff",
        "combo_view_sel_bg": "#330066", "combo_view_sel_text": "#ff66ff",
        "groupbox_border": "#9933ff",
        "accent_bg": "#ff66ff", "accent_text": "#1a0033", "accent_hover": "#ff99ff", "accent_pressed": "#cc33cc",
        "secondary_bg": "#330066", "secondary_text": "#e0d0ff", "secondary_border": "#661199", "secondary_hover": "#440088",
        "tab_pane_bg": "#240047", "tab_pane_border": "#661199",
        "tabbar_bg": "#1a0033", "tabbar_border": "#661199", "tabbar_text": "#d0b0ff",
        "tab_selected_bg": "#240047", "tab_selected_text": "#ff66ff",
        "statusbar_bg": "#0f0022", "statusbar_text": "#9944dd",
    },
    "monokai": {
        "pal_window": "#272822", "pal_windowtext": "#f8f8f2", "pal_base": "#1e1f1c",
        "pal_alternatebase": "#272822", "pal_tooltipbase": "#f8f8f2", "pal_tooltiptext": "#272822",
        "pal_text": "#cfd0c2", "pal_button": "#3e3d32", "pal_buttontext": "#f8f8f2",
        "pal_brighttext": "#a6e22e", "pal_highlight": "#f92672", "pal_highlightedtext": "#272822",
        "font_family": "'Segoe UI', 'Fira Code', 'Cascadia Code', sans-serif",
        "border_radius_small": "4px",
        "window_bg": "#272822", "text": "#cfd0c2",
        "textedit_bg": "#1e1f1c", "textedit_border": "#49483e", "focus_border": "#f92672",
        "input_bg": "#1e1f1c", "input_border": "#49483e",
        "combo_view_bg": "#1e1f1c", "combo_view_text": "#cfd0c2",
        "combo_view_sel_bg": "#49483e", "combo_view_sel_text": "#e6db74",
        "groupbox_border": "#49483e",
        "accent_bg": "#a6e22e", "accent_text": "#272822", "accent_hover": "#b8f340", "accent_pressed": "#8cc92a",
        "secondary_bg": "#3e3d32", "secondary_text": "#f8f8f2", "secondary_border": "#49483e", "secondary_hover": "#4e4d42",
        "tab_pane_bg": "#1e1f1c", "tab_pane_border": "#49483e",
        "tabbar_bg": "#23241f", "tabbar_border": "#49483e", "tabbar_text": "#cfd0c2",
        "tab_selected_bg": "#1e1f1c", "tab_selected_text": "#e6db74",
        "statusbar_bg": "#1a1b18", "statusbar_text": "#75715e",
    },
    "tokyo_night": {
        "pal_window": "#1a1b26", "pal_windowtext": "#c0caf5", "pal_base": "#24283b",
        "pal_alternatebase": "#1a1b26", "pal_tooltipbase": "#c0caf5", "pal_tooltiptext": "#1a1b26",
        "pal_text": "#a9b1d6", "pal_button": "#2f3349", "pal_buttontext": "#c0caf5",
        "pal_brighttext": "#7aa2f7", "pal_highlight": "#7aa2f7", "pal_highlightedtext": "#1a1b26",
        "font_family": "'Segoe UI', 'JetBrains Mono', 'Inter', sans-serif",
        "border_radius_small": "6px",
        "window_bg": "#1a1b26", "text": "#a9b1d6",
        "textedit_bg": "#24283b", "textedit_border": "#414868", "focus_border": "#7aa2f7",
        "input_bg": "#24283b", "input_border": "#414868",
        "combo_view_bg": "#24283b", "combo_view_text": "#a9b1d6",
        "combo_view_sel_bg": "#414868", "combo_view_sel_text": "#7dcfff",
        "groupbox_border": "#414868",
        "accent_bg": "#7aa2f7", "accent_text": "#1a1b26", "accent_hover": "#89b4fa", "accent_pressed": "#6a94e6",
        "secondary_bg": "#2f3349", "secondary_text": "#c0caf5", "secondary_border": "#414868", "secondary_hover": "#3b4268",
        "tab_pane_bg": "#24283b", "tab_pane_border": "#414868",
        "tabbar_bg": "#1f2335", "tabbar_border": "#414868", "tabbar_text": "#a9b1d6",
        "tab_selected_bg": "#24283b", "tab_selected_text": "#c0caf5",
        "statusbar_bg": "#16161e", "statusbar_text": "#565f89",
    },
    "nfs_tokyo": {
        "pal_window": "#0f0f15", "pal_windowtext": "#e0e8f0", "pal_base": "#1a1a24",
        "pal_alternatebase": "#0f0f15", "pal_tooltipbase": "#e0e8f0", "pal_tooltiptext": "#0f0f15",
        "pal_text": "#c8d0da", "pal_button": "#222230", "pal_buttontext": "#e0e8f0",
        "pal_brighttext": "#00e5ff", "pal_highlight": "#ff006e", "pal_highlightedtext": "#ffffff",
        "font_family": "'Segoe UI', 'Orbitron', 'Rajdhani', 'Racing Sans One', sans-serif",
        "border_radius_small": "4px",
        "background_image": "url(src/backgrounds/carbon.svg)",
        "window_bg": "#0f0f15", "text": "#c8d0da",
        "textedit_bg": "#1a1a24", "textedit_border": "#333350", "focus_border": "#00e5ff",
        "input_bg": "#1a1a24", "input_border": "#333350",
        "combo_view_bg": "#1a1a24", "combo_view_text": "#c8d0da",
        "combo_view_sel_bg": "#2a2a40", "combo_view_sel_text": "#00e5ff",
        "groupbox_border": "#333350",
        "accent_bg": "#ff006e", "accent_text": "#ffffff", "accent_hover": "#ff3388", "accent_pressed": "#cc0058",
        "secondary_bg": "#222230", "secondary_text": "#c8d0da", "secondary_border": "#333350", "secondary_hover": "#2e2e40",
        "tab_pane_bg": "#1a1a24", "tab_pane_border": "#333350",
        "tabbar_bg": "#0f0f15", "tabbar_border": "#333350", "tabbar_text": "#8899aa",
        "tab_selected_bg": "#1a1a24", "tab_selected_text": "#00e5ff",
        "statusbar_bg": "#08080f", "statusbar_text": "#667788",
    },
}

# Display labels shown in the theme picker, in display order.
THEME_LABELS = {
    "dark": "🌑 Dark (Sombre moderne)",
    "light": "☀️ Light (Clair moderne)",
    "nord": "❄️ Nord (Bleu glacial)",
    "solarized": "📖 Solarized Light (Lecture)",
    "sepia": "📜 Sépia (Confort visuel)",
    "contrast": "♿ Contraste élevé (Accessibilité)",
    "hacker": "💀 Hacker (Terminal vert)",
    "dragon": "🐉 Dragon (Feu & écailles)",
    "classic_mac": "🖥️ Classic Mac (System 6/7)",
    "retro_amber": "📺 Retro Amber (CRT ambre)",
    "retro_green": "🟢 Retro Green (IBM 5150)",
    "dracula": "🧛 Dracula (Pourpre & rose)",
    "synthwave": "🌆 Synthwave (Néon rétro)",
    "monokai": "🎨 Monokai (Dev chaleureux)",
    "tokyo_night": "🌃 Tokyo Night (Bleu nuit)",
    "nfs_tokyo": "🏎️ NFS Tokyo Drift (Pimp My Ride)",
}

_STYLESHEET_TEMPLATE = Template("""
    QMainWindow {
        background-color: $window_bg;
        background-image: $background_image;
        background-position: center;
        background-repeat: repeat;
    }
    QWidget {
        color: $text;
        font-family: $font_family;
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
        border-radius: $border_radius_small;
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
    """Worker thread to run translation without freezing the Qt UI.
    Checks cache first, injects glossary, and caches results."""

    def __init__(self, translator, text, src_lang, target_lang, callback,
                 lambda_err, glossary_entries=None, model="gemma:latest"):
        super().__init__()
        self.translator = translator
        self.text = text
        self.src_lang = src_lang
        self.target_lang = target_lang
        self.callback = callback
        self.lambda_err = lambda_err
        self.glossary_entries = glossary_entries or []
        self.model = model

    def run(self):
        try:
            # 1. Check translation cache first
            cached = cache_lookup(self.text, self.src_lang,
                                   self.target_lang, self.model)
            if cached:
                self.callback(cached)
                return

            # 2. Inject glossary into the translator's prompt
            if self.glossary_entries:
                base_prompt = getattr(self.translator, 'system_prompt', None)
                if base_prompt:
                    enhanced = inject_glossary_into_prompt(
                        base_prompt, self.glossary_entries
                    )
                    self.translator.system_prompt = enhanced

            # 3. Translate
            translation = self.translator.translate(
                self.text, self.src_lang, self.target_lang
            )

            # 4. Cache the result
            cache_store(self.text, self.src_lang, self.target_lang,
                        self.model, translation)

            self.callback(translation)
        except Exception as e:
            self.lambda_err(str(e))


class WallpaperWidget(QWidget):
    """Central widget that paints a background image.
    Supports tile, center, stretch, and fit modes.
    Works on all platforms including Wayland."""

    MODE_TILE = "tile"
    MODE_CENTER = "center"
    MODE_STRETCH = "stretch"
    MODE_FIT = "fit"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._wallpaper_pixmap: QPixmap | None = None
        self._wallpaper_path: str = ""
        self._wallpaper_mode: str = self.MODE_TILE
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_wallpaper(self, path: str, mode: str = MODE_TILE):
        """Set a background image and display mode. Pass empty path to clear."""
        self._wallpaper_path = path
        self._wallpaper_mode = mode
        if path and os.path.exists(path):
            self._wallpaper_pixmap = QPixmap(path)
        else:
            self._wallpaper_pixmap = None
        self.update()

    def paintEvent(self, event):
        px = self._wallpaper_pixmap
        if px and not px.isNull():
            painter = QPainter(self)
            w, h = self.width(), self.height()
            pw, ph = px.width(), px.height()
            if pw > 0 and ph > 0:
                mode = self._wallpaper_mode
                if mode == self.MODE_TILE:
                    for x in range(0, w, pw):
                        for y in range(0, h, ph):
                            painter.drawPixmap(x, y, px)
                elif mode == self.MODE_CENTER:
                    x = (w - pw) // 2
                    y = (h - ph) // 2
                    painter.drawPixmap(x, y, px)
                elif mode == self.MODE_STRETCH:
                    painter.drawPixmap(0, 0, w, h, px)
                elif mode == self.MODE_FIT:
                    scale = min(w / pw, h / ph)
                    nw, nh = int(pw * scale), int(ph * scale)
                    x, y = (w - nw) // 2, (h - nh) // 2
                    painter.drawPixmap(x, y, nw, nh, px)
            painter.end()
        super().paintEvent(event)


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
        
        # Load custom Shallot icon (app + window + tray)
        import os
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "shallot.png"))
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            QApplication.instance().setWindowIcon(app_icon)
            self.setWindowIcon(app_icon)
            self._shallot_icon = app_icon  # reuse for tray
            
        theme = self.config.get("ui_theme", "dark")
        self.apply_theme(theme if theme in THEMES else "dark")

        # Glossary (loaded once, editable in Settings)
        self.glossary_entries = load_glossary()

        # Desktop translation popup (lazy, shown by clipboard monitor or shortcut)
        self._desktop_popup = None

        # Clipboard monitor state
        self._clipboard_worker = None
        self._clipboard_monitoring = False

        # Audio capture state
        self._audio_capture = None          # AudioCapture instance (lazy)
        self._audio_timer = QTimer()        # Polls for new audio chunks
        self._audio_timer.setInterval(1500) # Transcribe every 1.5 s
        self._audio_timer.timeout.connect(self._audio_poll_chunk)
        self._audio_level_timer = QTimer()  # Refreshes level bar
        self._audio_level_timer.setInterval(80)
        self._audio_level_timer.timeout.connect(self._audio_refresh_level)

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
        tokens = THEMES.get(theme_key, THEMES["dark"]).copy()

        # Default background: solid colour. Themes can override with an image URL.
        if "background_image" not in tokens:
            tokens["background_image"] = "none"
        else:
            # Resolve relative paths (e.g. "url(src/backgrounds/...)") to absolute
            bg = tokens["background_image"]
            if bg.startswith("url(") and not bg.startswith("url(/"):
                inner = bg[4:-1]  # strip "url(" and ")"
                abs_path = os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "..", inner
                ))
                tokens["background_image"] = f"url({abs_path})"

        # User wallpaper override — painted directly by WallpaperWidget
        # (works on Wayland where QSS background-image is broken)
        user_bg = self.config.get("custom_wallpaper", "")
        if user_bg and os.path.exists(user_bg):
            wp_mode = self.config.get("wallpaper_mode", "tile")
            cw = self.centralWidget()
            if isinstance(cw, WallpaperWidget):
                cw.set_wallpaper(user_bg, wp_mode)
            tokens["background_image"] = f"url({user_bg})"  # QSS fallback
            alpha = self.config.get("wallpaper_transparency", 85) / 100.0
            def _hex_to_rgba(hex_color, a):
                h = hex_color.lstrip('#')
                r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                return f"rgba({r}, {g}, {b}, {a})"
            for key in ("textedit_bg", "input_bg", "combo_view_bg",
                         "tab_pane_bg", "tabbar_bg", "tab_selected_bg"):
                if key in tokens and not tokens[key].startswith("rgba"):
                    tokens[key] = _hex_to_rgba(tokens[key], alpha)
        else:
            cw = self.centralWidget()
            if isinstance(cw, WallpaperWidget):
                cw.set_wallpaper("")  # clear wallpaper, show solid colour

        # Font colour override
        fc = self.config.get("font_color_override", "")
        if fc:
            tokens["text"] = fc
            tokens["pal_text"] = fc
            tokens["pal_windowtext"] = fc
            tokens["pal_buttontext"] = fc

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

        # ── Subtle theme decorations ──
        # Each theme gets a small emoji in the window title.
        # Only "dragon" gets the overlay widget decorations.
        _THEME_DECOR = {
            "dark":        "🌑",   "light":     "☀️",
            "nord":        "❄️",   "solarized": "📖",
            "sepia":       "📜",   "contrast":  "♿",
            "hacker":      "💀",   "dragon":    "🐲",
            "classic_mac": "🖥️",   "retro_amber":"📺",
            "retro_green": "🟢",   "dracula":   "🧛",
            "synthwave":   "🌆",   "monokai":   "🎨",
            "tokyo_night": "🌃",
            "nfs_tokyo":   "🏎️",
        }
        emoji = _THEME_DECOR.get(theme_key, "")
        self.setWindowTitle(f"{emoji} ShallotT - Traducteur IA Local {emoji}".strip())

        # Show/hide theme overlay widgets (dragon & NFS) — Windows/macOS only
        if getattr(self, '_overlays_supported', False):
            if theme_key == "dragon" and self.dragon_head_label:
                self.dragon_head_label.show()
                self.dragon_tail_label.show()
            elif self.dragon_head_label:
                self.dragon_head_label.hide()
                self.dragon_tail_label.hide()
            if theme_key == "nfs_tokyo" and self.nfs_car_label:
                self.nfs_car_label.show()
                self.nfs_smoke_label.show()
                self.nfs_nos_label.show()
            elif self.nfs_car_label:
                self.nfs_car_label.hide()
                self.nfs_smoke_label.hide()
                self.nfs_nos_label.hide()
        self._position_theme_overlays()

        # Update status bar theme indicator
        if hasattr(self, 'theme_indicator'):
            self.theme_indicator.setText(emoji) if emoji else self.theme_indicator.setText("")

    def _position_theme_overlays(self):
        """Reposition all theme overlay widgets (dragon, NFS, etc.) after resize.
        Positions them at the extreme corners INSIDE the central widget so they
        are always visible (Qt clips children to the parent widget bounds).
        """
        cw = self.centralWidget()
        if not cw:
            return
        w = cw.width()
        h = cw.height()

        # Dragon: head top-right (72x72), tail bottom-left (72x72)
        if self.dragon_head_label and self.dragon_head_label.isVisible():
            self.dragon_head_label.move(w - 72, 0)
            self.dragon_head_label.raise_()
            self.dragon_tail_label.move(0, h - 72)
            self.dragon_tail_label.raise_()

        # NFS: car bottom-right (80x80), smoke bottom-left (60x60), NOS top-right (56x56)
        if self.nfs_car_label and self.nfs_car_label.isVisible():
            self.nfs_car_label.move(w - 80, h - 80)
            self.nfs_car_label.raise_()
            self.nfs_smoke_label.move(0, h - 60)
            self.nfs_smoke_label.raise_()
            self.nfs_nos_label.move(w - 56, 0)
            self.nfs_nos_label.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_theme_overlays()

    def apply_font_preferences(self):
        """Applies configured font type, size guidelines, and accessibility adjustments.
        When no custom font is saved, the active theme's font is used via QSS."""
        size = self.config.get("font_size", 13)
        family = self.config.get("font_family", "")
        is_dyslexic = self.config.get("dyslexic_mode", False)

        # Resolve the font family: user preference → theme default → system fallback
        if is_dyslexic:
            family = "Comic Sans MS" if sys.platform != "darwin" else "Chalkboard SE"
            size = max(16, size)
        elif not family:
            # No user preference — inherit from the current theme's QSS
            theme_key = self.config.get("ui_theme", "dark")
            tokens = THEMES.get(theme_key, THEMES["dark"])
            family = tokens.get("font_family", "'Segoe UI', Arial, sans-serif")
            # Strip QSS quotes and take the first family name for QFont
            family = family.split(",")[0].strip().strip("'\"")

        font = QFont(family, size)
        self.src_text_edit.setFont(font)
        self.target_text_edit.setFont(font)

        if is_dyslexic:
            theme = self.config.get("ui_theme", "dark")
            if theme in ("light", "solarized", "sepia", "classic_mac"):
                contrast_css = f"background-color: #ffffff; border: 3px solid #000000; color: #000000; font-family: '{family}'; font-size: {size}px; font-weight: bold; padding: 10px;"
            else:
                contrast_css = f"background-color: #000000; border: 3px solid #ffff00; color: #ffffff; font-family: '{family}'; font-size: {size}px; font-weight: bold; padding: 10px;"
            self.src_text_edit.setStyleSheet(contrast_css)
            self.target_text_edit.setStyleSheet(contrast_css)
        else:
            self.src_text_edit.setStyleSheet("")
            self.target_text_edit.setStyleSheet("")

    def init_ui(self):
        # Central Widget & Tab system (WallpaperWidget paints bg on all platforms)
        central_widget = WallpaperWidget()
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
        self.src_text_edit.setAcceptDrops(True)
        self.src_text_edit.dragEnterEvent = self._on_drag_enter
        self.src_text_edit.dropEvent = self._on_drop
        
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

        self.tts_btn = QPushButton("🔊 Read Aloud")
        self.tts_btn.setObjectName("secondaryBtn")
        self.tts_btn.clicked.connect(self.on_tts_speak)
        self.tts_btn.setToolTip("Lire la traduction à voix haute (pyttsx3 offline)")
        target_bottom.addWidget(self.tts_btn)

        target_vbox.addWidget(self.target_text_edit)
        target_vbox.addLayout(target_bottom)
        
        text_layout.addLayout(src_vbox, 1)
        text_layout.addLayout(target_vbox, 1)
        
        trans_layout.addLayout(text_layout, 1)

        # Manual Translate Button at bottom
        self.translate_btn = QPushButton("Translate (Enter)")
        self.translate_btn.clicked.connect(self.trigger_manual_translation)
        trans_layout.addWidget(self.translate_btn, 0)
        
        self.tabs.addTab(translator_widget, "Translator")

        # --- TAB 1.5: HISTORY ---
        history_widget = QWidget()
        hist_layout = QVBoxLayout(history_widget)
        hist_layout.setContentsMargins(10, 10, 10, 10)

        hist_search = QHBoxLayout()
        self.history_search_input = QLineEdit()
        self.history_search_input.setPlaceholderText("🔍 Search translations...")
        self.history_search_input.textChanged.connect(self.on_history_search)
        hist_search.addWidget(self.history_search_input)
        hist_layout.addLayout(hist_search)

        self.history_list = QTextEdit()
        self.history_list.setReadOnly(True)
        self.history_list.setPlaceholderText(
            "Recent translations will appear here automatically.\n"
            "Click a line to load it into the Translator tab."
        )
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_custom_context_menu)
        hist_layout.addWidget(self.history_list)

        hist_bottom = QHBoxLayout()
        self.history_count_label = QLabel("0 entries")
        self.history_count_label.setStyleSheet("color: #707a8a; font-size: 10px;")
        hist_bottom.addWidget(self.history_count_label)
        hist_bottom.addStretch()
        hist_refresh_btn = QPushButton("🔄 Refresh")
        hist_refresh_btn.setObjectName("secondaryBtn")
        hist_refresh_btn.clicked.connect(self.on_history_refresh)
        hist_bottom.addWidget(hist_refresh_btn)
        hist_layout.addLayout(hist_bottom)

        self.tabs.addTab(history_widget, "📜 History")

        # --- TAB 2: AUDIO TRANSLATION ---
        audio_widget = QWidget()
        audio_layout = QVBoxLayout(audio_widget)
        audio_layout.setContentsMargins(12, 12, 12, 12)

        # Source & model row
        audio_top = QHBoxLayout()

        audio_top.addWidget(QLabel("Source:"))
        self.audio_source_combo = QComboBox()
        self.audio_source_combo.addItems(["🎤 Microphone", "🔊 System Audio (WASAPI Loopback)"])
        self.audio_source_combo.setToolTip(
            "Microphone = votre voix.\n"
            "System Audio = tout son qui sort des haut-parleurs (YouTube, visio, meeting)."
        )
        audio_top.addWidget(self.audio_source_combo)

        audio_top.addSpacing(12)
        audio_top.addWidget(QLabel("Model:"))
        self.audio_model_combo = QComboBox()
        self.audio_model_combo.addItems([
            "tiny (rapide, ~150 Mo)",
            "tiny.en (English rapide, ~150 Mo)",
            "small (précis, ~500 Mo)",
            "medium (très précis, ~1.5 Go)",
        ])
        self.audio_model_combo.setCurrentIndex(1)  # tiny.en default
        self.audio_model_combo.setToolTip(
            "Modèle Whisper pour la reconnaissance vocale.\n"
            "tiny = rapide, small = plus précis, medium = très précis.\n"
            "Téléchargé automatiquement au premier usage."
        )
        audio_top.addWidget(self.audio_model_combo)
        audio_top.addStretch()
        audio_layout.addLayout(audio_top)

        # Record button + level bar row
        audio_controls = QHBoxLayout()

        self.audio_record_btn = QPushButton("🎙️ Start Recording")
        self.audio_record_btn.setObjectName("audioRecordBtn")
        self.audio_record_btn.setMinimumHeight(40)
        self.audio_record_btn.clicked.connect(self.on_audio_record_toggle)
        audio_controls.addWidget(self.audio_record_btn)

        # Simple text-based level meter
        self.audio_level_label = QLabel("🔇")
        self.audio_level_label.setMinimumWidth(80)
        self.audio_level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_level_label.setStyleSheet("font-size: 20px; font-family: monospace;")
        audio_controls.addWidget(self.audio_level_label)

        self.audio_status_label = QLabel("Ready")
        self.audio_status_label.setStyleSheet("color: #707a8a; font-size: 11px;")
        audio_controls.addWidget(self.audio_status_label)
        audio_controls.addStretch()
        audio_layout.addLayout(audio_controls)

        # Level bar (progress bar as audio meter)
        from PyQt6.QtWidgets import QProgressBar
        self.audio_level_bar = QProgressBar()
        self.audio_level_bar.setRange(0, 100)
        self.audio_level_bar.setValue(0)
        self.audio_level_bar.setTextVisible(False)
        self.audio_level_bar.setMaximumHeight(8)
        self.audio_level_bar.setStyleSheet(
            "QProgressBar { background: #1e1e2e; border: none; border-radius: 4px; }"
            "QProgressBar::chunk { background: #00ff41; border-radius: 4px; }"
        )
        audio_layout.addWidget(self.audio_level_bar)

        # Transcription display
        audio_layout.addWidget(QLabel("Transcription:"))
        self.audio_trans_text = QTextEdit()
        self.audio_trans_text.setReadOnly(True)
        self.audio_trans_text.setPlaceholderText(
            "Le texte transcrit apparaîtra ici en temps réel...\n\n"
            "💡 Conseil : Parlez clairement, le modèle tiny est optimisé pour la vitesse.\n"
            "Le texte sera automatiquement envoyé vers l'onglet Translator pour traduction."
        )
        self.audio_trans_text.setMaximumHeight(180)
        audio_layout.addWidget(self.audio_trans_text)

        # Action buttons row
        audio_actions = QHBoxLayout()
        self.audio_send_btn = QPushButton("📤 Send to Translator")
        self.audio_send_btn.setObjectName("secondaryBtn")
        self.audio_send_btn.clicked.connect(self.on_audio_send_to_translator)
        self.audio_send_btn.setEnabled(False)
        audio_actions.addWidget(self.audio_send_btn)

        self.audio_clear_btn = QPushButton("🗑️ Clear")
        self.audio_clear_btn.setObjectName("secondaryBtn")
        self.audio_clear_btn.clicked.connect(lambda: self.audio_trans_text.clear())
        audio_actions.addWidget(self.audio_clear_btn)
        audio_actions.addStretch()
        audio_layout.addLayout(audio_actions)

        audio_layout.addStretch()
        self.tabs.addTab(audio_widget, "🎤 Audio")

        # --- TAB 3: SETTINGS SIDE ---
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

        # Custom wallpaper picker
        wallpaper_layout = QHBoxLayout()
        wallpaper_layout.addWidget(QLabel("Custom Wallpaper (JPG/PNG) :"))
        self.wallpaper_path_label = QLabel(
            os.path.basename(self.config.get("custom_wallpaper", "")) or "None"
        )
        self.wallpaper_path_label.setStyleSheet("color: #707a8a; font-style: italic;")
        wallpaper_layout.addWidget(self.wallpaper_path_label)
        wallpaper_layout.addStretch()
        pick_wp_btn = QPushButton("📁 Choose Image")
        pick_wp_btn.setObjectName("secondaryBtn")
        pick_wp_btn.clicked.connect(self.on_pick_wallpaper)
        wallpaper_layout.addWidget(pick_wp_btn)
        clear_wp_btn = QPushButton("✕ Clear")
        clear_wp_btn.setObjectName("secondaryBtn")
        clear_wp_btn.clicked.connect(self.on_clear_wallpaper)
        wallpaper_layout.addWidget(clear_wp_btn)
        og_layout.addLayout(wallpaper_layout)

        # Wallpaper display mode
        wp_mode_layout = QHBoxLayout()
        wp_mode_layout.addWidget(QLabel("Display Mode :"))
        self.wp_mode_combo = QComboBox()
        self.wp_mode_combo.addItems([
            "🟫 Tile (repeat)", "🎯 Center", "📐 Stretch (fill)", "📏 Fit (aspect ratio)"
        ])
        mode_map = {"tile": 0, "center": 1, "stretch": 2, "fit": 3}
        self.wp_mode_combo.setCurrentIndex(mode_map.get(
            self.config.get("wallpaper_mode", "tile"), 0))
        self.wp_mode_combo.currentIndexChanged.connect(self.on_wallpaper_mode_changed)
        wp_mode_layout.addWidget(self.wp_mode_combo)
        wp_mode_layout.addStretch()
        og_layout.addLayout(wp_mode_layout)

        # Text area transparency slider (only meaningful with wallpaper)
        trans_layout = QHBoxLayout()
        trans_layout.addWidget(QLabel("Text Area Transparency :"))
        self.wp_transparency_slider = QSpinBox()
        self.wp_transparency_slider.setRange(50, 100)
        self.wp_transparency_slider.setValue(
            self.config.get("wallpaper_transparency", 85))
        self.wp_transparency_slider.setSuffix("%")
        self.wp_transparency_slider.setToolTip(
            "Opacity of text/edit areas. 100% = fully opaque, 50% = very transparent.")
        self.wp_transparency_slider.valueChanged.connect(self.on_wallpaper_transparency_changed)
        trans_layout.addWidget(self.wp_transparency_slider)
        trans_layout.addStretch()
        trans_layout.addWidget(QLabel("<i>Lower = more image visible through text</i>"))
        og_layout.addLayout(trans_layout)

        # Font colour override (useful when wallpaper makes theme text unreadable)
        fontcolor_layout = QHBoxLayout()
        fontcolor_layout.addWidget(QLabel("Override Text Colour :"))
        self.fontcolor_combo = QComboBox()
        self.fontcolor_combo.addItems([
            "🌓 Auto (theme default)",
            "⚫ Black (#000000)",
            "⚪ White (#ffffff)",
            "🟡 Yellow (#ffcc00)",
            "🟢 Green (#00ff41)",
            "🔵 Cyan (#00e5ff)",
            "🔴 Red (#ff3333)",
            "🟠 Orange (#ff8800)",
            "🟣 Purple (#bd93f9)",
        ])
        current_color = self.config.get("font_color_override", "")
        idx_map = {"": 0, "#000000": 1, "#ffffff": 2, "#ffcc00": 3, "#00ff41": 4,
                    "#00e5ff": 5, "#ff3333": 6, "#ff8800": 7, "#bd93f9": 8}
        self.fontcolor_combo.setCurrentIndex(idx_map.get(current_color, 0))
        fontcolor_layout.addWidget(self.fontcolor_combo)
        fontcolor_layout.addStretch()
        og_layout.addLayout(fontcolor_layout)

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

        # ── Glossary group ──
        glossary_group = QGroupBox("📚 Glossaire personnalisé (Termes à ne pas traduire)")
        gloss_layout = QVBoxLayout(glossary_group)
        gloss_layout.addWidget(QLabel(
            "<i>Définissez les termes qui doivent garder leur nom exact ou être traduits "
            "d'une manière spécifique. Format : <b>Source → Cible</b> (une entrée par ligne).</i>"
        ))
        self.glossary_edit = QTextEdit()
        self.glossary_edit.setPlaceholderText(
            "Ollama → Ollama\nAPI → API\nGemma → Gemma\nShallotT → ShallotT\n"
            "Docker → Docker\nWhisper → Whisper\nmachine learning → apprentissage automatique"
        )
        self.glossary_edit.setMaximumHeight(120)
        gloss_layout.addWidget(self.glossary_edit)

        gloss_actions = QHBoxLayout()
        gloss_actions.addStretch()
        gloss_reset_btn = QPushButton("Reset to Defaults")
        gloss_reset_btn.setObjectName("secondaryBtn")
        gloss_reset_btn.clicked.connect(self.on_glossary_reset)
        gloss_actions.addWidget(gloss_reset_btn)
        gloss_layout.addLayout(gloss_actions)
        settings_layout.addWidget(glossary_group)

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

        # ── Clipboard monitor + Cache group ──
        extras_group = QGroupBox("📋 Presse-papier & Cache")
        extras_layout = QVBoxLayout(extras_group)

        clip_row = QHBoxLayout()
        self.clipboard_monitor_cb = QCheckBox(
            "Surveiller le presse-papier (traduction popup automatique)"
        )
        self.clipboard_monitor_cb.setChecked(self._clipboard_monitoring)
        self.clipboard_monitor_cb.toggled.connect(self.on_toggle_clipboard_monitor)
        clip_row.addWidget(self.clipboard_monitor_cb)
        extras_layout.addLayout(clip_row)

        cache_row = QHBoxLayout()
        self.cache_info_label = QLabel("")
        cache_row.addWidget(self.cache_info_label)
        cache_row.addStretch()
        clear_cache_btn = QPushButton("🗑️ Clear Cache")
        clear_cache_btn.setObjectName("secondaryBtn")
        clear_cache_btn.clicked.connect(self.on_clear_cache)
        cache_row.addWidget(clear_cache_btn)
        extras_layout.addLayout(cache_row)

        settings_layout.addWidget(extras_group)

        settings_layout.addStretch()

        save_layout = QHBoxLayout()
        save_layout.addStretch()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_app_settings)
        save_layout.addWidget(save_btn)
        settings_layout.addLayout(save_layout)

        # Export / Import row
        export_layout = QHBoxLayout()
        export_btn = QPushButton("📤 Export Config")
        export_btn.setObjectName("secondaryBtn")
        export_btn.clicked.connect(self.on_export_config)
        export_layout.addWidget(export_btn)
        import_btn = QPushButton("📥 Import Config")
        import_btn.setObjectName("secondaryBtn")
        import_btn.clicked.connect(self.on_import_config)
        export_layout.addWidget(import_btn)
        export_layout.addStretch()
        settings_layout.addLayout(export_layout)

        self.tabs.addTab(settings_widget, "Settings")
        
        # Status Bar
        self.statusBar().showMessage(f"Connected to {self.config['ollama_url']} ({self.config['ollama_model']})")
        self.theme_indicator = QLabel("")
        self.theme_indicator.setStyleSheet("font-size: 14px; padding-right: 6px; background: transparent; border: none;")
        self.statusBar().addPermanentWidget(self.theme_indicator)

        # Populate glossary text edit from loaded entries
        gloss_text = "\n".join(
            f"{e.get('source', '')} → {e.get('target', '')}"
            for e in self.glossary_entries
        )
        self.glossary_edit.setPlainText(gloss_text)

        # Decorative theme overlays.
        # Emoji overlays are a Windows / macOS feature — on plain X11 without
        # a compositor, transparency is broken and emoji glyphs may not render.
        # We detect the platform and only create the overlays on supported OSes.
        self._overlays_supported = sys.platform in ("win32", "darwin")

        if self._overlays_supported:
            def _make_overlay(char: str, size: int, parent) -> QLabel:
                lbl = QLabel(char, parent)
                font = QFont()
                font.setPointSize(int(size * 0.75))
                lbl.setFont(font)
                lbl.setFixedSize(size, size)
                lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                lbl.setStyleSheet("background: transparent; border: none;")
                return lbl

            self.dragon_head_label = _make_overlay("🐲", 72, central_widget)
            self.dragon_head_label.hide()
            self.dragon_tail_label = _make_overlay("🐉", 72, central_widget)
            self.dragon_tail_label.hide()
            self.nfs_car_label = _make_overlay("🏎️", 80, central_widget)
            self.nfs_car_label.hide()
            self.nfs_smoke_label = _make_overlay("💨", 60, central_widget)
            self.nfs_smoke_label.hide()
            self.nfs_nos_label = _make_overlay("🔥", 56, central_widget)
            self.nfs_nos_label.hide()
        else:
            # Linux / other: skip overlays, keep title-bar + status-bar emoji only
            self.dragon_head_label = None
            self.dragon_tail_label = None
            self.nfs_car_label = None
            self.nfs_smoke_label = None
            self.nfs_nos_label = None

        # Re-apply current theme overlays now that they exist
        theme_key = self.config.get("ui_theme", "dark")
        if self._overlays_supported:
            if theme_key == "dragon":
                self.dragon_head_label.show()
                self.dragon_tail_label.show()
            elif theme_key == "nfs_tokyo":
                self.nfs_car_label.show()
                self.nfs_smoke_label.show()
                self.nfs_nos_label.show()
            self._position_theme_overlays()

        # Re-apply wallpaper NOW that the WallpaperWidget exists
        user_bg = self.config.get("custom_wallpaper", "")
        cw = self.centralWidget()
        if user_bg and os.path.exists(user_bg) and isinstance(cw, WallpaperWidget):
            cw.set_wallpaper(user_bg)

    def setup_system_tray(self):
        """Sets up the icon in the system menu bar for background running."""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Simple native looking drawing or fallback to simple icon
        # System tray icon — must be set BEFORE show() on Linux.
        # Modern Ubuntu (GNOME) AppIndicators need the icon attached early.
        tray_icon = getattr(self, '_shallot_icon', None)
        if tray_icon and not tray_icon.isNull():
            # Ensure multiple sizes for good rendering in the panel
            tray_icon.addPixmap(tray_icon.pixmap(64, 64))
            tray_icon.addPixmap(tray_icon.pixmap(32, 32))
            tray_icon.addPixmap(tray_icon.pixmap(22, 22))
            tray_icon.addPixmap(tray_icon.pixmap(16, 16))
            self.tray_icon.setIcon(tray_icon)
        else:
            # Fallback coloured pixmap
            pixmap = QPixmap(64, 64)
            pixmap.fill(QColor(137, 180, 250))
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
        
        # Deploy worker thread (with cache + glossary)
        worker = TranslationWorker(
            self.translator, text, src_lang, target_lang,
            self.translation_done.emit, self.translation_failed.emit,
            glossary_entries=self.glossary_entries,
            model=self.config.get("ollama_model", "gemma:latest"),
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

        # Save font colour override
        fc_idx = self.fontcolor_combo.currentIndex()
        fc_map = {0: "", 1: "#000000", 2: "#ffffff", 3: "#ffcc00", 4: "#00ff41",
                   5: "#00e5ff", 6: "#ff3333", 7: "#ff8800", 8: "#bd93f9"}
        self.config["font_color_override"] = fc_map.get(fc_idx, "")

        # Save wallpaper mode & transparency
        mode_map = {0: "tile", 1: "center", 2: "stretch", 3: "fit"}
        self.config["wallpaper_mode"] = mode_map.get(self.wp_mode_combo.currentIndex(), "tile")
        self.config["wallpaper_transparency"] = self.wp_transparency_slider.value()

        self.apply_theme(theme_sel)

        # Save glossary entries
        gloss_raw = self.glossary_edit.toPlainText().strip()
        new_glossary = []
        for line in gloss_raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if '→' in line:
                src, tgt = line.split('→', 1)
                new_glossary.append({"source": src.strip(), "target": tgt.strip(), "note": ""})
            elif '=' in line:
                src, tgt = line.split('=', 1)
                new_glossary.append({"source": src.strip(), "target": tgt.strip(), "note": ""})
        if new_glossary:
            self.glossary_entries = new_glossary
            save_glossary(new_glossary)
        self.config["glossary_entries"] = new_glossary

        save_config(self.config)

        # Re-initialize translator
        self.translator = OllamaTranslator(base_url=url, model=model, api_key=key)

        QMessageBox.information(self, "Settings Saved", f"Configuration updated and saved to:\n{CONFIG_PATH}")
        self.statusBar().showMessage(f"Active configuration: {model}@{url}", 4000)

    # ── TTS, Glossary, Drag-Drop, Clipboard Monitor ──────────────

    def on_tts_speak(self):
        """Read the translated text aloud with language-matched voice."""
        text = self.target_text_edit.toPlainText()
        if not text.strip():
            return
        target_lang = self.target_lang_box.currentText()
        self.tts_btn.setText("🔊 Speaking...")
        self.tts_btn.setEnabled(False)

        def _done():
            self.tts_btn.setText("🔊 Read Aloud")
            self.tts_btn.setEnabled(True)

        def _err(msg):
            self.tts_btn.setText("🔊 Read Aloud")
            self.tts_btn.setEnabled(True)
            self.statusBar().showMessage(f"TTS error: {msg}", 3000)

        tts_speak(text, target_lang=target_lang, on_done=_done, on_error=_err)

    def _on_drag_enter(self, event):
        """Accept file drops on the source text edit."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.src_text_edit.setStyleSheet(
                self.src_text_edit.styleSheet() +
                "QTextEdit { border: 2px dashed #ffaa33 !important; }"
            )

    def _on_drop(self, event):
        """Handle file drop: extract text and load into editor."""
        self.src_text_edit.setStyleSheet("")  # Restore theme
        urls = event.mimeData().urls()
        if not urls:
            return

        filepath = urls[0].toLocalFile()
        text, error = doc_extract_text(filepath)
        if error:
            self.statusBar().showMessage(f"Import error: {error}", 5000)
            return
        if text:
            self.src_text_edit.setPlainText(text)
            self.statusBar().showMessage(
                f"📄 Imported {os.path.basename(filepath)} ({len(text)} chars)", 4000
            )
            self.translate_text()

    def on_glossary_reset(self):
        """Reset glossary to default entries."""
        from src.glossary import DEFAULT_GLOSSARY_ENTRIES
        self.glossary_entries = list(DEFAULT_GLOSSARY_ENTRIES)
        save_glossary(self.glossary_entries)
        gloss_text = "\n".join(
            f"{e.get('source', '')} → {e.get('target', '')}"
            for e in self.glossary_entries
        )
        self.glossary_edit.setPlainText(gloss_text)
        self.statusBar().showMessage("Glossary reset to defaults.", 3000)

    def on_toggle_clipboard_monitor(self, enabled: bool):
        """Start/stop the clipboard monitor worker."""
        self._clipboard_monitoring = enabled
        if enabled:
            if self._clipboard_worker is None:
                self._clipboard_worker = ClipboardWorker(interval_ms=800)
                self._clipboard_worker.new_text.connect(self._on_clipboard_text)
            self._clipboard_worker.start()
            self.statusBar().showMessage("📋 Clipboard monitor ON — popup translation active", 3000)
        else:
            if self._clipboard_worker:
                self._clipboard_worker.stop()
            self.statusBar().showMessage("📋 Clipboard monitor OFF", 2000)

    def on_pick_wallpaper(self):
        """Open file dialog to choose a JPG/PNG wallpaper."""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Wallpaper Image",
            os.path.expanduser("~/Pictures"),
            "Images (*.jpg *.jpeg *.png *.bmp *.svg)"
        )
        if path:
            self.config["custom_wallpaper"] = path
            self.wallpaper_path_label.setText(os.path.basename(path))
            # Re-apply theme to show the wallpaper immediately
            theme_key = self.config.get("ui_theme", "dark")
            self.apply_theme(theme_key)

    def on_clear_wallpaper(self):
        """Remove custom wallpaper, revert to theme default."""
        self.config["custom_wallpaper"] = ""
        self.wallpaper_path_label.setText("None")
        theme_key = self.config.get("ui_theme", "dark")
        self.apply_theme(theme_key)

    def on_wallpaper_mode_changed(self, idx: int):
        """Apply wallpaper display mode immediately."""
        mode_map = {0: "tile", 1: "center", 2: "stretch", 3: "fit"}
        self.config["wallpaper_mode"] = mode_map.get(idx, "tile")
        user_bg = self.config.get("custom_wallpaper", "")
        if user_bg:
            cw = self.centralWidget()
            if isinstance(cw, WallpaperWidget):
                cw.set_wallpaper(user_bg, self.config["wallpaper_mode"])

    def on_wallpaper_transparency_changed(self, val: int):
        """Update text area transparency and re-apply theme."""
        self.config["wallpaper_transparency"] = val
        user_bg = self.config.get("custom_wallpaper", "")
        if user_bg:
            theme_key = self.config.get("ui_theme", "dark")
            self.apply_theme(theme_key)

    def on_clear_cache(self):
        """Clear the translation cache."""
        cache_clear()
        self._update_cache_info_label()
        self.statusBar().showMessage("🗑️ Translation cache cleared.", 3000)

    def _update_cache_info_label(self):
        """Refresh the cache stats label in Settings."""
        try:
            st = cache_stats()
            self.cache_info_label.setText(
                f"📊 Cache: {st['entries']} entries · {st['size_mb']} MB"
            )
        except Exception:
            pass

    def _on_clipboard_text(self, text: str):
        """Called when new text appears in clipboard (if monitoring is on)."""
        if not self._clipboard_monitoring:
            return
        if len(text) < 4 or len(text) > 5000:
            return  # Skip trivial or huge clipboard content

        # Show desktop popup with quick translation
        self._show_desktop_popup(text)

    def _show_desktop_popup(self, text: str):
        """Translate and show in the desktop overlay popup."""
        if self._desktop_popup is None:
            self._desktop_popup = DesktopTranslationPopup()

        src_lang = self.src_lang_box.currentText()
        target_lang = self.target_lang_box.currentText()

        # Quick inline translation via a small background worker
        def _translate_and_show():
            try:
                model = self.config.get("ollama_model", "gemma:latest")
                # Check cache first
                cached = cache_lookup(text, src_lang, target_lang, model)
                if cached:
                    self._desktop_popup.show_translation(
                        text, cached, f"{src_lang} → {target_lang}"
                    )
                    return

                result = self.translator.translate(text, src_lang, target_lang)
                if result:
                    cache_store(text, src_lang, target_lang, model, result)
                    self._desktop_popup.show_translation(
                        text, result, f"{src_lang} → {target_lang}"
                    )
            except Exception:
                pass  # Silent fail for clipboard popup

        threading.Thread(target=_translate_and_show, daemon=True).start()

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

    # ── Audio Translation ────────────────────────────────────────

    def on_audio_record_toggle(self):
        """Start / stop audio recording with the selected source."""
        if self._audio_capture and self._audio_capture.recording:
            self._stop_audio_recording()
        else:
            self._start_audio_recording()

    def _start_audio_recording(self):
        from src.audio_capture import AudioCapture

        self._audio_capture = AudioCapture(sample_rate=16000)
        source_idx = self.audio_source_combo.currentIndex()

        if source_idx == 0:
            dev_id, dev_name = AudioCapture.find_microphone_device()
        else:
            dev_id, dev_name = AudioCapture.find_wasapi_loopback_device()

        if dev_id is None:
            self.audio_status_label.setText(f"❌ {dev_name}")
            self.audio_status_label.setStyleSheet("color: #f38ba8; font-size: 11px;")
            return

        self.audio_status_label.setText(f"🎙️ {dev_name}")
        self.audio_status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        self.audio_record_btn.setText("⏹️ Stop Recording")
        self.audio_record_btn.setStyleSheet(
            "QPushButton { background-color: #f38ba8; color: #000; font-weight: bold; "
            "border-radius: 5px; padding: 8px 20px; min-height: 40px; }"
        )

        try:
            self._audio_capture.start(device_id=dev_id,
                                      level_callback=self._on_audio_level)
            self._audio_timer.start()
            self._audio_level_timer.start()
        except Exception as e:
            self.audio_status_label.setText(f"❌ Error: {e}")
            self.audio_status_label.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _stop_audio_recording(self):
        self._audio_timer.stop()
        self._audio_level_timer.stop()

        if self._audio_capture:
            self._audio_capture.stop()
            self._audio_capture = None

        self.audio_record_btn.setText("🎙️ Start Recording")
        self.audio_record_btn.setStyleSheet("")  # Revert to theme
        self.audio_status_label.setText("Ready")
        self.audio_status_label.setStyleSheet("color: #707a8a; font-size: 11px;")
        self.audio_level_bar.setValue(0)
        self.audio_level_label.setText("🔇")

    def _on_audio_level(self, level: float):
        """Called from audio callback — just store, UI update via timer."""
        self._last_audio_level = level

    def _audio_refresh_level(self):
        """Update the level bar and label from the last known level."""
        level = getattr(self, '_last_audio_level', 0.0)
        pct = min(int(level * 200), 100)  # Scale roughly to 0-100
        self.audio_level_bar.setValue(pct)
        if pct < 5:
            self.audio_level_label.setText("🔇")
        elif pct < 25:
            self.audio_level_label.setText("🔈")
        elif pct < 60:
            self.audio_level_label.setText("🔉")
        else:
            self.audio_level_label.setText("🔊")

    def _audio_poll_chunk(self):
        """Called by QTimer: grab the latest audio chunk and run STT."""
        if not self._audio_capture or not self._audio_capture.recording:
            return

        chunk = self._audio_capture.drain_chunk()
        if chunk is None or len(chunk) < 16000 * 0.3:
            return  # Too short, skip

        # Dispatch STT in background
        model_map = {
            0: "tiny", 1: "tiny.en", 2: "small", 3: "medium",
        }
        model_size = model_map.get(self.audio_model_combo.currentIndex(), "tiny.en")

        from src.stt import transcribe_async

        self.audio_status_label.setText("🔍 Transcribing...")
        self.audio_status_label.setStyleSheet("color: #ffaa33; font-size: 11px;")

        transcribe_async(
            audio=chunk,
            sample_rate=16000,
            model_size=model_size,
            on_done=self._on_transcription_done,
            on_error=self._on_transcription_error,
        )

    def _on_transcription_done(self, text: str):
        if not text.strip():
            self.audio_status_label.setText("🎙️ Listening...")
            self.audio_status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
            return

        # Append to transcription display
        current = self.audio_trans_text.toPlainText()
        if current:
            self.audio_trans_text.setPlainText(current + " " + text)
        else:
            self.audio_trans_text.setPlainText(text)

        # Auto-scroll to bottom
        self.audio_trans_text.moveCursor(self.audio_trans_text.textCursor().MoveOperation.End)

        # Enable send button
        self.audio_send_btn.setEnabled(True)

        # Auto-send to translator
        self._auto_send_to_translator(text)

        self.audio_status_label.setText("🎙️ Listening...")
        self.audio_status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")

    def _on_transcription_error(self, err: str):
        self.audio_status_label.setText(f"❌ STT error: {err[:40]}")
        self.audio_status_label.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _auto_send_to_translator(self, text: str):
        """Send transcribed text to the Translator tab and trigger translation."""
        self.src_text_edit.setPlainText(text)
        self.translate_text()

    def on_audio_send_to_translator(self):
        """Manually send the full transcription to Translator."""
        text = self.audio_trans_text.toPlainText()
        if text.strip():
            self.tabs.setCurrentIndex(0)  # Switch to Translator tab
            self._auto_send_to_translator(text)

    # ── Export / Import ──────────────────────────────────────────

    def on_export_config(self):
        """Save current config to a user-chosen JSON file."""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Config", "shallott_config.json", "JSON (*.json)")
        if path:
            save_config(self.config)
            import shutil
            shutil.copy(CONFIG_PATH, path)
            self.statusBar().showMessage(f"📤 Config exported to: {path}", 4000)

    def on_import_config(self):
        """Load config from a JSON file and apply it."""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Config", "", "JSON (*.json)")
        if path:
            import json
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    imported = json.load(f)
                self.config.update(imported)
                save_config(self.config)
                self.statusBar().showMessage("📥 Config imported! Restart to apply all settings.", 5000)
                QMessageBox.information(self, "Config Imported",
                    "Settings loaded. Some changes require a restart.\n"
                    "Theme, font, and wallpaper are applied immediately.")
                # Re-apply what we can
                self.apply_theme(self.config.get("ui_theme", "dark"))
                self.apply_font_preferences()
            except Exception as e:
                QMessageBox.warning(self, "Import Failed", str(e))

    # ── Translation History ──────────────────────────────────────

    def on_history_refresh(self):
        """Load recent translations from cache into the history tab."""
        search = self.history_search_input.text().strip()
        entries = cache_stats()
        recent = []  # We'll populate from cache metadata
        # Query cache: get_recent returns list of dicts
        from src.translation_cache import get_recent
        rows = get_recent(limit=50, search=search)
        html_parts = ['<div style="font-family: monospace; font-size: 11px;">']
        for i, r in enumerate(rows):
            ts = r.get("created_at", "")[:19]
            src = r.get("source_lang", "?")
            tgt = r.get("target_lang", "?")
            model = r.get("model", "?")
            text = r.get("translation", "")[:200]
            html_parts.append(
                f'<div style="margin:4px 0;padding:6px;background:#1e1e2e;'
                f'border-radius:4px;color:#cdd6f4;">'
                f'<span style="color:#707a8a;">{ts}</span> '
                f'<b>{src}→{tgt}</b> <span style="color:#ffaa33;">{model}</span><br>'
                f'<span style="color:#a6e3a1;">{text}</span></div>'
            )
        html_parts.append('</div>')
        self.history_list.setHtml("".join(html_parts))
        self.history_count_label.setText(f"{len(rows)} entries")

    def on_history_search(self, _text: str):
        """Debounced search — just refresh."""
        self.on_history_refresh()

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

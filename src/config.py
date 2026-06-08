import os
import json
import platform

DEFAULT_CONFIG = {
    "ollama_url": "http://localhost:11434",
    "ollama_model": "gemma:latest", # Gemma 8B ou gemma2:9b (ou gemma2:9b-instruct-q4_K_M)
    "ollama_api_key": "", # Clé d'API optionnelle pour reverse proxies sécurisés (ex. Bearer token)
    "source_lang": "Auto Detection",
    "target_lang": "French",
    "ui_theme": "dark",
    "max_characters": 10000, # Limite par défaut à 10 000 lettres pour optimiser la vitesse de traitement
    "shortcut_translate": "ctrl+c+c",
    "shortcut_ocr": "ctrl+f8"
}

# Cross-platform config path (APPDATA on Windows, or ~/.config on Unix)
if platform.system() == "Windows":
    CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ShallotT")
else:
    CONFIG_DIR = os.path.expanduser("~/.config/ShallotT")

CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

def load_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
        
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Ensure all default keys are present
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")

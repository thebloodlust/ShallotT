"""
Custom glossary / terminology manager for ShallotT.

Users define terms that should NEVER be translated, or specify
exact translations for domain-specific vocabulary.

Example glossary entry:   "Ollama"  →  "Ollama"
                          "API"     →  "API"
                          "Gemma"   →  "Gemma"

The glossary is injected into the translation prompt so the LLM
respects the user's terminology preferences.
"""

import json
import os
from src.config import CONFIG_DIR

GLOSSARY_PATH = os.path.join(CONFIG_DIR, "glossary.json")

DEFAULT_GLOSSARY_ENTRIES = [
    {"source": "Ollama",      "target": "Ollama",      "note": "nom du logiciel"},
    {"source": "API",         "target": "API",         "note": "terme technique"},
    {"source": "Gemma",       "target": "Gemma",       "note": "nom du modèle"},
    {"source": "ShallotT",    "target": "ShallotT",    "note": "nom de l'appli"},
    {"source": "PyTorch",     "target": "PyTorch",     "note": "framework"},
    {"source": "CUDA",        "target": "CUDA",        "note": "technologie GPU"},
    {"source": "Whisper",     "target": "Whisper",     "note": "modèle STT"},
    {"source": "WASAPI",      "target": "WASAPI",      "note": "API audio Windows"},
    {"source": "Docker",      "target": "Docker",      "note": "conteneurisation"},
    {"source": "SQLite",      "target": "SQLite",      "note": "base de données"},
    {"source": "JSON",        "target": "JSON",        "note": "format"},
    {"source": "GitHub",      "target": "GitHub",      "note": "plateforme"},
    {"source": "ChatGPT",     "target": "ChatGPT",     "note": "nom de produit"},
    {"source": "macOS",       "target": "macOS",       "note": "système Apple"},
    {"source": "Windows",     "target": "Windows",     "note": "système Microsoft"},
]


def load_glossary() -> list[dict]:
    """Return the list of glossary entries. Creates default on first call."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(GLOSSARY_PATH):
        save_glossary(DEFAULT_GLOSSARY_ENTRIES)
        return list(DEFAULT_GLOSSARY_ENTRIES)
    try:
        with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return list(DEFAULT_GLOSSARY_ENTRIES)


def save_glossary(entries: list[dict]):
    """Persist glossary entries to disk."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(GLOSSARY_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def build_glossary_prompt_snippet(entries: list[dict]) -> str:
    """Turn glossary entries into a prompt instruction snippet.

    Returns an empty string when the glossary is empty (no noise in prompt).
    """
    if not entries:
        return ""

    lines = []
    for e in entries:
        src = e.get("source", "").strip()
        tgt = e.get("target", "").strip()
        if src and tgt:
            if src == tgt:
                lines.append(f'- "{src}" = NE PAS TRADUIRE, garder tel quel')
            else:
                lines.append(f'- "{src}" → "{tgt}"')

    if not lines:
        return ""

    return (
        "\n\n[GLOSSAIRE PERSONNALISÉ — respecte strictement ces règles :]\n"
        + "\n".join(lines)
        + "\nApplique ces règles avant toute autre considération de traduction."
    )


def inject_glossary_into_prompt(base_prompt: str, entries: list[dict]) -> str:
    """Return the base prompt with the glossary snippet appended."""
    snippet = build_glossary_prompt_snippet(entries)
    if not snippet:
        return base_prompt
    return base_prompt + snippet

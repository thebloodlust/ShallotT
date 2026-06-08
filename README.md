# ShallotT 🧅

**AI-powered translation plugin** with global keyboard shortcuts, OCR support,
and a browser extension — all powered by a remote
[Ollama](https://ollama.com/) instance running **Gemma 3 8B (Q4\_K\_M)**.

Works seamlessly over any network, including WireGuard and Tailscale VPNs.

---

## Features

| Feature | Details |
|---|---|
| **Ctrl + C + C** | Translate the current clipboard content |
| **Ctrl + F8** | Drag-select a screen region → OCR → translate |
| **Browser extension** | Context menu + **Alt + T** shortcut, popup, settings page |
| **Remote Ollama** | Configure any host (LAN, WireGuard, Tailscale) |
| **Model** | `gemma3:8b-instruct-q4_K_M` (configurable) |
| **System tray** | Status indicator, config shortcut, quit |

---

## Quick start

### 1 – Install system dependencies

| Dependency | Install |
|---|---|
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | `sudo apt install tesseract-ocr` / `brew install tesseract` / [Windows installer](https://github.com/UB-Mannheim/tesseract/wiki) |
| Ollama | See [ollama.com](https://ollama.com/download) |

Pull the model on the Ollama server:

```bash
ollama pull gemma3:8b-instruct-q4_K_M
```

### 2 – Install ShallotT

```bash
pip install shallott          # from PyPI (once published)
# or, from source:
git clone https://github.com/thebloodlust/ShallotT
cd ShallotT
pip install .
```

### 3 – Configure

Copy `config.example.json` → `config.json` in the same directory (or `~/.config/shallott/config.json`) and edit:

```json
{
  "ollama": {
    "host": "http://192.168.1.100:11434",
    "model": "gemma3:8b-instruct-q4_K_M"
  },
  "translation": {
    "target_language": "en"
  }
}
```

> **VPN users:** set `host` to the WireGuard / Tailscale IP of the machine
> running Ollama (e.g. `http://100.x.y.z:11434` for Tailscale).

### 4 – Run

```bash
shallott
# or
python -m shallott.app
```

A tray icon appears (🧅).  Press **Ctrl+C+C** to translate clipboard,
**Ctrl+F8** to select a region for OCR translation.

---

## Browser extension

Load the `browser_extension/` folder as an **unpacked extension** in Chrome/Edge:

1. Open `chrome://extensions` → enable **Developer mode**
2. Click **Load unpacked** → select `browser_extension/`
3. Click the 🧅 icon → **⚙ Settings** → enter your Ollama host URL

**Usage:**
- Select text on any page → right-click → *Translate with ShallotT*
- Or press **Alt + T** to translate the current selection

---

## Configuration reference

| Key | Default | Description |
|---|---|---|
| `ollama.host` | `http://localhost:11434` | Ollama server URL |
| `ollama.model` | `gemma3:8b-instruct-q4_K_M` | Model tag |
| `ollama.timeout` | `60` | Request timeout in seconds |
| `ollama.verify_ssl` | `true` | Verify TLS certificate |
| `hotkeys.translate_clipboard` | `<ctrl>+c+c` | Clipboard translation shortcut |
| `hotkeys.translate_ocr` | `<ctrl>+<f8>` | OCR translation shortcut |
| `translation.target_language` | `en` | Target language code or name |
| `ocr.lang` | `eng+fra+deu+spa+jpn+chi_sim` | Tesseract language packs |
| `ui.overlay_duration` | `8` | Seconds before the result overlay disappears |

The config file is loaded from (in order):
1. `--config PATH` CLI argument
2. `SHALLOTT_CONFIG` environment variable
3. `./config.json`
4. `~/.config/shallott/config.json`
5. `~/.shallott.json`

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

MIT

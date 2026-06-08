"""Ollama API client for ShallotT.

Connects to a remote (or local) Ollama instance.  Works seamlessly over
WireGuard / Tailscale VPNs because the target address is fully configurable.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Generator

import requests

logger = logging.getLogger(__name__)

_TRANSLATE_SYSTEM_PROMPT = (
    "You are a professional translator. "
    "Translate the user's text into {target_language}. "
    "If the target language matches the detected source language, translate into English instead. "
    "Return ONLY the translated text — no explanations, no labels, no markdown."
)

_DETECT_LANG_PROMPT = (
    "Identify the language of the following text. "
    "Reply with only the language name in English (e.g. French, Japanese, German)."
)


class OllamaClient:
    """Thin wrapper around the Ollama /api/generate and /api/chat endpoints."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        ollama_cfg = cfg.get("ollama", {})
        self.host: str = ollama_cfg.get("host", "http://localhost:11434").rstrip("/")
        self.model: str = ollama_cfg.get("model", "gemma3:8b-instruct-q4_K_M")
        self.timeout: int = int(ollama_cfg.get("timeout", 60))
        self.verify_ssl: bool = bool(ollama_cfg.get("verify_ssl", True))
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def is_reachable(self) -> bool:
        """Return True if the Ollama host responds to a health-check."""
        try:
            resp = self._session.get(
                f"{self.host}/api/tags",
                timeout=5,
                verify=self.verify_ssl,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def translate(self, text: str, target_language: str = "en") -> str:
        """Translate *text* into *target_language* using the configured model.

        Returns the translated string.
        """
        system = _TRANSLATE_SYSTEM_PROMPT.format(target_language=target_language)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            "stream": False,
        }
        response = self._post("/api/chat", payload)
        return response["message"]["content"].strip()

    def translate_stream(
        self, text: str, target_language: str = "en"
    ) -> Generator[str, None, None]:
        """Streaming translation — yields partial tokens as they arrive."""
        system = _TRANSLATE_SYSTEM_PROMPT.format(target_language=target_language)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            "stream": True,
        }
        with self._session.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=self.timeout,
            verify=self.verify_ssl,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                chunk = json.loads(raw_line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.host}{path}"
        logger.debug("POST %s model=%s", url, payload.get("model"))
        resp = self._session.post(
            url,
            json=payload,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        return resp.json()

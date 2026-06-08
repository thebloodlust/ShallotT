import requests
import json
import urllib.parse
import re

class OllamaTranslator:
    def __init__(self, base_url="http://localhost:11434", model="gemma2:9b", api_key=""):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key

    @property
    def base_url(self):
        return self._base_url

    @base_url.setter
    def base_url(self, value):
        self._base_url = self._normalize_url(value)

    def _normalize_url(self, url):
        cleaned = (url or "http://localhost:11434").strip()
        if not cleaned:
            return "http://localhost:11434"
            
        # Strip common Ollama API paths or trailing slashes
        cleaned = re.sub(r'/api/tags/?$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'/api/generate/?$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'/api/?$', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.rstrip('/')
        
        # Ensure scheme
        if not cleaned.lower().startswith(('http://', 'https://')):
            cleaned = "http://" + cleaned
            
        try:
            parsed = urllib.parse.urlparse(cleaned)
            # Add port 11434 if no port is present on the netloc (hostname or IP)
            if ':' not in parsed.netloc:
                cleaned = f"{parsed.scheme}://{parsed.netloc}:11434"
            else:
                cleaned = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            if ':' not in cleaned[6:]:
                cleaned = cleaned + ":11434"
        return cleaned

    def _get_headers(self):
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def translate(self, text, source_lang="Auto Detection", target_lang="French"):
        if not text or not text.strip():
            return ""

        url = f"{self.base_url}/api/generate"
        
        # Optimize prompt for translation with Gemma to be ultra-fast and direct, with no yapping.
        if source_lang == "Auto Detection" or not source_lang:
            prompt_context = f"Translate the following text into {target_lang}."
        else:
            prompt_context = f"Translate the following text from {source_lang} to {target_lang}."
            
        full_prompt = (
            f"<start_of_turn>user\n"
            f"You are a professional, high-performance translator like DeepL. Translate the text accurately. Preserve the original formatting, paragraph breaks, tone, and style.\n"
            f"CRITICAL: Do not write any explanations, summaries, preamble, warning, notes, or code blocks. Just output the translation directly.\n\n"
            f"Instruction: {prompt_context}\n\n"
            f"Text to translate:\n{text}\n"
            f"<start_of_turn>model\n"
        )

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 2048 # limit maximum translation tokens for speed
            }
        }

        try:
            # Increased timeout to 60 seconds to allow time for Ollama to load the model into VRAM/RAM on cold starts
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=60)
            response.raise_for_status()
            result = response.json()
            translation = result.get("response", "").strip()
            return translation
        except requests.exceptions.ReadTimeout:
            raise Exception(f"Timeout error: Ollama did not respond in 60 seconds.\n"
                            f"The model '{self.model}' might be too large or loading slowly on the Mac mini server. Try again in a moment!")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Connection error: Could not reach Ollama at {self.base_url}.\n"
                            f"Please verification that Ollama is running and accessible (check Tailscale/Wireguard VPN if used).")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"Model '{self.model}' not found in Ollama.\n"
                                f"Please run 'ollama pull {self.model}' in your terminal to download it.")
            elif e.response.status_code in (401, 403):
                raise Exception(f"Authentication error (401/403) accessing Ollama server.\n"
                                f"Please verify if your API Key/Auth Token is correct.")
            else:
                raise Exception(f"Ollama API error: {e}")
        except Exception as e:
            raise Exception(f"Failed to translate: {str(e)}")

    def check_connection(self):
        """Verify if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                models = [model["name"] for model in response.json().get("models", [])]
                return True, models
            return False, []
        except Exception:
            return False, []

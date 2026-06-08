"""Tests for shallott.translator (OllamaClient)."""

import pytest
import responses as resp_lib

from shallott.translator import OllamaClient

BASE = "http://ollama-test:11434"

_SAMPLE_CFG = {
    "ollama": {
        "host": BASE,
        "model": "gemma3:8b-instruct-q4_K_M",
        "timeout": 10,
        "verify_ssl": False,
    }
}


def _client():
    return OllamaClient(_SAMPLE_CFG)


# ─── is_reachable ─────────────────────────────────────────────────────────────

@resp_lib.activate
def test_is_reachable_true():
    resp_lib.add(resp_lib.GET, f"{BASE}/api/tags", json={"models": []}, status=200)
    assert _client().is_reachable() is True


@resp_lib.activate
def test_is_reachable_false_on_error():
    import requests as _requests
    resp_lib.add(
        resp_lib.GET,
        f"{BASE}/api/tags",
        body=_requests.exceptions.ConnectionError("unreachable"),
    )
    assert _client().is_reachable() is False


@resp_lib.activate
def test_is_reachable_false_on_non_200():
    resp_lib.add(resp_lib.GET, f"{BASE}/api/tags", status=503)
    assert _client().is_reachable() is False


# ─── translate ────────────────────────────────────────────────────────────────

@resp_lib.activate
def test_translate_returns_content():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE}/api/chat",
        json={"message": {"role": "assistant", "content": "Bonjour le monde"}},
        status=200,
    )
    result = _client().translate("Hello world", target_language="fr")
    assert result == "Bonjour le monde"


@resp_lib.activate
def test_translate_strips_whitespace():
    resp_lib.add(
        resp_lib.POST,
        f"{BASE}/api/chat",
        json={"message": {"role": "assistant", "content": "  Hola  \n"}},
        status=200,
    )
    result = _client().translate("Hello", target_language="es")
    assert result == "Hola"


@resp_lib.activate
def test_translate_raises_on_http_error():
    resp_lib.add(resp_lib.POST, f"{BASE}/api/chat", status=500)
    with pytest.raises(Exception):
        _client().translate("test")


# ─── model / host propagation ─────────────────────────────────────────────────

def test_client_reads_model_from_config():
    assert _client().model == "gemma3:8b-instruct-q4_K_M"


def test_client_reads_host_from_config():
    assert _client().host == BASE


def test_client_strips_trailing_slash():
    cfg = {"ollama": {"host": f"{BASE}/", "model": "m", "timeout": 5, "verify_ssl": False}}
    assert OllamaClient(cfg).host == BASE

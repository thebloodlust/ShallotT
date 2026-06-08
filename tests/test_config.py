"""Tests for shallott.config"""

import json
import os
import pytest
from pathlib import Path

from shallott import config


def test_defaults_are_returned_when_no_file(tmp_path, monkeypatch):
    """No config file → fall back to built-in defaults."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SHALLOTT_CONFIG", raising=False)
    cfg = config.load()
    assert cfg["ollama"]["host"] == "http://localhost:11434"
    assert cfg["hotkeys"]["translate_clipboard"] == "<ctrl>+c+c"
    assert cfg["hotkeys"]["translate_ocr"] == "<ctrl>+<f8>"


def test_user_values_override_defaults(tmp_path, monkeypatch):
    """Values in a user config file override defaults; unset keys keep defaults."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "ollama": {"host": "http://10.0.0.5:11434"},
        "translation": {"target_language": "fr"},
    }))
    monkeypatch.delenv("SHALLOTT_CONFIG", raising=False)
    cfg = config.load(cfg_file)
    assert cfg["ollama"]["host"] == "http://10.0.0.5:11434"
    assert cfg["ollama"]["model"] == "gemma3:8b-instruct-q4_K_M"  # default kept
    assert cfg["translation"]["target_language"] == "fr"


def test_env_var_path_is_used(tmp_path, monkeypatch):
    cfg_file = tmp_path / "custom.json"
    cfg_file.write_text(json.dumps({"ollama": {"host": "http://vpn-host:11434"}}))
    monkeypatch.setenv("SHALLOTT_CONFIG", str(cfg_file))
    cfg = config.load()
    assert cfg["ollama"]["host"] == "http://vpn-host:11434"


def test_explicit_path_takes_priority_over_env(tmp_path, monkeypatch):
    env_cfg = tmp_path / "env.json"
    env_cfg.write_text(json.dumps({"ollama": {"host": "http://env-host:11434"}}))
    explicit_cfg = tmp_path / "explicit.json"
    explicit_cfg.write_text(json.dumps({"ollama": {"host": "http://explicit-host:11434"}}))
    monkeypatch.setenv("SHALLOTT_CONFIG", str(env_cfg))
    cfg = config.load(explicit_cfg)
    assert cfg["ollama"]["host"] == "http://explicit-host:11434"


def test_deep_merge_preserves_nested_defaults(tmp_path):
    cfg_file = tmp_path / "c.json"
    cfg_file.write_text(json.dumps({"ollama": {"model": "llama3:8b"}}))
    cfg = config.load(cfg_file)
    # host was not specified → keep default
    assert cfg["ollama"]["host"] == "http://localhost:11434"
    assert cfg["ollama"]["model"] == "llama3:8b"

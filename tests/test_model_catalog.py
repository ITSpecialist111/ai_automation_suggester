"""Tests for model catalog helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module(name: str):
    path = Path(__file__).resolve().parents[1] / "custom_components" / "ai_automation_suggester" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


model_catalog = load_module("model_catalog")


def test_openai_gpt_55_uses_responses_api():
    assert model_catalog.model_uses_responses_api("OpenAI", "gpt-5.5") is True
    assert model_catalog.should_send_temperature("OpenAI", "gpt-5.5") is False


def test_deprecated_google_model_warns():
    warnings = model_catalog.compatibility_warnings("Google", "gemini-2.0-flash")
    assert any("deprecated" in warning.lower() for warning in warnings)


def test_unknown_local_model_is_allowed_as_custom():
    capabilities = model_catalog.get_model_capabilities("Ollama", "my-local-model")
    assert capabilities.model == "my-local-model"
    assert capabilities.status == model_catalog.STATUS_CUSTOM
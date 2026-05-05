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


def test_google_json_schema_strips_additional_properties():
    schema = model_catalog.google_json_schema_response_format()["json_schema"]["schema"]

    def contains_key(value, target_key: str) -> bool:
        if isinstance(value, dict):
            return target_key in value or any(contains_key(item, target_key) for item in value.values())
        if isinstance(value, list):
            return any(contains_key(item, target_key) for item in value)
        return False

    assert not contains_key(schema, "additionalProperties")


def test_openai_json_schema_keeps_additional_properties():
    schema = model_catalog.json_schema_response_format()["json_schema"]["schema"]

    assert "additionalProperties" in schema


def test_github_copilot_default_model():
    assert model_catalog.get_default_model("GitHub Copilot") == "gpt-4o"


def test_github_copilot_gpt4o_sends_temperature():
    assert model_catalog.should_send_temperature("GitHub Copilot", "gpt-4o") is True


def test_github_copilot_o3_mini_omits_temperature():
    assert model_catalog.should_send_temperature("GitHub Copilot", "o3-mini") is False


def test_github_copilot_deprecated_o1_warns():
    warnings = model_catalog.compatibility_warnings("GitHub Copilot", "o1-mini")
    assert any("deprecated" in w.lower() for w in warnings)


def test_github_copilot_catalog_has_model_listing_url():
    catalog = model_catalog.get_provider_catalog("GitHub Copilot")
    assert catalog is not None
    assert catalog.model_listing_url == "https://api.githubcopilot.com/models"
    assert catalog.supports_model_listing is True
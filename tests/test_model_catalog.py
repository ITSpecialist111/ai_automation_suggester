"""Tests for model catalog helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from custom_components.ai_automation_suggester.const import DEFAULT_MODELS


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


@pytest.mark.parametrize("provider,expected", [("Google", "gemini-3.5-flash"), ("Groq", "openai/gpt-oss-120b")])
def test_provider_defaults_use_supported_models(provider, expected):
    assert DEFAULT_MODELS[provider] == expected
    assert model_catalog.get_provider_catalog(provider).default_model == expected
    assert model_catalog.get_model_capabilities(provider, expected).status == model_catalog.STATUS_STABLE


def test_google_previous_default_warns_with_replacement():
    warnings = model_catalog.compatibility_warnings("Google", "gemini-2.5-flash")
    assert any("gemini-3.5-flash" in warning for warning in warnings)


@pytest.mark.parametrize("model", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-8b-8192"])
def test_groq_retired_models_warn_with_current_replacement(model):
    warnings = model_catalog.compatibility_warnings("Groq", model)
    assert any("deprecated" in warning.lower() for warning in warnings)
    assert any("gpt-oss" in warning for warning in warnings)


def test_groq_qwen_alternative_is_marked_preview():
    capabilities = model_catalog.get_model_capabilities("Groq", "qwen/qwen3.6-27b")
    assert capabilities.status == model_catalog.STATUS_PREVIEW
    assert capabilities.supports_reasoning is True


def test_unknown_local_model_is_allowed_as_custom():
    capabilities = model_catalog.get_model_capabilities("Ollama", "my-local-model")
    assert capabilities.model == "my-local-model"
    assert capabilities.status == model_catalog.STATUS_CUSTOM


def test_openrouter_free_router_supports_structured_output():
    capabilities = model_catalog.get_model_capabilities("OpenRouter", "openrouter/free")

    assert capabilities.supports_structured_output is True
    assert capabilities.supports_json_schema is True


def test_minimax_catalog_contains_target_models():
    catalog = model_catalog.get_provider_catalog("MiniMax")

    assert catalog.default_model == "MiniMax-M3"
    assert [item.model for item in catalog.models] == ["MiniMax-M3", "MiniMax-M2.7"]
    assert model_catalog.get_model_capabilities("MiniMax", "MiniMax-M3").context_window == 1_000_000
    assert model_catalog.get_model_capabilities("MiniMax", "MiniMax-M2.7").context_window == 204_800


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


@pytest.mark.parametrize("model", ["gpt-6.1-sol", "gpt-6-luna", "gpt-6", "gpt-7.0-mini", "gpt-10", "GPT-6.1-Sol", "gpt-5.9"])
def test_future_gpt_generations_use_responses_api(model):
    capabilities = model_catalog.get_model_capabilities("OpenAI", model)

    assert model_catalog.model_uses_responses_api("OpenAI", model) is True
    assert capabilities.token_parameter == "max_output_tokens"
    assert capabilities.supports_json_schema is True
    assert model_catalog.should_send_temperature("OpenAI", model) is False


@pytest.mark.parametrize("provider", ["OpenAI Azure", "Custom OpenAI", "Generic OpenAI"])
@pytest.mark.parametrize("model", ["gpt-6.1-sol", "gpt-6-luna", "o5-mini"])
def test_future_gpt_generations_use_max_completion_tokens_on_chat_apis(provider, model):
    assert model_catalog.model_uses_responses_api(provider, model) is False
    assert model_catalog.chat_token_parameter(provider, model) == "max_completion_tokens"
    assert model_catalog.should_send_temperature(provider, model) is False


@pytest.mark.parametrize(
    "model,expected",
    [
        ("gpt-5", True),
        ("gpt-5.4-mini", True),
        ("gpt-6.1-sol", True),
        ("gpt-60", True),
        ("o1", True),
        ("o1-mini", True),
        ("o3-pro", True),
        ("o5", True),
        ("gpt-4o-mini", False),
        ("gpt-4.1", False),
        ("gpt-3.5-turbo", False),
        ("gpt-oss-120b", False),
        ("ollama", False),
        ("omni-model", False),
        ("", False),
        (None, False),
    ],
)
def test_openai_reasoning_family_detection(model, expected):
    assert model_catalog.is_openai_reasoning_family(model) is expected


def test_unknown_direct_openai_model_avoids_deprecated_max_tokens():
    assert model_catalog.model_uses_responses_api("OpenAI", "some-future-model") is False
    assert model_catalog.chat_token_parameter("OpenAI", "some-future-model") == "max_completion_tokens"
    assert model_catalog.should_send_temperature("OpenAI", "some-future-model") is True


@pytest.mark.parametrize("provider", ["OpenAI Azure", "Custom OpenAI", "Generic OpenAI", "OpenRouter"])
def test_unknown_models_on_other_providers_keep_max_tokens(provider):
    assert model_catalog.chat_token_parameter(provider, "my-custom-deployment") == "max_tokens"

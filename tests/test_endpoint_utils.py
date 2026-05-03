"""Tests for provider endpoint normalization helpers."""

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


endpoint_utils = load_module("endpoint_utils")


def test_openai_chat_endpoint_accepts_base_or_exact_url():
    assert endpoint_utils.openai_chat_endpoint("localhost:8080") == "http://localhost:8080/v1/chat/completions"
    assert endpoint_utils.openai_chat_endpoint("http://localhost:8080/v1") == "http://localhost:8080/v1/chat/completions"
    assert endpoint_utils.openai_chat_endpoint("http://localhost:8080/api") == "http://localhost:8080/api/chat/completions"
    assert (
        endpoint_utils.openai_chat_endpoint("http://localhost:8080/api/chat/completions")
        == "http://localhost:8080/api/chat/completions"
    )


def test_openai_model_endpoint_candidates_include_open_webui_shape():
    candidates = endpoint_utils.openai_model_endpoint_candidates("http://localhost:8080/api/chat/completions")

    assert "http://localhost:8080/api/models" in candidates


def test_ollama_base_url_accepts_full_url_or_host_port():
    assert endpoint_utils.ollama_base_url(base_url="http://localhost:3000/ollama") == "http://localhost:3000/ollama"
    assert (
        endpoint_utils.ollama_base_url(ip_address="localhost", port=11434, https=False)
        == "http://localhost:11434"
    )


def test_ollama_api_candidates_include_open_webui_proxy_path():
    assert endpoint_utils.ollama_api_candidates("http://localhost:3000", "api/chat") == [
        "http://localhost:3000/api/chat",
        "http://localhost:3000/ollama/api/chat",
    ]
    assert endpoint_utils.ollama_api_candidates("http://localhost:3000/ollama", "api/chat") == [
        "http://localhost:3000/ollama/api/chat"
    ]


def test_bearer_auth_headers_accepts_token_or_full_header():
    assert endpoint_utils.bearer_auth_headers(None) is None
    assert endpoint_utils.bearer_auth_headers("secret-token") == {"Authorization": "Bearer secret-token"}
    assert endpoint_utils.bearer_auth_headers("Bearer already-formatted") == {
        "Authorization": "Bearer already-formatted"
    }
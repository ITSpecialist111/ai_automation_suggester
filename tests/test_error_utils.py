"""Tests for credential-safe provider error formatting."""

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


error_utils = load_module("error_utils")


def test_sanitizer_redacts_credentials_but_preserves_household_context():
    message = (
        "Kitchen motion request failed; Authorization: Bearer sk-secret-value; "
        "https://example.test/v1?api_key=google-secret&room=Kitchen"
    )

    sanitized = error_utils.sanitize_provider_error(message)

    assert "Kitchen" in sanitized
    assert "motion" in sanitized
    assert "sk-secret-value" not in sanitized
    assert "google-secret" not in sanitized
    assert sanitized.count("[redacted]") == 2


def test_sanitizer_bounds_long_errors():
    sanitized = error_utils.sanitize_provider_error("x" * 200, limit=80)

    assert len(sanitized) <= 80
    assert sanitized.endswith("(truncated)")

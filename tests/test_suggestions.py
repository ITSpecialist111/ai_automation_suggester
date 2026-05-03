"""Tests for suggestion response parsing."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path


def load_module(name: str):
    path = Path(__file__).resolve().parents[1] / "custom_components" / "ai_automation_suggester" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


suggestions = load_module("suggestions")


def test_parse_structured_json_suggestion():
    raw = """
    {
      "suggestions": [
        {
          "title": "Turn on hall light",
          "description": "Turns on the hall light when motion is detected.",
          "yaml": "alias: Hall motion light\\ntrigger: []\\naction: []",
          "entities_used": ["binary_sensor.hall_motion", "light.hall"]
        }
      ]
    }
    """

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="OpenAI",
        model="gpt-5.5",
        created_at=datetime(2026, 5, 3, 12, 0, 0),
        entities_processed=["binary_sensor.hall_motion"],
    )

    assert parsed[0]["title"] == "Turn on hall light"
    assert parsed[0]["yamlCode"].startswith("alias: Hall")
    assert parsed[0]["provider"] == "OpenAI"


def test_parse_fenced_yaml_fallback():
    raw = """Use this automation.

```yaml
alias: Kitchen reminder
trigger: []
action: []
```
"""

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="Anthropic",
        model="claude-sonnet-4-6",
        created_at=datetime(2026, 5, 3, 12, 0, 0),
        entities_processed=["sensor.kitchen"],
    )

    assert parsed[0]["description"].startswith("Use this automation")
    assert "Kitchen reminder" in parsed[0]["yamlCode"]


def test_length_finish_reason_adds_warning():
    parsed = suggestions.parse_suggestion_response(
        "No YAML this time",
        provider="OpenRouter",
        model="openai/gpt-5.4-mini",
        created_at=datetime(2026, 5, 3, 12, 0, 0),
        entities_processed=[],
        response_metadata={"finish_reason": "length"},
    )

    assert any("truncated" in warning for warning in parsed[0]["warnings"])
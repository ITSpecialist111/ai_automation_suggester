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


def test_requesty_length_finish_reason_adds_warning():
    parsed = suggestions.parse_suggestion_response(
        "No YAML this time",
        provider="Requesty",
        model="openai/gpt-4o-mini",
        created_at=datetime(2026, 5, 3, 12, 0, 0),
        entities_processed=[],
        response_metadata={"finish_reason": "length"},
    )

    assert parsed[0]["provider"] == "Requesty"
    assert any("truncated" in warning for warning in parsed[0]["warnings"])


def test_parse_malformed_json_yaml_blocks_from_provider():
    raw = '''
{
    "suggestions": [
        {
            "title": "Laundry Drying Alerts Based on Weather",
            "description": "Notify when the laundry drying index is favorable.",
            "yaml": ""
                alias: "Notify when laundry drying conditions are optimal"
                trigger:
                    - platform: numeric_state
                        entity_id: sensor.laundry_drying_index
                        above: 70
                action:
                    - service: notify.notify
                        data:
                            message: "Optimal laundry drying conditions now!"
            "",
            "entities_used": [
                "sensor.laundry_drying_index",
                "sun.sun"
            ],
            "automation_ids_used": [],
            "confidence": 0.6,
            "warnings": [
                "Adjust the threshold based on your local climate."
            ]
        }
    ]
}
'''

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="Mistral AI",
        model="mistral-medium",
        created_at=datetime(2026, 5, 3, 12, 0, 0),
        entities_processed=["sensor.laundry_drying_index"],
        response_metadata={"finish_reason": "length"},
    )

    assert parsed[0]["title"] == "Laundry Drying Alerts Based on Weather"
    assert parsed[0]["description"] == "Notify when the laundry drying index is favorable."
    assert parsed[0]["yamlCode"].startswith("alias:")
    assert "sensor.laundry_drying_index" in parsed[0]["entities_used"]
    assert not any(warning == "No automation YAML was returned." for warning in parsed[0]["warnings"])
    assert any("malformed JSON" in warning for warning in parsed[0]["warnings"])


def test_notification_formats_parser_repair_warning_for_users():
    message = suggestions.format_suggestion_notification(
        {
            "title": "Recovered suggestion",
            "description": "A recovered suggestion.",
            "warnings": [suggestions.PARSE_REPAIR_WARNING],
        }
    )

    assert "malformed JSON" not in message
    assert "needed formatting repair" in message


def test_script_ids_used_in_structured_json():
    raw = """
    {
      "suggestions": [
        {
          "title": "Test script suggestion",
          "description": "A suggestion referencing scripts.",
          "yaml": "alias: test\\ntrigger: []\\naction: []",
          "entities_used": ["light.living_room"],
          "automation_ids_used": ["automation.morning"],
          "script_ids_used": ["script.welcome", "script.goodbye"]
        }
      ]
    }
    """

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="OpenAI",
        model="gpt-5.5",
        created_at=datetime(2026, 5, 3, 12, 0, 0),
        entities_processed=["light.living_room"],
    )

    assert parsed[0]["script_ids_used"] == ["script.welcome", "script.goodbye"]
    assert parsed[0]["automation_ids_used"] == ["automation.morning"]


def test_script_ids_used_in_malformed_json():
    raw = '''
{
    "suggestions": [
        {
            "title": "Weather script automation",
            "description": "Check weather and run script.",
            "yaml": ""
                alias: "Weather check"
                trigger: []
                action: []
            "",
            "entities_used": ["sensor.temperature"],
            "automation_ids_used": ["automation.weather_alert"],
            "script_ids_used": ["script.weather_check"],
            "confidence": 0.8,
            "warnings": []
        }
    ]
}
'''

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="Mistral AI",
        model="mistral-medium",
        created_at=datetime(2026, 5, 3, 12, 0, 0),
        entities_processed=["sensor.temperature"],
    )

    assert parsed[0]["script_ids_used"] == ["script.weather_check"]
    assert parsed[0]["automation_ids_used"] == ["automation.weather_alert"]


def test_script_ids_used_defaults_to_empty():
    raw = """
    {
      "suggestions": [
        {
          "title": "Simple suggestion",
          "description": "No script references.",
          "yaml": "alias: simple\\ntrigger: []\\naction: []",
          "entities_used": []
        }
      ]
    }
    """

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="OpenAI",
        model="gpt-5.5",
        created_at=datetime(2026, 5, 3, 12, 0, 0),
        entities_processed=[],
    )

    assert parsed[0]["script_ids_used"] == []


def test_unparseable_structured_payload_does_not_become_notification_body():
    raw = '{"suggestions": [ this is not recoverable ]}'

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="Mistral AI",
        model="mistral-medium",
        created_at=datetime(2026, 5, 3, 12, 0, 0),
        entities_processed=[],
    )

    assert not parsed[0]["description"].startswith("{")
    assert "could not be parsed" in parsed[0]["description"]


def test_model_cannot_set_store_id_or_review_status():
    raw = """
    {
        "id": "model-controlled-id",
        "status": "accepted",
        "title": "Server-owned fields",
        "description": "The model must not control workflow fields.",
        "yaml": "alias: Safe fields\\ntriggers: []\\nactions: []"
    }
    """

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="OpenAI",
        model="gpt-5.5",
        created_at=datetime(2026, 7, 11, 12, 0, 0),
        entities_processed=[],
    )

    assert parsed[0]["id"] != "model-controlled-id"
    assert parsed[0]["status"] == "new"


def test_yaml_references_are_extracted_and_unsampled_entities_warn():
    raw = """
    {
        "title": "Motion light",
        "description": "Turn on a light after motion.",
        "yaml": "alias: Motion light\\ntriggers:\\n  - trigger: state\\n    entity_id: binary_sensor.hall_motion\\nactions:\\n  - action: light.turn_on\\n    target:\\n      entity_id: light.hall",
        "entities_used": []
    }
    """

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="OpenAI",
        model="gpt-5.5",
        created_at=datetime(2026, 7, 11, 12, 0, 0),
        entities_processed=["binary_sensor.hall_motion"],
    )

    assert parsed[0]["yaml_entities_used"] == ["binary_sensor.hall_motion", "light.hall"]
    assert parsed[0]["services_used"] == ["light.turn_on"]
    assert any("light.hall" in warning and "sampled" in warning for warning in parsed[0]["warnings"])


def test_invalid_confidence_is_ignored_with_warning():
    raw = """
    {
        "title": "Invalid confidence",
        "description": "Confidence must be between zero and one.",
        "yaml": "alias: Invalid confidence\\ntriggers: []\\nactions: []",
        "confidence": 4.2
    }
    """

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="OpenAI",
        model="gpt-5.5",
        created_at=datetime(2026, 7, 11, 12, 0, 0),
        entities_processed=[],
    )

    assert parsed[0]["confidence"] is None
    assert any("confidence outside" in warning for warning in parsed[0]["warnings"])
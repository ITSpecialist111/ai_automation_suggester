"""Tests for suggestion response parsing."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml


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


@pytest.mark.parametrize("response_format", ["fenced_yaml", "plain_json", "structured_json", "fenced_json", "malformed_json"])
def test_yaml_fences_preserve_newlines_and_four_space_indentation(response_format):
    yaml_code = """alias: Climate helper
triggers:
    - trigger: state
      entity_id: input_boolean.climate
      to: 'on'
actions:
    - action: button.press
      target:
          entity_id: button.air1_power_on"""
    fenced_yaml = f"```yaml\n{yaml_code}\n```"
    payload = json.dumps({"suggestions": [{
        "title": "Climate helper",
        "description": "Preserve YAML formatting.",
        "yaml": yaml_code if response_format == "plain_json" else fenced_yaml,
    }]})
    if response_format == "fenced_yaml":
        raw = fenced_yaml
    elif response_format == "fenced_json":
        raw = f"```json\n{payload}\n```"
    elif response_format == "malformed_json":
        raw = payload[:-1] + ",}"
    else:
        raw = payload

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="Google",
        model="gemini-3.5-flash",
        created_at=datetime(2026, 9, 5, 12, 0, 0),
        entities_processed=["input_boolean.climate", "button.air1_power_on"],
    )

    assert parsed[0]["yamlCode"] == yaml_code
    assert parsed[0]["services_used"] == ["button.press"]
    assert not any("could not be parsed" in warning for warning in parsed[0]["warnings"])


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

@pytest.mark.parametrize(
    "metadata",
    [
        {"finish_reason": "MAX_TOKENS"},
        {"stop_reason": "max_tokens"},
        {"done_reason": "length"},
        {"finish_reason": "length", "native_finish_reason": "MAX_TOKENS"},
        {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}},
    ],
)
def test_provider_output_limit_reasons_add_truncation_warning(metadata):
    parsed = suggestions.parse_suggestion_response(
        "No YAML this time",
        provider="Google",
        model="gemini-3.5-flash",
        created_at=datetime(2026, 9, 26, 12, 0, 0),
        entities_processed=[],
        response_metadata=metadata,
    )

    assert suggestions.TRUNCATION_WARNING in parsed[0]["warnings"]


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"finish_reason": "STOP"},
        {"stop_reason": "end_turn"},
        {"done_reason": "stop"},
        {"status": "incomplete", "incomplete_details": {"reason": "content_filter"}},
    ],
)
def test_completed_responses_do_not_add_truncation_warning(metadata):
    parsed = suggestions.parse_suggestion_response(
        "No YAML this time",
        provider="Anthropic",
        model="claude-sonnet-4-6",
        created_at=datetime(2026, 9, 26, 12, 0, 0),
        entities_processed=[],
        response_metadata=metadata,
    )

    assert suggestions.TRUNCATION_WARNING not in parsed[0]["warnings"]


def test_truncated_structured_output_explains_output_limit():
    parsed = suggestions.parse_suggestion_response(
        '{"suggestions": [{"title": "Turn on the hall li',
        provider="Google",
        model="gemini-3.5-flash",
        created_at=datetime(2026, 9, 26, 12, 0, 0),
        entities_processed=[],
        response_metadata={"finish_reason": "MAX_TOKENS"},
    )

    assert parsed[0]["description"] == suggestions.TRUNCATED_STRUCTURED_OUTPUT_DESCRIPTION
    assert "No automation YAML was returned." in parsed[0]["warnings"]
    message = suggestions.format_suggestion_notification(parsed[0])
    assert "Max Output Tokens" in message
    assert "may have been cut off" in message


def test_yaml_escapes_copied_into_json_parse_without_repair_warning():
    # Gemini can copy a YAML double-quoted escape such as \xED into a JSON
    # string. JSON rejects that escape, but the YAML text is still intact.
    raw = (
        '{"suggestions": [{"title": "Klima", "description": "Pomocn\u00edk.", '
        '"yaml": "alias: \\"Pomocn\\xEDk klima vyp\\"\\ntrigger:\\n  - platform: state\\n'
        "    entity_id: input_boolean.klimatizace\\n    to: \\'off\\'\\naction: []\"}]}"
    )
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="Google",
        model="gemini-3.5-flash",
        created_at=datetime(2026, 9, 26, 12, 0, 0),
        entities_processed=["input_boolean.klimatizace"],
    )

    assert suggestions.PARSE_REPAIR_WARNING not in parsed[0]["warnings"]
    assert "\n  - platform: state\n    entity_id: input_boolean.klimatizace" in parsed[0]["yamlCode"]
    automation = yaml.safe_load(parsed[0]["yamlCode"])
    assert automation["alias"] == "Pomocn\u00edk klima vyp"
    assert automation["trigger"][0]["to"] == "off"
    assert not any("could not be parsed" in warning for warning in parsed[0]["warnings"])


def test_literal_newlines_inside_json_strings_parse_without_repair_warning():
    yaml_code = "alias: Hall light\ntriggers:\n    - trigger: state\n      entity_id: binary_sensor.hall\nactions: []"
    raw = '{"suggestions": [{"title": "Hall", "description": "Line one\nLine two", "yaml": "' + yaml_code + '"}]}'

    parsed = suggestions.parse_suggestion_response(
        raw,
        provider="Ollama",
        model="gemma4:12b",
        created_at=datetime(2026, 9, 26, 12, 0, 0),
        entities_processed=["binary_sensor.hall"],
    )

    assert parsed[0]["yamlCode"] == yaml_code
    assert parsed[0]["description"] == "Line one\nLine two"
    assert suggestions.PARSE_REPAIR_WARNING not in parsed[0]["warnings"]


def test_json_escape_repair_only_changes_invalid_escapes():
    text = r'"keep \\x \" \/ \n \u00e9, repair \xED \u12 \' \$"'

    assert suggestions._repair_json_escapes(text) == r'"keep \\x \" \/ \n \u00e9, repair \\xED \\u12 ' + "'" + r' \\$"'

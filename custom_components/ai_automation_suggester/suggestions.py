"""Suggestion parsing and formatting helpers."""

from __future__ import annotations

import json
import re
import textwrap
from datetime import datetime
from typing import Any
from uuid import uuid4

import yaml

YAML_RE = re.compile(r"```(?:yaml|yml)\s*([\s\S]+?)\s*```", flags=re.IGNORECASE)
JSON_RE = re.compile(r"```json\s*([\s\S]+?)\s*```", flags=re.IGNORECASE)
STRING_FIELDS_AFTER_YAML = "entities_used|automation_ids_used|confidence|warnings"
PARSE_REPAIR_WARNING = "The provider returned malformed JSON; suggestions were parsed best-effort."


STRUCTURED_OUTPUT_INSTRUCTIONS = """
Return a JSON object with this shape and no surrounding Markdown:
{
  "suggestions": [
    {
      "title": "Short automation title",
      "description": "Why this automation is useful and how it works",
      "yaml": "Home Assistant automation YAML",
      "entities_used": ["domain.entity_id"],
      "automation_ids_used": [],
      "script_ids_used": [],
      "confidence": 0.0,
      "warnings": []
    }
  ]
}
Only reference entity_ids present in the prompt. Keep suggestions review-only;
do not claim that automations have been created or changed.
"""


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _try_json_loads(raw_response: str) -> dict | list | None:
    """Try to decode model output as JSON, including fenced JSON."""

    text = raw_response.strip()
    fenced = JSON_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _decode_jsonish_string(value: str) -> str:
    """Decode a JSON string fragment when possible."""

    try:
        return str(json.loads(f'"{value}"'))
    except json.JSONDecodeError:
        return value.replace('\\"', '"').replace("\\n", "\n").strip()


def _extract_string_field(segment: str, field: str) -> str | None:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*"((?:\\.|[^"\\])*)"', segment)
    return _decode_jsonish_string(match.group(1)).strip() if match else None


def _extract_array_field(segment: str, field: str) -> list:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*(\[[\s\S]*?\])', segment)
    if not match:
        return []
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _extract_number_field(segment: str, field: str) -> float | None:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*(-?\d+(?:\.\d+)?)', segment)
    return float(match.group(1)) if match else None


def _extract_yaml_field(segment: str) -> str | None:
    malformed = re.search(
        rf'"yaml"\s*:\s*""\s*\r?\n(?P<yaml>[\s\S]*?)\r?\n\s*""\s*,?\s*(?=\r?\n\s*"(?:{STRING_FIELDS_AFTER_YAML})"|\r?\n\s*\}})',
        segment,
    )
    if malformed:
        return textwrap.dedent(malformed.group("yaml")).strip() or None

    valid = re.search(r'"yaml"\s*:\s*"((?:\\.|[^"\\])*)"', segment)
    if valid:
        return _decode_jsonish_string(valid.group(1)).strip() or None
    return None


def _try_loose_structured_items(raw_response: str) -> list[dict[str, Any]]:
    """Extract suggestions from malformed JSON-like provider responses."""

    if '"suggestions"' not in raw_response and '"title"' not in raw_response:
        return []

    title_matches = list(re.finditer(r'"title"\s*:', raw_response))
    items: list[dict[str, Any]] = []
    for index, match in enumerate(title_matches):
        start = raw_response.rfind("{", 0, match.start())
        if start == -1:
            start = match.start()
        end = title_matches[index + 1].start() if index + 1 < len(title_matches) else len(raw_response)
        segment = raw_response[start:end]

        title = _extract_string_field(segment, "title")
        description = _extract_string_field(segment, "description")
        yaml_code = _extract_yaml_field(segment)
        if not any((title, description, yaml_code)):
            continue

        item: dict[str, Any] = {
            "title": title,
            "description": description,
            "yaml": yaml_code,
            "entities_used": _extract_array_field(segment, "entities_used"),
            "automation_ids_used": _extract_array_field(segment, "automation_ids_used"),
            "script_ids_used": _extract_array_field(segment, "script_ids_used"),
            "warnings": _extract_array_field(segment, "warnings"),
        }
        confidence = _extract_number_field(segment, "confidence")
        if confidence is not None:
            item["confidence"] = confidence
        items.append(item)

    return items


def _validate_yaml(yaml_code: str | None) -> list[str]:
    warnings: list[str] = []
    if not yaml_code:
        warnings.append("No automation YAML was returned.")
        return warnings
    try:
        parsed = yaml.safe_load(yaml_code)
    except yaml.YAMLError as err:
        warnings.append(f"Returned YAML could not be parsed: {err}")
        return warnings
    if parsed is None:
        warnings.append("Returned YAML was empty after parsing.")
    elif not isinstance(parsed, (dict, list)):
        warnings.append("Returned YAML parsed to an unexpected scalar value.")
    return warnings


def _normalise_suggestion(
    item: dict[str, Any],
    *,
    provider: str,
    model: str,
    created_at: datetime,
    entities_processed: list[str],
    inherited_warnings: list[str],
    response_metadata: dict[str, Any],
) -> dict[str, Any]:
    title = str(item.get("title") or "AI automation suggestion").strip()
    description = str(item.get("description") or item.get("shortDescription") or "").strip()
    yaml_code = item.get("yaml") or item.get("yaml_block") or item.get("yamlCode")
    yaml_code = str(yaml_code).strip() if yaml_code else None
    warnings = [str(w) for w in inherited_warnings]
    warnings.extend(str(w) for w in _as_list(item.get("warnings")))
    warnings.extend(_validate_yaml(yaml_code))

    finish_reason = response_metadata.get("finish_reason")
    if finish_reason in {"length", "max_tokens"}:
        warnings.append("The provider reported a length finish reason; the suggestion may be truncated.")
    if response_metadata.get("status") == "incomplete":
        warnings.append("The provider returned an incomplete response.")

    suggestion_id = str(item.get("id") or uuid4())
    return {
        "id": suggestion_id,
        "title": title,
        "shortDescription": description[:180] if description else title,
        "detailedDescription": description,
        "description": description,
        "yamlCode": yaml_code,
        "yaml_block": yaml_code,
        "provider": provider,
        "model": model,
        "status": str(item.get("status") or "new"),
        "created_at": created_at.isoformat(),
        "entities_used": [str(e) for e in _as_list(item.get("entities_used"))],
        "automation_ids_used": [str(a) for a in _as_list(item.get("automation_ids_used"))],
        "script_ids_used": [str(s) for s in _as_list(item.get("script_ids_used"))],
        "entities_processed": entities_processed,
        "confidence": item.get("confidence"),
        "warnings": warnings,
        "response_metadata": response_metadata,
    }


def parse_suggestion_response(
    raw_response: str,
    *,
    provider: str,
    model: str,
    created_at: datetime,
    entities_processed: list[str],
    inherited_warnings: list[str] | None = None,
    response_metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Parse a provider response into stored suggestion dictionaries."""

    inherited = inherited_warnings or []
    metadata = response_metadata or {}
    structured = _try_json_loads(raw_response)
    if isinstance(structured, dict):
        raw_items = structured.get("suggestions")
        if raw_items is None:
            raw_items = [structured]
        elif isinstance(raw_items, dict):
            raw_items = [raw_items]
        elif not isinstance(raw_items, list):
            raw_items = []
        suggestions = [
            _normalise_suggestion(
                item if isinstance(item, dict) else {"description": str(item)},
                provider=provider,
                model=model,
                created_at=created_at,
                entities_processed=entities_processed,
                inherited_warnings=inherited,
                response_metadata=metadata,
            )
            for item in raw_items
        ]
        if suggestions:
            return suggestions
    elif isinstance(structured, list):
        suggestions = [
            _normalise_suggestion(
                item if isinstance(item, dict) else {"description": str(item)},
                provider=provider,
                model=model,
                created_at=created_at,
                entities_processed=entities_processed,
                inherited_warnings=inherited,
                response_metadata=metadata,
            )
            for item in structured
        ]
        if suggestions:
            return suggestions

    loose_items = _try_loose_structured_items(raw_response)
    if loose_items:
        loose_warnings = [*inherited, PARSE_REPAIR_WARNING]
        return [
            _normalise_suggestion(
                item,
                provider=provider,
                model=model,
                created_at=created_at,
                entities_processed=entities_processed,
                inherited_warnings=loose_warnings,
                response_metadata=metadata,
            )
            for item in loose_items
        ]

    yaml_match = YAML_RE.search(raw_response)
    yaml_code = yaml_match.group(1).strip() if yaml_match else None
    if yaml_match:
        description = YAML_RE.sub("", raw_response).strip()
    elif raw_response.lstrip().startswith(("{", "[")) or '"suggestions"' in raw_response:
        description = "The provider returned structured output that could not be parsed. Try regenerating with a lower entity limit or a newer model."
    else:
        description = raw_response.strip()
    return [
        _normalise_suggestion(
            {
                "title": "AI automation suggestion",
                "description": description,
                "yaml": yaml_code,
            },
            provider=provider,
            model=model,
            created_at=created_at,
            entities_processed=entities_processed,
            inherited_warnings=inherited,
            response_metadata=metadata,
        )
    ]


def format_suggestion_notification(suggestion: dict[str, Any]) -> str:
    """Render one suggestion for a Home Assistant notification."""

    parts = [f"## {suggestion.get('title', 'AI automation suggestion')}"]
    description = suggestion.get("description")
    if description:
        parts.append(str(description))
    yaml_code = suggestion.get("yamlCode") or suggestion.get("yaml_block")
    if yaml_code:
        parts.append("```yaml\n" + str(yaml_code).strip() + "\n```")
    warnings = suggestion.get("warnings") or []
    if warnings:
        parts.append("Warnings:\n" + "\n".join(f"- {_format_notification_warning(warning)}" for warning in warnings))
    return "\n\n".join(parts)


def _format_notification_warning(warning: Any) -> str:
    """Return a concise user-facing warning for notifications."""

    text = str(warning)
    if text == PARSE_REPAIR_WARNING:
        return "Provider response needed formatting repair before display. Review the YAML before using it."
    if text == "The provider reported a length finish reason; the suggestion may be truncated.":
        return "The AI response may have been cut off. Review the YAML before using it."
    return text
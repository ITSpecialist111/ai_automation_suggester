"""Suggestion parsing and formatting helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

import yaml

YAML_RE = re.compile(r"```(?:yaml|yml)\s*([\s\S]+?)\s*```", flags=re.IGNORECASE)
JSON_RE = re.compile(r"```json\s*([\s\S]+?)\s*```", flags=re.IGNORECASE)


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

    yaml_match = YAML_RE.search(raw_response)
    yaml_code = yaml_match.group(1).strip() if yaml_match else None
    description = YAML_RE.sub("", raw_response).strip() if yaml_match else raw_response.strip()
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
        parts.append("Warnings:\n" + "\n".join(f"- {warning}" for warning in warnings))
    return "\n\n".join(parts)
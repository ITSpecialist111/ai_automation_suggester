"""Credential-safe diagnostic helpers."""

from __future__ import annotations

import re
from typing import Any

ERROR_TEXT_LIMIT = 1000
_SENSITIVE_ERROR_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"(?i)([?&](?:api[_-]?key|key|token|access_token)=)[^&\s]+"),
    re.compile(r"(?i)([\"']?(?:api[_-]?key|token|password|client_secret)[\"']?\s*[:=]\s*[\"']?)[^,\s\"'&}]+"),
)


def sanitize_provider_error(error: Any, limit: int = ERROR_TEXT_LIMIT) -> str:
    """Return a bounded error message with authentication material removed.

    Household context is intentionally preserved. Only authentication material
    and secret-bearing query parameters are redacted from diagnostics.
    """

    text = " ".join(str(error).split())
    for pattern in _SENSITIVE_ERROR_PATTERNS:
        text = pattern.sub(r"\1[redacted]", text)
    if len(text) > limit:
        return f"{text[: limit - 14].rstrip()}… (truncated)"
    return text

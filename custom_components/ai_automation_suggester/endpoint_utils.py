"""Endpoint normalization helpers for provider setup and requests."""

from __future__ import annotations

import re


def ensure_http_url(value: str | None, *, default_scheme: str = "http") -> str:
    """Return a stripped HTTP(S) URL, adding a scheme when one is omitted."""

    endpoint = str(value or "").strip().rstrip("/")
    if not endpoint:
        return ""
    if re.match(r"^https?://", endpoint):
        return endpoint
    return f"{default_scheme}://{endpoint}"


def openai_chat_endpoint(endpoint: str | None) -> str:
    """Normalize an OpenAI-compatible endpoint to a chat completions URL."""

    base = ensure_http_url(endpoint)
    if not base:
        return ""
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/api"):
        return f"{base}/chat/completions"
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def openai_model_endpoint_candidates(endpoint: str | None) -> list[str]:
    """Return likely model-listing endpoints for OpenAI-compatible servers."""

    base = ensure_http_url(endpoint)
    if not base:
        return []
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]

    candidates: list[str]
    if base.endswith("/api"):
        candidates = [f"{base}/models", f"{base}/v1/models"]
    elif base.endswith("/v1"):
        candidates = [f"{base}/models"]
    else:
        candidates = [f"{base}/v1/models", f"{base}/models", f"{base}/api/models"]
    return _dedupe(candidates)


def ollama_base_url(
    *,
    base_url: str | None = None,
    ip_address: str | None = None,
    port: int | str | None = None,
    https: bool = False,
) -> str:
    """Build an Ollama-compatible base URL from either a full URL or host/port fields."""

    if base_url:
        return ensure_http_url(base_url)
    if not ip_address:
        return ""
    host = str(ip_address).strip().rstrip("/")
    if re.match(r"^https?://", host):
        return host
    proto = "https" if https else "http"
    return f"{proto}://{host}:{port or 11434}"


def ollama_api_candidates(base_url: str, api_path: str) -> list[str]:
    """Return likely Ollama API paths for native Ollama and Open WebUI proxies."""

    base = ensure_http_url(base_url)
    if not base:
        return []
    path = api_path.strip("/")
    if base.endswith(f"/{path}"):
        return [base]
    if base.endswith("/api") and path.startswith("api/"):
        return [f"{base}/{path.split('/', 1)[1]}"]
    candidates = [f"{base}/{path}"]
    if not base.endswith("/ollama"):
        candidates.append(f"{base}/ollama/{path}")
    return _dedupe(candidates)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped
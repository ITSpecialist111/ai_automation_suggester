"""Static model capability metadata for AI Automation Suggester.

The catalog is intentionally conservative. Providers still allow custom model
names, but known metadata lets the integration choose safer request parameters
and warn users about stale defaults, preview models, and deprecated IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

STATUS_STABLE = "stable"
STATUS_PREVIEW = "preview"
STATUS_DEPRECATED = "deprecated"
STATUS_CUSTOM = "custom"


@dataclass(frozen=True)
class ModelCapabilities:
    """Capabilities for a specific model or model family."""

    model: str
    label: str = ""
    endpoint_family: str = "chat"
    context_window: int | None = None
    max_output_tokens: int | None = None
    token_parameter: str = "max_tokens"
    supports_structured_output: bool = False
    supports_json_schema: bool = False
    supports_reasoning: bool = False
    omit_temperature: bool = False
    status: str = STATUS_STABLE
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProviderCatalog:
    """Default model and known capabilities for a provider."""

    provider: str
    default_model: str
    models: tuple[ModelCapabilities, ...]
    supports_model_listing: bool = False
    model_listing_url: str | None = None


SUGGESTION_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "yaml": {"type": "string"},
                    "entities_used": {"type": "array", "items": {"type": "string"}},
                    "automation_ids_used": {"type": "array", "items": {"type": "string"}},
                    "script_ids_used": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "description", "yaml"],
                "additionalProperties": True,
            },
        }
    },
    "required": ["suggestions"],
    "additionalProperties": True,
}


OPENAI_MODELS = (
    ModelCapabilities(
        "gpt-5.5",
        "GPT-5.5",
        endpoint_family="responses",
        token_parameter="max_output_tokens",
        supports_structured_output=True,
        supports_json_schema=True,
        supports_reasoning=True,
        omit_temperature=True,
        notes=("Use the OpenAI Responses API.",),
    ),
    ModelCapabilities(
        "gpt-5.5-pro",
        "GPT-5.5 Pro",
        endpoint_family="responses",
        token_parameter="max_output_tokens",
        supports_structured_output=True,
        supports_json_schema=True,
        supports_reasoning=True,
        omit_temperature=True,
        notes=("Highest-intelligence OpenAI option; expect higher latency and cost.",),
    ),
    ModelCapabilities(
        "gpt-5.4-mini",
        "GPT-5.4 Mini",
        endpoint_family="responses",
        token_parameter="max_output_tokens",
        supports_structured_output=True,
        supports_json_schema=True,
        supports_reasoning=True,
        omit_temperature=True,
    ),
    ModelCapabilities(
        "gpt-5.4",
        "GPT-5.4",
        endpoint_family="responses",
        token_parameter="max_output_tokens",
        supports_structured_output=True,
        supports_json_schema=True,
        supports_reasoning=True,
        omit_temperature=True,
    ),
    ModelCapabilities(
        "gpt-4o-mini",
        "GPT-4o Mini",
        token_parameter="max_completion_tokens",
        supports_structured_output=True,
        supports_json_schema=True,
    ),
    ModelCapabilities(
        "gpt-4.1-mini",
        "GPT-4.1 Mini",
        token_parameter="max_completion_tokens",
        supports_structured_output=True,
        supports_json_schema=True,
    ),
    ModelCapabilities(
        "o3",
        "o3",
        token_parameter="max_completion_tokens",
        supports_reasoning=True,
        omit_temperature=True,
    ),
    ModelCapabilities(
        "o4-mini",
        "o4 Mini",
        token_parameter="max_completion_tokens",
        supports_reasoning=True,
        omit_temperature=True,
    ),
)


PROVIDER_CATALOGS: dict[str, ProviderCatalog] = {
    "OpenAI": ProviderCatalog(
        "OpenAI",
        "gpt-5.4-mini",
        OPENAI_MODELS,
        True,
        "https://api.openai.com/v1/models",
    ),
    "OpenAI Azure": ProviderCatalog(
        "OpenAI Azure",
        "gpt-5.4-mini",
        OPENAI_MODELS,
    ),
    "Anthropic": ProviderCatalog(
        "Anthropic",
        "claude-sonnet-4-6",
        (
            ModelCapabilities(
                "claude-opus-4-7",
                "Claude Opus 4.7",
                token_parameter="max_tokens",
                supports_reasoning=True,
                notes=("Use adaptive thinking; manual budget_tokens is not accepted.",),
            ),
            ModelCapabilities(
                "claude-sonnet-4-6",
                "Claude Sonnet 4.6",
                token_parameter="max_tokens",
                supports_reasoning=True,
                notes=("Adaptive thinking is recommended for reasoning-heavy requests.",),
            ),
            ModelCapabilities("claude-haiku-4-5", "Claude Haiku 4.5"),
            ModelCapabilities(
                "claude-3-7-sonnet-latest",
                "Claude 3.7 Sonnet Latest",
                status=STATUS_DEPRECATED,
                notes=("Prefer Claude Sonnet 4.6 for new configurations.",),
            ),
        ),
        True,
        "https://api.anthropic.com/v1/models",
    ),
    "Google": ProviderCatalog(
        "Google",
        "gemini-2.5-flash",
        (
            ModelCapabilities(
                "gemini-2.5-flash",
                "Gemini 2.5 Flash",
                supports_structured_output=True,
                supports_json_schema=True,
            ),
            ModelCapabilities(
                "gemini-2.5-pro",
                "Gemini 2.5 Pro",
                supports_structured_output=True,
                supports_json_schema=True,
            ),
            ModelCapabilities(
                "gemini-3-flash-preview",
                "Gemini 3 Flash Preview",
                supports_structured_output=True,
                supports_json_schema=True,
                status=STATUS_PREVIEW,
            ),
            ModelCapabilities(
                "gemini-3.1-pro-preview",
                "Gemini 3.1 Pro Preview",
                supports_structured_output=True,
                supports_json_schema=True,
                status=STATUS_PREVIEW,
            ),
            ModelCapabilities(
                "gemini-2.0-flash",
                "Gemini 2.0 Flash",
                supports_structured_output=True,
                supports_json_schema=True,
                status=STATUS_DEPRECATED,
                notes=("Gemini 2.0 Flash is deprecated in current Gemini docs.",),
            ),
        ),
        True,
        "https://generativelanguage.googleapis.com/v1beta/models",
    ),
    "Groq": ProviderCatalog(
        "Groq",
        "llama-3.3-70b-versatile",
        (
            ModelCapabilities("llama-3.3-70b-versatile", "Llama 3.3 70B Versatile"),
            ModelCapabilities("llama-3.1-8b-instant", "Llama 3.1 8B Instant"),
            ModelCapabilities("openai/gpt-oss-120b", "GPT OSS 120B"),
            ModelCapabilities("openai/gpt-oss-20b", "GPT OSS 20B"),
            ModelCapabilities(
                "llama3-8b-8192",
                "Llama 3 8B 8192",
                status=STATUS_DEPRECATED,
                notes=("Use llama-3.1-8b-instant or llama-3.3-70b-versatile.",),
            ),
        ),
        True,
        "https://api.groq.com/openai/v1/models",
    ),
    "LocalAI": ProviderCatalog("LocalAI", "llama3", (), True),
    "Ollama": ProviderCatalog("Ollama", "llama3.1", (), True),
    "Custom OpenAI": ProviderCatalog("Custom OpenAI", "gpt-4o-mini", OPENAI_MODELS, True),
    "Generic OpenAI": ProviderCatalog("Generic OpenAI", "gpt-4o-mini", OPENAI_MODELS, True),
    "Mistral AI": ProviderCatalog(
        "Mistral AI",
        "mistral-small-latest",
        (
            ModelCapabilities(
                "mistral-small-latest",
                "Mistral Small Latest",
                supports_structured_output=True,
                supports_json_schema=True,
            ),
            ModelCapabilities(
                "mistral-medium-latest",
                "Mistral Medium Latest",
                supports_structured_output=True,
                supports_json_schema=True,
            ),
            ModelCapabilities(
                "mistral-large-latest",
                "Mistral Large Latest",
                supports_structured_output=True,
                supports_json_schema=True,
            ),
            ModelCapabilities(
                "mistral-medium",
                "Mistral Medium",
                status=STATUS_DEPRECATED,
                notes=("Prefer current -latest aliases or published dated IDs.",),
            ),
        ),
        True,
        "https://api.mistral.ai/v1/models",
    ),
    "Perplexity AI": ProviderCatalog(
        "Perplexity AI",
        "sonar",
        (
            ModelCapabilities("sonar", "Sonar", supports_structured_output=True, supports_json_schema=True),
            ModelCapabilities(
                "sonar-pro",
                "Sonar Pro",
                supports_structured_output=True,
                supports_json_schema=True,
            ),
            ModelCapabilities(
                "sonar-reasoning-pro",
                "Sonar Reasoning Pro",
                supports_structured_output=True,
                supports_json_schema=True,
                supports_reasoning=True,
            ),
            ModelCapabilities(
                "sonar-deep-research",
                "Sonar Deep Research",
                supports_structured_output=True,
                supports_json_schema=True,
                supports_reasoning=True,
                notes=("Expect higher latency for research workflows.",),
            ),
        ),
    ),
    "OpenRouter": ProviderCatalog(
        "OpenRouter",
        "openai/gpt-5.4-mini",
        (
            ModelCapabilities(
                "openai/gpt-5.5",
                "OpenAI GPT-5.5 via OpenRouter",
                token_parameter="max_tokens",
                supports_structured_output=True,
                supports_json_schema=True,
                supports_reasoning=True,
                omit_temperature=True,
            ),
            ModelCapabilities(
                "openai/gpt-5.4-mini",
                "OpenAI GPT-5.4 Mini via OpenRouter",
                supports_structured_output=True,
                supports_json_schema=True,
                supports_reasoning=True,
                omit_temperature=True,
            ),
            ModelCapabilities(
                "anthropic/claude-opus-4.7",
                "Claude Opus 4.7 via OpenRouter",
                supports_structured_output=True,
                supports_json_schema=True,
                supports_reasoning=True,
            ),
            ModelCapabilities(
                "anthropic/claude-sonnet-4.6",
                "Claude Sonnet 4.6 via OpenRouter",
                supports_structured_output=True,
                supports_json_schema=True,
                supports_reasoning=True,
            ),
        ),
        True,
        "https://openrouter.ai/api/v1/models",
    ),
}


def get_provider_catalog(provider: str) -> ProviderCatalog | None:
    """Return the static catalog for a provider."""

    return PROVIDER_CATALOGS.get(provider)


def get_default_model(provider: str) -> str:
    """Return the recommended default model for a provider."""

    catalog = get_provider_catalog(provider)
    return catalog.default_model if catalog else ""


def get_model_capabilities(provider: str, model: str | None) -> ModelCapabilities:
    """Return known capabilities for a selected model.

    Unknown user-supplied model names remain valid and are treated as custom chat
    models with conservative OpenAI-compatible defaults.
    """

    selected = model or get_default_model(provider)
    catalog = get_provider_catalog(provider)
    if catalog:
        for item in catalog.models:
            if item.model == selected:
                return item
        for item in catalog.models:
            if selected.startswith(item.model.rstrip("*")):
                return item

    if provider in {"OpenAI", "OpenAI Azure", "Custom OpenAI", "Generic OpenAI"}:
        if selected.startswith(("gpt-5", "o3", "o4")):
            return ModelCapabilities(
                selected,
                endpoint_family="responses" if provider == "OpenAI" else "chat",
                token_parameter="max_output_tokens" if provider == "OpenAI" else "max_completion_tokens",
                supports_structured_output=provider == "OpenAI",
                supports_json_schema=provider == "OpenAI",
                supports_reasoning=True,
                omit_temperature=True,
            )
        if selected.startswith(("gpt-4o", "gpt-4.1")):
            return ModelCapabilities(
                selected,
                token_parameter="max_completion_tokens",
                supports_structured_output=True,
                supports_json_schema=True,
            )

    return ModelCapabilities(selected, status=STATUS_CUSTOM)


def model_uses_responses_api(provider: str, model: str | None) -> bool:
    """Return True when the model should use OpenAI's Responses API."""

    return provider == "OpenAI" and get_model_capabilities(provider, model).endpoint_family == "responses"


def chat_token_parameter(provider: str, model: str | None) -> str:
    """Return the correct token limit parameter for chat-compatible APIs."""

    capabilities = get_model_capabilities(provider, model)
    if capabilities.token_parameter == "max_output_tokens":
        return "max_completion_tokens"
    return capabilities.token_parameter


def should_send_temperature(provider: str, model: str | None) -> bool:
    """Return False for models known to reject custom temperature settings."""

    return not get_model_capabilities(provider, model).omit_temperature


def supports_json_schema(provider: str, model: str | None) -> bool:
    """Return True if this provider/model should receive JSON schema requests."""

    return get_model_capabilities(provider, model).supports_json_schema


def json_schema_response_format() -> dict:
    """Return an OpenAI-compatible JSON schema response_format block."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "automation_suggestions",
            "strict": False,
            "schema": SUGGESTION_RESPONSE_SCHEMA,
        },
    }


def _strip_schema_keys(value, unsupported_keys: set[str]):
    """Return a copy of a schema value without unsupported keys."""

    if isinstance(value, dict):
        return {
            key: _strip_schema_keys(schema_value, unsupported_keys)
            for key, schema_value in value.items()
            if key not in unsupported_keys
        }
    if isinstance(value, list):
        return [_strip_schema_keys(item, unsupported_keys) for item in value]
    return value


def google_json_schema_response_format() -> dict:
    """Return a Google Gemini-compatible JSON schema response format."""

    response_format = json_schema_response_format()
    return {
        "type": response_format["type"],
        "json_schema": {
            "name": response_format["json_schema"]["name"],
            "strict": response_format["json_schema"]["strict"],
            "schema": _strip_schema_keys(
                response_format["json_schema"]["schema"],
                {"additionalProperties"},
            ),
        },
    }


def compatibility_warnings(provider: str, model: str | None) -> list[str]:
    """Return user-facing warnings for the selected provider/model."""

    capabilities = get_model_capabilities(provider, model)
    warnings: list[str] = []
    if capabilities.status == STATUS_PREVIEW:
        warnings.append(f"{capabilities.model} is a preview model and may change without notice.")
    if capabilities.status == STATUS_DEPRECATED:
        warnings.append(f"{capabilities.model} is deprecated; choose a current model when possible.")
    warnings.extend(capabilities.notes)
    return warnings
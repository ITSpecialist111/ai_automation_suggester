# custom_components/ai_automation_suggester/config_flow.py
"""Config flow for AI Automation Suggester."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .const import *
from .endpoint_utils import (
    bearer_auth_headers,
    ensure_http_url,
    ollama_api_candidates,
    ollama_base_url,
    openai_model_endpoint_candidates,
)

_LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Lightweight provider validators (unchanged)
# ─────────────────────────────────────────────────────────────
class ProviderValidator:
    """Ping each provider with a dummy request to validate credentials."""

    def __init__(self, hass, request_timeout: int | None = None):
        self.session = async_get_clientsession(hass)
        self.timeout = aiohttp.ClientTimeout(total=max(10, int(request_timeout or DEFAULT_REQUEST_TIMEOUT)))

    async def validate_openai(self, api_key: str) -> Optional[str]:
        hdr = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            resp = await self.session.get("https://api.openai.com/v1/models", headers=hdr, timeout=self.timeout)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:  # noqa: BLE001
            return str(err)

    async def validate_anthropic(self, api_key: str, model: str) -> Optional[str]:
        hdr = {
            "x-api-key": api_key,
            "anthropic-version": VERSION_ANTHROPIC,
            "content-type": "application/json",
        }
        try:
            resp = await self.session.get("https://api.anthropic.com/v1/models", headers=hdr, timeout=self.timeout)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_google(self, api_key: str, model: str) -> Optional[str]:
        try:
            resp = await self.session.get(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}?key={api_key}",
                timeout=self.timeout,
            )
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_groq(self, api_key: str) -> Optional[str]:
        hdr = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            resp = await self.session.get("https://api.groq.com/openai/v1/models", headers=hdr, timeout=self.timeout)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_localai(self, ip: str, port: int, https: bool) -> Optional[str]:
        proto = "https" if https else "http"
        try:
            resp = await self.session.get(f"{proto}://{ip}:{port}/v1/models", timeout=self.timeout)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_ollama(
        self,
        ip: str | None,
        port: int | None,
        https: bool,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> Optional[str]:
        base = ollama_base_url(base_url=base_url, ip_address=ip, port=port, https=https)
        if not base:
            return "Ollama host/port or base URL is required"
        last_error = None
        headers = bearer_auth_headers(api_key)
        try:
            for endpoint in ollama_api_candidates(base, "api/tags"):
                resp = await self.session.get(endpoint, headers=headers, timeout=self.timeout)
                if resp.status == 200:
                    return None
                last_error = f"{endpoint}: {resp.status} {await resp.text()}"
            return last_error
        except Exception as err:
            return str(err)

    async def validate_custom_openai(self, endpoint: str, api_key: str | None) -> Optional[str]:
        hdr = {"Content-Type": "application/json"}
        if api_key:
            hdr["Authorization"] = f"Bearer {api_key}"
        last_error = None
        try:
            for model_endpoint in openai_model_endpoint_candidates(endpoint):
                resp = await self.session.get(model_endpoint, headers=hdr, timeout=self.timeout)
                if resp.status == 200:
                    return None
                last_error = f"{model_endpoint}: {resp.status} {await resp.text()}"
            return last_error or "No valid model endpoint could be built"
        except Exception as err:
            return str(err)

    async def validate_perplexity(self, api_key: str, model: str) -> Optional[str]:
        hdr = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        # Perplexity 'sonar' models require max_tokens >= 16; a smaller value is
        # rejected with a 400 during validation (issue #171).
        payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 16}
        try:
            resp = await self.session.post(ENDPOINT_PERPLEXITY, headers=hdr, json=payload, timeout=self.timeout)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_openrouter(self, api_key: str, model: str) -> Optional[str]:
        hdr = {"content-type": "application/json"}
        if api_key:
            hdr["Authorization"] = f"Bearer {api_key}"
        try:
            resp = await self.session.get(
                "https://openrouter.ai/api/v1/models", headers=hdr, timeout=self.timeout
            )
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_generic_openai(self, endpoint: str, api_key: str) -> Optional[str]:
        hdr = {"Content-Type": "application/json"}
        if api_key:
            hdr["Authorization"] = f"Bearer {api_key}"
        try:
            resp = await self.session.get(ensure_http_url(endpoint), headers=hdr, timeout=self.timeout)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)


# ─────────────────────────────────────────────────────────────
# Config‑flow main class
# ─────────────────────────────────────────────────────────────
class AIAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle integration setup via the UI."""

    VERSION = CONFIG_VERSION

    def __init__(self) -> None:
        self.provider: str | None = None
        self.data: Dict[str, Any] = {}
        self.validator: ProviderValidator | None = None

    # ───────── Initial provider choice ─────────
    async def async_step_user(self, user_input: Dict[str, Any] | None = None):
        errors: Dict[str, str] = {}
        if user_input:
            self.provider = user_input[CONF_PROVIDER]
            self.data.update(user_input)
            return await {
                "OpenAI": self.async_step_openai,
                "Anthropic": self.async_step_anthropic,
                "Google": self.async_step_google,
                "Groq": self.async_step_groq,
                "LocalAI": self.async_step_localai,
                "Ollama": self.async_step_ollama,
                "Custom OpenAI": self.async_step_custom_openai,
                "Mistral AI": self.async_step_mistral,
                "Perplexity AI": self.async_step_perplexity,
                "OpenRouter": self.async_step_openrouter,
                "OpenAI Azure": self.async_step_openai_azure,
                "Generic OpenAI": self.async_step_generic_openai,
                "LiteLLM": self.async_step_litellm,
            }[self.provider]()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROVIDER): vol.In(
                        [
                            "Anthropic",
                            "Custom OpenAI",
                            "Generic OpenAI",
                            "Google",
                            "Groq",
                            "LiteLLM",
                            "LocalAI",
                            "Mistral AI",
                            "Ollama",
                            "OpenAI Azure",
                            "OpenAI",
                            "OpenRouter",
                            "Perplexity AI",
                        ]
                    )
                }
            ),
            errors=errors,
        )

    # ───────── helper to reduce repetition ─────────
    async def _provider_form(
        self,
        step_id: str,
        schema: vol.Schema,
        validate_fn,
        title: str,
        errors: Dict[str, str],
        placeholders: Dict[str, str],
        user_input: Dict[str, Any] | None,
    ):
        if user_input:
            self.validator = ProviderValidator(self.hass, user_input.get(CONF_REQUEST_TIMEOUT))
            err = await validate_fn(user_input)
            if err is None:
                self.data.update({
                **user_input,
                CONF_MAX_INPUT_TOKENS: user_input.get(CONF_MAX_INPUT_TOKENS, DEFAULT_MAX_INPUT_TOKENS),
                CONF_MAX_OUTPUT_TOKENS: user_input.get(CONF_MAX_OUTPUT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS),
            })
                return self.async_create_entry(title=title, data=self.data)
            errors["base"] = "api_error"
            placeholders["error_message"] = err

        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors, description_placeholders=placeholders)

    # ───────── provider‑specific steps (OpenAI shown; others similar) ─────────
    def _add_token_fields(self, base: Dict[Any, Any]) -> Dict[Any, Any]:
        """Append common tuning fields to the schema."""
        base[vol.Optional(CONF_MAX_INPUT_TOKENS, default=DEFAULT_MAX_INPUT_TOKENS)] = vol.All(
            vol.Coerce(int), vol.Range(min=100)
        )
        base[vol.Optional(CONF_MAX_OUTPUT_TOKENS, default=DEFAULT_MAX_OUTPUT_TOKENS)] = vol.All(
            vol.Coerce(int), vol.Range(min=100)
        )
        base[vol.Optional(CONF_CUSTOM_SYSTEM_PROMPT, default="")] = str
        base[vol.Optional(CONF_EXCLUDED_DOMAINS, default="")] = str
        base[vol.Optional(CONF_EXCLUDED_ENTITIES, default="")] = str
        base[vol.Optional(CONF_EXCLUDED_AREAS, default="")] = str
        base[vol.Optional(CONF_HISTORY_RETENTION, default=DEFAULT_HISTORY_RETENTION)] = vol.All(
            vol.Coerce(int), vol.Range(min=1, max=250)
        )
        base[vol.Optional(CONF_REQUEST_TIMEOUT, default=DEFAULT_REQUEST_TIMEOUT)] = vol.All(
            vol.Coerce(int), vol.Range(min=10, max=1800)
        )
        return base

    async def async_step_openai(self, user_input=None):
        schema = {
            vol.Required(CONF_OPENAI_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(CONF_OPENAI_MODEL, default=DEFAULT_MODELS["OpenAI"]): str,
            vol.Optional(CONF_OPENAI_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
            vol.Optional(CONF_OPENAI_REASONING_EFFORT, default=DEFAULT_OPENAI_REASONING_EFFORT): vol.In(["minimal", "low", "medium", "high"]),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "openai",
            vol.Schema(schema),
            lambda ui: self.validator.validate_openai(ui[CONF_OPENAI_API_KEY]),
            "AI Automation Suggester (OpenAI)",
            {},
            {},
            user_input,
        )

    async def async_step_anthropic(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_anthropic(
                ui[CONF_ANTHROPIC_API_KEY], ui.get(CONF_ANTHROPIC_MODEL, DEFAULT_MODELS["Anthropic"])
            )

        schema = {
            vol.Required(CONF_ANTHROPIC_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(CONF_ANTHROPIC_MODEL, default=DEFAULT_MODELS["Anthropic"]): str,
            vol.Optional(CONF_ANTHROPIC_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "anthropic",
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (Anthropic)",
            {},
            {},
            user_input,
        )

    async def async_step_google(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_google(
                ui[CONF_GOOGLE_API_KEY], ui.get(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"])
            )

        schema = {
            vol.Required(CONF_GOOGLE_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(CONF_GOOGLE_MODEL, default=DEFAULT_MODELS["Google"]): str,
            vol.Optional(CONF_GOOGLE_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "google",
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (Google)",
            {},
            {},
            user_input,
        )

    async def async_step_groq(self, user_input=None):
        schema = {
            vol.Required(CONF_GROQ_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(CONF_GROQ_MODEL, default=DEFAULT_MODELS["Groq"]): str,
            vol.Optional(CONF_GROQ_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
                vol.Coerce(float), vol.Range(min=0.0, max=2.0)
            ),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "groq",
            vol.Schema(schema),
            lambda ui: self.validator.validate_groq(ui[CONF_GROQ_API_KEY]),
            "AI Automation Suggester (Groq)",
            {},
            {},
            user_input,
        )

    async def async_step_localai(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_localai(ui[CONF_LOCALAI_IP_ADDRESS], ui[CONF_LOCALAI_PORT], ui[CONF_LOCALAI_HTTPS])

        schema = {
            vol.Required(CONF_LOCALAI_IP_ADDRESS): str,
            vol.Required(CONF_LOCALAI_PORT, default=8080): int,
            vol.Required(CONF_LOCALAI_HTTPS, default=False): bool,
            vol.Optional(CONF_LOCALAI_MODEL, default=DEFAULT_MODELS["LocalAI"]): str,
            vol.Optional(CONF_LOCALAI_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
                vol.Coerce(float), vol.Range(min=0.0, max=2.0)
            ),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "localai", 
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (LocalAI)",
            {},
            {},
            user_input,
        )

    async def async_step_ollama(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_ollama(
                ui.get(CONF_OLLAMA_IP_ADDRESS),
                ui.get(CONF_OLLAMA_PORT),
                ui.get(CONF_OLLAMA_HTTPS, False),
                ui.get(CONF_OLLAMA_BASE_URL),
                ui.get(CONF_OLLAMA_API_KEY),
            )

        schema = {
            vol.Optional(CONF_OLLAMA_BASE_URL, default=""): str,
            vol.Optional(CONF_OLLAMA_API_KEY, default=""): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(CONF_OLLAMA_IP_ADDRESS, default="localhost"): str,
            vol.Optional(CONF_OLLAMA_PORT, default=11434): int,
            vol.Optional(CONF_OLLAMA_HTTPS, default=False): bool,
            vol.Optional(CONF_OLLAMA_MODEL, default=DEFAULT_MODELS["Ollama"]): str,
            vol.Optional(CONF_OLLAMA_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
                vol.Coerce(float), vol.Range(min=0.0, max=2.0)
            ),
            vol.Optional(CONF_OLLAMA_DISABLE_THINK, default=False): bool,
   
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "ollama",
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (Ollama)",
            {},
            {},
            user_input,
        )

    async def async_step_custom_openai(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_custom_openai(ui[CONF_CUSTOM_OPENAI_ENDPOINT], ui.get(CONF_CUSTOM_OPENAI_API_KEY))

        schema = {
            vol.Required(CONF_CUSTOM_OPENAI_ENDPOINT): str,
            vol.Optional(CONF_CUSTOM_OPENAI_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(CONF_CUSTOM_OPENAI_MODEL, default=DEFAULT_MODELS["Custom OpenAI"]): str,
            vol.Optional(CONF_CUSTOM_OPENAI_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "custom_openai",
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (Custom OpenAI)",
            {},
            {},
            user_input,
        )

    # Mistral: no live validation needed
    async def async_step_mistral(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return self.async_create_entry(title="AI Automation Suggester (Mistral AI)", data=self.data)

        schema = {
            vol.Required(CONF_MISTRAL_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(CONF_MISTRAL_MODEL, default=DEFAULT_MODELS["Mistral AI"]): str,
            vol.Optional(CONF_MISTRAL_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
                vol.Coerce(float), vol.Range(min=0.0, max=2.0)
            ),
        }
        self._add_token_fields(schema)
        return self.async_show_form(step_id="mistral", data_schema=vol.Schema(schema))

    async def async_step_perplexity(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_perplexity(
                ui[CONF_PERPLEXITY_API_KEY], ui.get(CONF_PERPLEXITY_MODEL, DEFAULT_MODELS["Perplexity AI"])
            )

        schema = {
            vol.Required(CONF_PERPLEXITY_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(CONF_PERPLEXITY_MODEL, default=DEFAULT_MODELS["Perplexity AI"]): str,
            vol.Optional(CONF_PERPLEXITY_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
                vol.Coerce(float), vol.Range(min=0.0, max=2.0)
            ),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "perplexity",
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (Perplexity)",
            {},
            {},
            user_input,
        )

    async def async_step_openrouter(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_openrouter(
                ui[CONF_OPENROUTER_API_KEY],
                ui.get(CONF_OPENROUTER_MODEL, DEFAULT_MODELS["OpenRouter"]),
            )

        schema = {
            vol.Required(CONF_OPENROUTER_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(
                CONF_OPENROUTER_MODEL, default=DEFAULT_MODELS["OpenRouter"]
            ): str,
            vol.Optional(CONF_OPENROUTER_REASONING_MAX_TOKENS, default=0): vol.All(
                vol.Coerce(int), vol.Range(min=0)
            ),
            vol.Optional(
                CONF_OPENROUTER_TEMPERATURE, default=DEFAULT_TEMPERATURE
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "openrouter",
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (OpenRouter)",
            {},
            {},
            user_input,
        )

    async def async_step_openai_azure(self, user_input=None):
        async def _v(ui):
            if not ui.get(CONF_OPENAI_AZURE_API_KEY) or not ui.get(CONF_OPENAI_AZURE_DEPLOYMENT_ID) or not ui.get(CONF_OPENAI_AZURE_API_VERSION):
                return "All fields are required"
            return None

        schema = {
            vol.Required(CONF_OPENAI_AZURE_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Required(CONF_OPENAI_AZURE_DEPLOYMENT_ID, default=DEFAULT_MODELS["OpenAI Azure"]): str,
            vol.Required(CONF_OPENAI_AZURE_ENDPOINT, default="{your-resource-name}.openai.azure.com"): str,
            vol.Required(CONF_OPENAI_AZURE_API_VERSION, default="2025-01-01-preview"): str,
            vol.Optional(CONF_OPENAI_AZURE_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "openai_azure",
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (OpenAI Azure)",
            {},
            {},
            user_input,
        )

    async def async_step_generic_openai(self, user_input=None):
        """Handle the Generic OpenAI API configuration."""
        async def _v(ui):
            if not ui.get(CONF_GENERIC_OPENAI_ENDPOINT):
                return "API URL is required"
            if ui.get(CONF_GENERIC_OPENAI_ENABLE_VALIDATION, False):
                if not ui.get(CONF_GENERIC_OPENAI_VALIDATION_ENDPOINT):
                    return "Validation endpoint is required when validation is enabled"
                return await self.validator.validate_generic_openai(ui[CONF_GENERIC_OPENAI_VALIDATION_ENDPOINT], ui.get(CONF_GENERIC_OPENAI_API_KEY))

        schema = {
            vol.Required(CONF_GENERIC_OPENAI_ENDPOINT): str,
            vol.Required(CONF_GENERIC_OPENAI_API_KEY): TextSelector(TextSelectorConfig(type="password")),
            vol.Required(CONF_GENERIC_OPENAI_MODEL, default=DEFAULT_MODELS["Generic OpenAI"]): str,
            vol.Optional(CONF_GENERIC_OPENAI_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
            vol.Optional(CONF_GENERIC_OPENAI_VALIDATION_ENDPOINT, default=""): str,
            vol.Optional(CONF_GENERIC_OPENAI_ENABLE_VALIDATION, default=False): bool,
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "generic_openai",
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (Generic OpenAI)",
            {},
            {},
            user_input,
        )

    async def async_step_litellm(self, user_input=None):
        """Handle the LiteLLM configuration."""
        async def _v(ui):
            if not ui.get(CONF_LITELLM_MODEL):
                return "Model is required (e.g. openai/gpt-4o, anthropic/claude-sonnet-4-6)"

        schema = {
            vol.Required(CONF_LITELLM_MODEL, default=DEFAULT_MODELS["LiteLLM"]): str,
            vol.Optional(CONF_LITELLM_API_KEY, default=""): TextSelector(TextSelectorConfig(type="password")),
            vol.Optional(CONF_LITELLM_API_BASE, default=""): str,
            vol.Optional(CONF_LITELLM_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
        }
        self._add_token_fields(schema)
        return await self._provider_form(
            "litellm",
            vol.Schema(schema),
            _v,
            "AI Automation Suggester (LiteLLM)",
            {},
            {},
            user_input,
        )

    # ───────── Options flow (edit after setup) ─────────
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AIAutomationOptionsFlowHandler(config_entry)


class AIAutomationOptionsFlowHandler(config_entries.OptionsFlow):
    """Allow post‑setup tweaking of models, keys, token budgets."""

    def __init__(self, config_entry):
        super().__init__()
        self._config_entry = config_entry

    def _get_option(self, key, default=None):
        """Get value from options, then data, then default."""
        if key in self._config_entry.options:
            return self._config_entry.options.get(key)
        if key in self._config_entry.data:
            return self._config_entry.data.get(key)
        return default

    async def async_step_init(self, user_input=None):
        if user_input:
            new_data = {
                **self._config_entry.options,
                **user_input,
                CONF_MAX_INPUT_TOKENS: user_input.get(
                    CONF_MAX_INPUT_TOKENS,
                    self._get_option(CONF_MAX_INPUT_TOKENS, DEFAULT_MAX_INPUT_TOKENS)
                ),
                CONF_MAX_OUTPUT_TOKENS: user_input.get(
                    CONF_MAX_OUTPUT_TOKENS,
                    self._get_option(CONF_MAX_OUTPUT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS)
                ),
            }
            return self.async_create_entry(title="", data=new_data)

        provider = self._config_entry.data.get(CONF_PROVIDER)
        schema: Dict[Any, Any] = {
            vol.Optional(CONF_MAX_INPUT_TOKENS, default=self._get_option(CONF_MAX_INPUT_TOKENS, DEFAULT_MAX_INPUT_TOKENS)
            ): vol.All(vol.Coerce(int), vol.Range(min=100)),
            vol.Optional(CONF_MAX_OUTPUT_TOKENS, default=self._get_option(CONF_MAX_OUTPUT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS)
            ): vol.All(vol.Coerce(int), vol.Range(min=100)),
            vol.Optional(CONF_CUSTOM_SYSTEM_PROMPT, default=self._get_option(CONF_CUSTOM_SYSTEM_PROMPT, "")): str,
            vol.Optional(CONF_EXCLUDED_DOMAINS, default=self._get_option(CONF_EXCLUDED_DOMAINS, "")): str,
            vol.Optional(CONF_EXCLUDED_ENTITIES, default=self._get_option(CONF_EXCLUDED_ENTITIES, "")): str,
            vol.Optional(CONF_EXCLUDED_AREAS, default=self._get_option(CONF_EXCLUDED_AREAS, "")): str,
            vol.Optional(CONF_HISTORY_RETENTION, default=self._get_option(CONF_HISTORY_RETENTION, DEFAULT_HISTORY_RETENTION)): vol.All(vol.Coerce(int), vol.Range(min=1, max=250)),
            vol.Optional(CONF_REQUEST_TIMEOUT, default=self._get_option(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT)): vol.All(vol.Coerce(int), vol.Range(min=10, max=1800)),
        }

        # provider‑specific editable fields
        if provider == "OpenAI":
            schema[vol.Optional(CONF_OPENAI_API_KEY, default=self._get_option(CONF_OPENAI_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_OPENAI_MODEL, default=self._get_option(CONF_OPENAI_MODEL, DEFAULT_MODELS["OpenAI"]))] = str
            schema[vol.Optional(CONF_OPENAI_TEMPERATURE, default=self._get_option(CONF_OPENAI_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
            schema[vol.Optional(CONF_OPENAI_REASONING_EFFORT, default=self._get_option(CONF_OPENAI_REASONING_EFFORT, DEFAULT_OPENAI_REASONING_EFFORT))] = vol.In(["minimal", "low", "medium", "high"])
        elif provider == "Anthropic":
            schema[vol.Optional(CONF_ANTHROPIC_API_KEY, default=self._get_option(CONF_ANTHROPIC_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_ANTHROPIC_MODEL, default=self._get_option(CONF_ANTHROPIC_MODEL, DEFAULT_MODELS["Anthropic"]))] = str
            schema[vol.Optional(CONF_ANTHROPIC_TEMPERATURE, default=self._get_option(CONF_ANTHROPIC_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
        elif provider == "Google":
            schema[vol.Optional(CONF_GOOGLE_API_KEY, default=self._get_option(CONF_GOOGLE_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_GOOGLE_MODEL, default=self._get_option(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"]))] = str
            schema[vol.Optional(CONF_GOOGLE_TEMPERATURE, default=self._get_option(CONF_GOOGLE_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
        elif provider == "Groq":
            schema[vol.Optional(CONF_GROQ_API_KEY, default=self._get_option(CONF_GROQ_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_GROQ_MODEL, default=self._get_option(CONF_GROQ_MODEL, DEFAULT_MODELS["Groq"]))] = str
            schema[vol.Optional(CONF_GROQ_TEMPERATURE, default=self._get_option(CONF_GROQ_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
        elif provider == "LocalAI":
            schema[vol.Optional(CONF_LOCALAI_HTTPS, default=self._get_option(CONF_LOCALAI_HTTPS, False))] = bool
            schema[vol.Optional(CONF_LOCALAI_MODEL, default=self._get_option(CONF_LOCALAI_MODEL, DEFAULT_MODELS["LocalAI"]))] = str
            schema[vol.Optional(CONF_LOCALAI_TEMPERATURE, default=self._get_option(CONF_LOCALAI_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
            schema[vol.Optional(CONF_LOCALAI_IP_ADDRESS, default=self._get_option(CONF_LOCALAI_IP_ADDRESS, "localhost"))] = str
            schema[vol.Optional(CONF_LOCALAI_PORT, default=self._get_option(CONF_LOCALAI_PORT, 8080))] = int
        elif provider == "Ollama":
            schema[vol.Optional(CONF_OLLAMA_BASE_URL, default=self._get_option(CONF_OLLAMA_BASE_URL, ""))] = str
            schema[vol.Optional(CONF_OLLAMA_API_KEY, default=self._get_option(CONF_OLLAMA_API_KEY, ""))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_OLLAMA_IP_ADDRESS, default=self._get_option(CONF_OLLAMA_IP_ADDRESS, "localhost"))] = str
            schema[vol.Optional(CONF_OLLAMA_PORT, default=self._get_option(CONF_OLLAMA_PORT, 11434))] = int
            schema[vol.Optional(CONF_OLLAMA_HTTPS, default=self._get_option(CONF_OLLAMA_HTTPS, False))] = bool
            schema[vol.Optional(CONF_OLLAMA_MODEL, default=self._get_option(CONF_OLLAMA_MODEL, DEFAULT_MODELS["Ollama"]))] = str
            schema[vol.Optional(CONF_OLLAMA_TEMPERATURE, default=self._get_option(CONF_OLLAMA_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
            schema[vol.Optional(CONF_OLLAMA_DISABLE_THINK, default=self._get_option(CONF_OLLAMA_DISABLE_THINK, False))] = bool    
        elif provider == "Custom OpenAI":
            schema[vol.Optional(CONF_CUSTOM_OPENAI_ENDPOINT, default=self._get_option(CONF_CUSTOM_OPENAI_ENDPOINT))] = str
            schema[vol.Optional(CONF_CUSTOM_OPENAI_API_KEY, default=self._get_option(CONF_CUSTOM_OPENAI_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_CUSTOM_OPENAI_MODEL, default=self._get_option(CONF_CUSTOM_OPENAI_MODEL, DEFAULT_MODELS["Custom OpenAI"]))] = str
            schema[vol.Optional(CONF_CUSTOM_OPENAI_TEMPERATURE, default=self._get_option(CONF_CUSTOM_OPENAI_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
        elif provider == "Mistral AI":
            schema[vol.Optional(CONF_MISTRAL_API_KEY, default=self._get_option(CONF_MISTRAL_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_MISTRAL_MODEL, default=self._get_option(CONF_MISTRAL_MODEL, DEFAULT_MODELS["Mistral AI"]))] = str
            schema[vol.Optional(CONF_MISTRAL_TEMPERATURE, default=self._get_option(CONF_MISTRAL_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
        elif provider == "Perplexity AI":
            schema[vol.Optional(CONF_PERPLEXITY_API_KEY, default=self._get_option(CONF_PERPLEXITY_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_PERPLEXITY_MODEL, default=self._get_option(CONF_PERPLEXITY_MODEL, DEFAULT_MODELS["Perplexity AI"]))] = str
            schema[vol.Optional(CONF_PERPLEXITY_TEMPERATURE, default=self._get_option(CONF_PERPLEXITY_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
        elif provider == "OpenRouter":
            schema[vol.Optional(CONF_OPENROUTER_API_KEY, default=self._get_option(CONF_OPENROUTER_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_OPENROUTER_MODEL, default=self._get_option(CONF_OPENROUTER_MODEL, DEFAULT_MODELS["OpenRouter"]))] = str
            schema[vol.Optional(CONF_OPENROUTER_REASONING_MAX_TOKENS, default=self._get_option(CONF_OPENROUTER_REASONING_MAX_TOKENS, 0))] = vol.All(vol.Coerce(int), vol.Range(min=0))
            schema[vol.Optional(CONF_OPENROUTER_TEMPERATURE, default=self._get_option(CONF_OPENROUTER_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
        elif provider == "OpenAI Azure":
            schema[vol.Optional(CONF_OPENAI_AZURE_API_KEY, default=self._get_option(CONF_OPENAI_AZURE_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_OPENAI_AZURE_ENDPOINT, default=self._get_option(CONF_OPENAI_AZURE_ENDPOINT))] = str
            schema[vol.Optional(CONF_OPENAI_AZURE_DEPLOYMENT_ID, default=self._get_option(CONF_OPENAI_AZURE_DEPLOYMENT_ID, DEFAULT_MODELS["OpenAI Azure"]))] = str
            schema[vol.Optional(CONF_OPENAI_AZURE_API_VERSION, default=self._get_option(CONF_OPENAI_AZURE_API_VERSION, "2025-01-01-preview"))] = str
            schema[vol.Optional(CONF_OPENAI_AZURE_TEMPERATURE, default=self._get_option(CONF_OPENAI_AZURE_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
        elif provider == "Generic OpenAI":
            schema[vol.Optional(CONF_GENERIC_OPENAI_API_KEY, default=self._get_option(CONF_GENERIC_OPENAI_API_KEY))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_GENERIC_OPENAI_ENDPOINT, default=self._get_option(CONF_GENERIC_OPENAI_ENDPOINT))] = str
            schema[vol.Optional(CONF_GENERIC_OPENAI_MODEL, default=self._get_option(CONF_GENERIC_OPENAI_MODEL, DEFAULT_MODELS["Generic OpenAI"]))] = str
            schema[vol.Optional(CONF_GENERIC_OPENAI_TEMPERATURE, default=self._get_option(CONF_GENERIC_OPENAI_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))
            schema[vol.Optional(CONF_GENERIC_OPENAI_VALIDATION_ENDPOINT, default=self._get_option(CONF_GENERIC_OPENAI_VALIDATION_ENDPOINT, ""))] = str
            schema[vol.Optional(CONF_GENERIC_OPENAI_ENABLE_VALIDATION, default=self._get_option(CONF_GENERIC_OPENAI_ENABLE_VALIDATION, False))] = bool
        elif provider == "LiteLLM":
            schema[vol.Optional(CONF_LITELLM_API_KEY, default=self._get_option(CONF_LITELLM_API_KEY, ""))] = TextSelector(TextSelectorConfig(type="password"))
            schema[vol.Optional(CONF_LITELLM_MODEL, default=self._get_option(CONF_LITELLM_MODEL, DEFAULT_MODELS["LiteLLM"]))] = str
            schema[vol.Optional(CONF_LITELLM_API_BASE, default=self._get_option(CONF_LITELLM_API_BASE, ""))] = str
            schema[vol.Optional(CONF_LITELLM_TEMPERATURE, default=self._get_option(CONF_LITELLM_TEMPERATURE, DEFAULT_TEMPERATURE))] = vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0))

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))

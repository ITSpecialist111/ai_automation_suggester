# custom_components/ai_automation_suggester/config_flow.py
"""Config flow for AI Automation Suggester."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_PROVIDER,
    CONF_MAX_TOKENS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODELS,
    # OpenAI
    CONF_OPENAI_API_KEY,
    CONF_OPENAI_MODEL,
    # Anthropic
    CONF_ANTHROPIC_API_KEY,
    CONF_ANTHROPIC_MODEL,
    VERSION_ANTHROPIC,
    # Google
    CONF_GOOGLE_API_KEY,
    CONF_GOOGLE_MODEL,
    # Groq
    CONF_GROQ_API_KEY,
    CONF_GROQ_MODEL,
    # LocalAI
    CONF_LOCALAI_IP_ADDRESS,
    CONF_LOCALAI_PORT,
    CONF_LOCALAI_HTTPS,
    CONF_LOCALAI_MODEL,
    # Ollama
    CONF_OLLAMA_IP_ADDRESS,
    CONF_OLLAMA_PORT,
    CONF_OLLAMA_HTTPS,
    CONF_OLLAMA_MODEL,
    # Custom OpenAI
    CONF_CUSTOM_OPENAI_ENDPOINT,
    CONF_CUSTOM_OPENAI_API_KEY,
    CONF_CUSTOM_OPENAI_MODEL,
    # Mistral
    CONF_MISTRAL_API_KEY,
    CONF_MISTRAL_MODEL,
    # Perplexity (NEW)
    CONF_PERPLEXITY_API_KEY,
    CONF_PERPLEXITY_MODEL,
    ENDPOINT_PERPLEXITY,
)

_LOGGER = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper – validate provider connectivity with a tiny request
# ─────────────────────────────────────────────────────────────────────────────
class ProviderValidator:
    """Lightweight connectivity checks for each provider."""

    def __init__(self, hass):
        self.session = async_get_clientsession(hass)

    async def validate_openai(self, api_key: str) -> Optional[str]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            resp = await self.session.get("https://api.openai.com/v1/models", headers=headers)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:  # noqa: BLE001
            return str(err)

    async def validate_anthropic(self, api_key: str, model: str) -> Optional[str]:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": VERSION_ANTHROPIC,
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
            "max_tokens": 1,
            "temperature": 0,
        }
        try:
            resp = await self.session.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_google(self, api_key: str, model: str) -> Optional[str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "Hello"}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 1},
        }
        try:
            resp = await self.session.post(url, json=payload)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_groq(self, api_key: str) -> Optional[str]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            resp = await self.session.get("https://api.groq.com/openai/v1/models", headers=headers)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_localai(self, ip: str, port: int, https: bool) -> Optional[str]:
        proto = "https" if https else "http"
        try:
            resp = await self.session.get(f"{proto}://{ip}:{port}/v1/models")
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_ollama(self, ip: str, port: int, https: bool) -> Optional[str]:
        proto = "https" if https else "http"
        try:
            resp = await self.session.get(f"{proto}://{ip}:{port}/api/tags")
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_custom_openai(self, endpoint: str, api_key: str | None) -> Optional[str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            resp = await self.session.get(f"{endpoint}/v1/models", headers=headers)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)

    async def validate_perplexity(self, api_key: str, model: str) -> Optional[str]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 1,
            "temperature": 0,
        }
        try:
            resp = await self.session.post(ENDPOINT_PERPLEXITY, headers=headers, json=payload)
            return None if resp.status == 200 else await resp.text()
        except Exception as err:
            return str(err)


# ─────────────────────────────────────────────────────────────────────────────
# Config Flow
# ─────────────────────────────────────────────────────────────────────────────
class AIAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self.provider: str | None = None
        self.data: Dict[str, Any] = {}
        self.validator: ProviderValidator | None = None

    # ─────────── initial step – pick provider ───────────
    async def async_step_user(self, user_input: Dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input:
            self.provider = user_input[CONF_PROVIDER]
            self.data.update(user_input)

            # prevent duplicates
            if any(ent.data.get(CONF_PROVIDER) == self.provider for ent in self._async_current_entries()):
                errors["base"] = "already_configured"
            else:
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
                }[self.provider]()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_PROVIDER): vol.In(
                [
                    "OpenAI",
                    "Anthropic",
                    "Google",
                    "Groq",
                    "LocalAI",
                    "Ollama",
                    "Custom OpenAI",
                    "Mistral AI",
                    "Perplexity AI",
                ]
            )}),
            errors=errors,
        )

    # ─────────── helper to cut repetition ───────────
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
            self.validator = ProviderValidator(self.hass)
            err = await validate_fn(user_input)
            if err is None:
                self.data.update(user_input)
                return self.async_create_entry(title=title, data=self.data)
            errors["base"] = "api_error"
            placeholders["error_message"] = err

        return self.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    # ---------------- provider‑specific steps -----------------
    async def async_step_openai(self, user_input=None):
        return await self._provider_form(
            "openai",
            vol.Schema(
                {
                    vol.Required(CONF_OPENAI_API_KEY): str,
                    vol.Optional(CONF_OPENAI_MODEL, default=DEFAULT_MODELS["OpenAI"]): str,
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(vol.Coerce(int), vol.Range(min=100)),
                }
            ),
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

        return await self._provider_form(
            "anthropic",
            vol.Schema(
                {
                    vol.Required(CONF_ANTHROPIC_API_KEY): str,
                    vol.Optional(CONF_ANTHROPIC_MODEL, default=DEFAULT_MODELS["Anthropic"]): str,
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(vol.Coerce(int), vol.Range(min=100)),
                }
            ),
            _v,
            "AI Automation Suggester (Anthropic)",
            {},
            {},
            user_input,
        )

    async def async_step_google(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_google(ui[CONF_GOOGLE_API_KEY], ui.get(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"]))

        return await self._provider_form(
            "google",
            vol.Schema(
                {
                    vol.Required(CONF_GOOGLE_API_KEY): str,
                    vol.Optional(CONF_GOOGLE_MODEL, default=DEFAULT_MODELS["Google"]): str,
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(vol.Coerce(int), vol.Range(min=100)),
                }
            ),
            _v,
            "AI Automation Suggester (Google)",
            {},
            {},
            user_input,
        )

    async def async_step_groq(self, user_input=None):
        return await self._provider_form(
            "groq",
            vol.Schema(
                {
                    vol.Required(CONF_GROQ_API_KEY): str,
                    vol.Optional(CONF_GROQ_MODEL, default=DEFAULT_MODELS["Groq"]): str,
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(vol.Coerce(int), vol.Range(min=100)),
                }
            ),
            lambda ui: self.validator.validate_groq(ui[CONF_GROQ_API_KEY]),
            "AI Automation Suggester (Groq)",
            {},
            {},
            user_input,
        )

    async def async_step_localai(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_localai(ui[CONF_LOCALAI_IP_ADDRESS], ui[CONF_LOCALAI_PORT], ui[CONF_LOCALAI_HTTPS])

        return await self._provider_form(
            "localai",
            vol.Schema(
                {
                    vol.Required(CONF_LOCALAI_IP_ADDRESS): str,
                    vol.Required(CONF_LOCALAI_PORT, default=8080): int,
                    vol.Required(CONF_LOCALAI_HTTPS, default=False): bool,
                    vol.Optional(CONF_LOCALAI_MODEL, default=DEFAULT_MODELS["LocalAI"]): str,
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(vol.Coerce(int), vol.Range(min=100)),
                }
            ),
            _v,
            "AI Automation Suggester (LocalAI)",
            {},
            {},
            user_input,
        )

    async def async_step_ollama(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_ollama(ui[CONF_OLLAMA_IP_ADDRESS], ui[CONF_OLLAMA_PORT], ui[CONF_OLLAMA_HTTPS])

        return await self._provider_form(
            "ollama",
            vol.Schema(
                {
                    vol.Required(CONF_OLLAMA_IP_ADDRESS): str,
                    vol.Required(CONF_OLLAMA_PORT, default=11434): int,
                    vol.Required(CONF_OLLAMA_HTTPS, default=False): bool,
                    vol.Optional(CONF_OLLAMA_MODEL, default=DEFAULT_MODELS["Ollama"]): str,
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(vol.Coerce(int), vol.Range(min=100)),
                }
            ),
            _v,
            "AI Automation Suggester (Ollama)",
            {},
            {},
            user_input,
        )

    async def async_step_custom_openai(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_custom_openai(ui[CONF_CUSTOM_OPENAI_ENDPOINT], ui.get(CONF_CUSTOM_OPENAI_API_KEY))

        return await self._provider_form(
            "custom_openai",
            vol.Schema(
                {
                    vol.Required(CONF_CUSTOM_OPENAI_ENDPOINT): str,
                    vol.Optional(CONF_CUSTOM_OPENAI_API_KEY): str,
                    vol.Optional(CONF_CUSTOM_OPENAI_MODEL, default=DEFAULT_MODELS["Custom OpenAI"]): str,
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(vol.Coerce(int), vol.Range(min=100)),
                }
            ),
            _v,
            "AI Automation Suggester (Custom OpenAI)",
            {},
            {},
            user_input,
        )

    # no live validation for Mistral
    async def async_step_mistral(self, user_input=None):
        if user_input:
            self.data.update(user_input)
            return self.async_create_entry(title="AI Automation Suggester (Mistral AI)", data=self.data)

        return self.async_show_form(
            step_id="mistral",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MISTRAL_API_KEY): str,
                    vol.Optional(CONF_MISTRAL_MODEL, default=DEFAULT_MODELS["Mistral AI"]): str,
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(vol.Coerce(int), vol.Range(min=100)),
                }
            ),
        )

    async def async_step_perplexity(self, user_input=None):
        async def _v(ui):
            return await self.validator.validate_perplexity(
                ui[CONF_PERPLEXITY_API_KEY], ui.get(CONF_PERPLEXITY_MODEL, DEFAULT_MODELS["Perplexity AI"])
            )

        return await self._provider_form(
            "perplexity",
            vol.Schema(
                {
                    vol.Required(CONF_PERPLEXITY_API_KEY): str,
                    vol.Optional(CONF_PERPLEXITY_MODEL, default=DEFAULT_MODELS["Perplexity AI"]): str,
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(vol.Coerce(int), vol.Range(min=100)),
                }
            ),
            _v,
            "AI Automation Suggester (Perplexity)",
            {},
            {},
            user_input,
        )

    # ─────────── Options flow ───────────
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):  # noqa: D401
        return AIAutomationOptionsFlowHandler(config_entry)


class AIAutomationOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow – allows tweaking tokens/model keys after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input:
            return self.async_create_entry(title="", data=user_input)

        provider = self.config_entry.data.get(CONF_PROVIDER)
        schema: Dict[Any, Any] = {
            vol.Optional(CONF_MAX_TOKENS, default=self.config_entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): vol.All(
                vol.Coerce(int), vol.Range(min=100)
            )
        }

        # add provider‑specific editable fields
        if provider == "OpenAI":
            schema[vol.Optional(CONF_OPENAI_API_KEY)] = str
            schema[vol.Optional(CONF_OPENAI_MODEL, default=self.config_entry.data.get(CONF_OPENAI_MODEL, DEFAULT_MODELS["OpenAI"]))] = str
        elif provider == "Anthropic":
            schema[vol.Optional(CONF_ANTHROPIC_API_KEY)] = str
            schema[
                vol.Optional(CONF_ANTHROPIC_MODEL, default=self.config_entry.data.get(CONF_ANTHROPIC_MODEL, DEFAULT_MODELS["Anthropic"]))
            ] = str
        elif provider == "Google":
            schema[vol.Optional(CONF_GOOGLE_API_KEY)] = str
            schema[vol.Optional(CONF_GOOGLE_MODEL, default=self.config_entry.data.get(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"]))] = str
        elif provider == "Groq":
            schema[vol.Optional(CONF_GROQ_API_KEY)] = str
            schema[vol.Optional(CONF_GROQ_MODEL, default=self.config_entry.data.get(CONF_GROQ_MODEL, DEFAULT_MODELS["Groq"]))] = str
        elif provider == "LocalAI":
            schema[vol.Optional(CONF_LOCALAI_HTTPS)] = bool
            schema[
                vol.Optional(CONF_LOCALAI_MODEL, default=self.config_entry.data.get(CONF_LOCALAI_MODEL, DEFAULT_MODELS["LocalAI"]))
            ] = str
        elif provider == "Ollama":
            schema[vol.Optional(CONF_OLLAMA_HTTPS)] = bool
            schema[
                vol.Optional(CONF_OLLAMA_MODEL, default=self.config_entry.data.get(CONF_OLLAMA_MODEL, DEFAULT_MODELS["Ollama"]))
            ] = str
        elif provider == "Custom OpenAI":
            schema[vol.Optional(CONF_CUSTOM_OPENAI_ENDPOINT)] = str
            schema[vol.Optional(CONF_CUSTOM_OPENAI_API_KEY)] = str
            schema[
                vol.Optional(
                    CONF_CUSTOM_OPENAI_MODEL, default=self.config_entry.data.get(CONF_CUSTOM_OPENAI_MODEL, DEFAULT_MODELS["Custom OpenAI"])
                )
            ] = str
        elif provider == "Mistral AI":
            schema[vol.Optional(CONF_MISTRAL_API_KEY)] = str
            schema[vol.Optional(CONF_MISTRAL_MODEL, default=self.config_entry.data.get(CONF_MISTRAL_MODEL, DEFAULT_MODELS["Mistral AI"]))] = str
        elif provider == "Perplexity AI":
            schema[vol.Optional(CONF_PERPLEXITY_API_KEY)] = str
            schema[
                vol.Optional(
                    CONF_PERPLEXITY_MODEL, default=self.config_entry.data.get(CONF_PERPLEXITY_MODEL, DEFAULT_MODELS["Perplexity AI"])
                )
            ] = str

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))

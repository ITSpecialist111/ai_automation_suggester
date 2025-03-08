# custom_components/ai_automation_suggester/config_flow.py

"""Config flow for AI Automation Suggester integration."""
import logging
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_PROVIDER,
    CONF_MAX_TOKENS,
    DEFAULT_MAX_TOKENS,
    CONF_OPENAI_API_KEY,
    CONF_OPENAI_MODEL,
    CONF_ANTHROPIC_API_KEY,
    CONF_ANTHROPIC_MODEL,
    CONF_GOOGLE_API_KEY,
    CONF_GOOGLE_MODEL,
    CONF_GROQ_API_KEY,
    CONF_GROQ_MODEL,
    CONF_LOCALAI_IP_ADDRESS,
    CONF_LOCALAI_PORT,
    CONF_LOCALAI_HTTPS,
    CONF_LOCALAI_MODEL,
    CONF_OLLAMA_IP_ADDRESS,
    CONF_OLLAMA_PORT,
    CONF_OLLAMA_HTTPS,
    CONF_OLLAMA_MODEL,
    CONF_CUSTOM_OPENAI_ENDPOINT,
    CONF_CUSTOM_OPENAI_API_KEY,
    CONF_CUSTOM_OPENAI_MODEL,
    DEFAULT_MODELS,
    VERSION_ANTHROPIC,
    # Mistral AI additions:
    CONF_MISTRAL_API_KEY,
    CONF_MISTRAL_MODEL,
)

_LOGGER = logging.getLogger(__name__)


class ProviderValidator:
    """Validate provider configurations."""

    def __init__(self, hass):
        self.hass = hass
        self.session = async_get_clientsession(hass)

    async def validate_openai(self, api_key: str) -> Optional[str]:
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json',
        }
        try:
            _LOGGER.debug("Validating OpenAI API key")
            response = await self.session.get("https://api.openai.com/v1/models", headers=headers)
            if response.status == 200:
                return None  # Success
            else:
                error_text = await response.text()
                _LOGGER.error(f"OpenAI validation error response: {error_text}")
                try:
                    error_json = await response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                except Exception:
                    error_message = error_text
                return error_message
        except Exception as err:
            _LOGGER.error(f"OpenAI validation exception: {err}")
            return str(err)

    async def validate_anthropic(self, api_key: str, model: str) -> Optional[str]:
        headers = {
            'x-api-key': api_key,
            'anthropic-version': VERSION_ANTHROPIC,
            'content-type': 'application/json'
        }
        try:
            _LOGGER.debug("Validating Anthropic API key")
            response = await self.session.post(
                "https://api.anthropic.com/v1/complete",
                headers=headers,
                json={
                    "prompt": "\n\nHuman: Hello\n\nAssistant:",
                    "model": model,
                    "max_tokens_to_sample": 1,
                    "temperature": 0.5,
                    "stop_sequences": ["\n\nHuman:"]
                }
            )
            if response.status == 200:
                return None  # Success
            else:
                error_text = await response.text()
                _LOGGER.error(f"Anthropic validation error response: {error_text}")
                try:
                    error_json = await response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                except Exception:
                    error_message = error_text
                return error_message
        except Exception as err:
            _LOGGER.error(f"Anthropic validation exception: {err}")
            return str(err)

    async def validate_google(self, api_key: str, model: str) -> Optional[str]:
        headers = {'Content-Type': 'application/json'}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "Hello"}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 100, "topK": 40, "topP": 0.95}
        }
        try:
            _LOGGER.debug(f"Validating Google API key with model: {model}")
            response = await self.session.post(url, headers=headers, json=payload)
            if response.status == 200:
                return None  # Success
            else:
                error_text = await response.text()
                _LOGGER.error(f"Google validation error response: {error_text}")
                try:
                    error_json = await response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                except Exception:
                    error_message = error_text
                return error_message
        except Exception as err:
            _LOGGER.error(f"Google validation exception: {err}")
            return str(err)

    async def validate_groq(self, api_key: str) -> Optional[str]:
        headers = {'Authorization': f"Bearer {api_key}", 'Content-Type': 'application/json'}
        try:
            _LOGGER.debug("Validating Groq API key")
            response = await self.session.get("https://api.groq.com/openai/v1/models", headers=headers)
            if response.status == 200:
                return None  # Success
            else:
                error_text = await response.text()
                _LOGGER.error(f"Groq validation error response: {error_text}")
                try:
                    error_json = await response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                except Exception:
                    error_message = error_text
                return error_message
        except Exception as err:
            _LOGGER.error(f"Groq validation exception: {err}")
            return str(err)

    async def validate_localai(self, ip_address: str, port: int, https: bool = False) -> Optional[str]:
        protocol = "https" if https else "http"
        url = f"{protocol}://{ip_address}:{port}/v1/models"
        try:
            _LOGGER.debug(f"Validating LocalAI connection to {url}")
            response = await self.session.get(url)
            if response.status == 200:
                return None  # Success
            else:
                error_text = await response.text()
                _LOGGER.error(f"LocalAI validation error response: {error_text}")
                return f"HTTP {response.status}: {error_text}"
        except Exception as err:
            _LOGGER.error(f"LocalAI validation exception: {err}")
            return str(err)

    async def validate_ollama(self, ip_address: str, port: int, https: bool = False) -> Optional[str]:
        protocol = "https" if https else "http"
        url = f"{protocol}://{ip_address}:{port}/api/tags"
        try:
            _LOGGER.debug(f"Validating Ollama connection to {url}")
            response = await self.session.get(url)
            if response.status == 200:
                return None  # Success
            else:
                error_text = await response.text()
                _LOGGER.error(f"Ollama validation error response: {error_text}")
                return f"HTTP {response.status}: {error_text}"
        except Exception as err:
            _LOGGER.error(f"Ollama validation exception: {err}")
            return str(err)

    async def validate_custom_openai(self, endpoint: str, api_key: Optional[str]) -> Optional[str]:
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
        try:
            _LOGGER.debug(f"Validating Custom OpenAI endpoint {endpoint}")
            response = await self.session.get(f"{endpoint}/v1/models", headers=headers)
            if response.status == 200:
                return None  # Success
            else:
                error_text = await response.text()
                _LOGGER.error(f"Custom OpenAI validation error response: {error_text}")
                try:
                    error_json = await response.json()
                    error_message = error_json.get("error", {}).get("message", error_text)
                except Exception:
                    error_message = error_text
                return error_message
        except Exception as err:
            _LOGGER.error(f"Custom OpenAI validation exception: {err}")
            return str(err)


class AIAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI Automation Suggester integration."""

    VERSION = 1

    def __init__(self):
        self.provider = None
        self.data = {}
        self.validator = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return AIAutomationOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        if user_input is not None:
            self.provider = user_input[CONF_PROVIDER]
            self.data.update(user_input)
            # Check if provider is already configured
            existing_entries = self._async_current_entries()
            for entry in existing_entries:
                if entry.data.get(CONF_PROVIDER) == self.provider:
                    errors["base"] = "already_configured"
                    break
            if not errors:
                provider_steps = {
                    "OpenAI": self.async_step_openai,
                    "Anthropic": self.async_step_anthropic,
                    "Google": self.async_step_google,
                    "Groq": self.async_step_groq,
                    "LocalAI": self.async_step_localai,
                    "Ollama": self.async_step_ollama,
                    "Custom OpenAI": self.async_step_custom_openai,
                    "Mistral AI": self.async_step_mistral,
                }
                return await provider_steps[self.provider]()
        providers = ["OpenAI", "Anthropic", "Google", "Groq", "LocalAI", "Ollama", "Custom OpenAI", "Mistral AI"]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_PROVIDER): vol.In(providers)}),
            errors=errors
        )

    async def async_step_openai(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        description_placeholders = {}
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            error_message = await self.validator.validate_openai(user_input[CONF_OPENAI_API_KEY])
            if error_message is None:
                self.data.update(user_input)
                return self.async_create_entry(title="AI Automation Suggester (OpenAI)", data=self.data)
            else:
                errors["base"] = "api_error"
                description_placeholders["error_message"] = error_message
        return self.async_show_form(
            step_id="openai",
            data_schema=vol.Schema({
                vol.Required(CONF_OPENAI_API_KEY): str,
                vol.Optional(CONF_OPENAI_MODEL, default=DEFAULT_MODELS["OpenAI"]): str,
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS):
                    vol.All(vol.Coerce(int), vol.Range(min=100)),
            }),
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_anthropic(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        description_placeholders = {}
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            model = user_input.get(CONF_ANTHROPIC_MODEL, DEFAULT_MODELS["Anthropic"])
            error_message = await self.validator.validate_anthropic(api_key=user_input[CONF_ANTHROPIC_API_KEY], model=model)
            if error_message is None:
                self.data.update(user_input)
                return self.async_create_entry(title="AI Automation Suggester (Anthropic)", data=self.data)
            else:
                errors["base"] = "api_error"
                description_placeholders["error_message"] = error_message
        return self.async_show_form(
            step_id="anthropic",
            data_schema=vol.Schema({
                vol.Required(CONF_ANTHROPIC_API_KEY): str,
                vol.Optional(CONF_ANTHROPIC_MODEL, default=DEFAULT_MODELS["Anthropic"]): str,
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS):
                    vol.All(vol.Coerce(int), vol.Range(min=100)),
            }),
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_google(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        description_placeholders = {}
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            model = user_input.get(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"])
            error_message = await self.validator.validate_google(api_key=user_input[CONF_GOOGLE_API_KEY], model=model)
            if error_message is None:
                self.data.update(user_input)
                return self.async_create_entry(title="AI Automation Suggester (Google)", data=self.data)
            else:
                errors["base"] = "api_error"
                description_placeholders["error_message"] = error_message
        return self.async_show_form(
            step_id="google",
            data_schema=vol.Schema({
                vol.Required(CONF_GOOGLE_API_KEY): str,
                vol.Optional(CONF_GOOGLE_MODEL, default=DEFAULT_MODELS["Google"]): str,
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS):
                    vol.All(vol.Coerce(int), vol.Range(min=100)),
            }),
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_groq(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        description_placeholders = {}
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            error_message = await self.validator.validate_groq(user_input[CONF_GROQ_API_KEY])
            if error_message is None:
                self.data.update(user_input)
                return self.async_create_entry(title="AI Automation Suggester (Groq)", data=self.data)
            else:
                errors["base"] = "api_error"
                description_placeholders["error_message"] = error_message
        return self.async_show_form(
            step_id="groq",
            data_schema=vol.Schema({
                vol.Required(CONF_GROQ_API_KEY): str,
                vol.Optional(CONF_GROQ_MODEL, default=DEFAULT_MODELS["Groq"]): str,
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS):
                    vol.All(vol.Coerce(int), vol.Range(min=100)),
            }),
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_localai(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        description_placeholders = {}
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            error_message = await self.validator.validate_localai(
                user_input[CONF_LOCALAI_IP_ADDRESS],
                user_input[CONF_LOCALAI_PORT],
                user_input[CONF_LOCALAI_HTTPS]
            )
            if error_message is None:
                self.data.update(user_input)
                return self.async_create_entry(title="AI Automation Suggester (LocalAI)", data=self.data)
            else:
                errors["base"] = "api_error"
                description_placeholders["error_message"] = error_message
        return self.async_show_form(
            step_id="localai",
            data_schema=vol.Schema({
                vol.Required(CONF_LOCALAI_IP_ADDRESS): str,
                vol.Required(CONF_LOCALAI_PORT, default=8080): int,
                vol.Required(CONF_LOCALAI_HTTPS, default=False): bool,
                vol.Optional(CONF_LOCALAI_MODEL, default=DEFAULT_MODELS["LocalAI"]): str,
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS):
                    vol.All(vol.Coerce(int), vol.Range(min=100)),
            }),
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_ollama(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        description_placeholders = {}
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            error_message = await self.validator.validate_ollama(
                user_input[CONF_OLLAMA_IP_ADDRESS],
                user_input[CONF_OLLAMA_PORT],
                user_input[CONF_OLLAMA_HTTPS]
            )
            if error_message is None:
                self.data.update(user_input)
                return self.async_create_entry(title="AI Automation Suggester (Ollama)", data=self.data)
            else:
                errors["base"] = "api_error"
                description_placeholders["error_message"] = error_message
        return self.async_show_form(
            step_id="ollama",
            data_schema=vol.Schema({
                vol.Required(CONF_OLLAMA_IP_ADDRESS): str,
                vol.Required(CONF_OLLAMA_PORT, default=11434): int,
                vol.Required(CONF_OLLAMA_HTTPS, default=False): bool,
                vol.Optional(CONF_OLLAMA_MODEL, default=DEFAULT_MODELS["Ollama"]): str,
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS):
                    vol.All(vol.Coerce(int), vol.Range(min=100)),
            }),
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_custom_openai(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        description_placeholders = {}
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            api_key = user_input.get(CONF_CUSTOM_OPENAI_API_KEY)
            endpoint = user_input[CONF_CUSTOM_OPENAI_ENDPOINT]
            error_message = await self.validator.validate_custom_openai(endpoint=endpoint, api_key=api_key)
            if error_message is None:
                self.data.update(user_input)
                return self.async_create_entry(title="AI Automation Suggester (Custom OpenAI)", data=self.data)
            else:
                errors["base"] = "api_error"
                description_placeholders["error_message"] = error_message
        return self.async_show_form(
            step_id="custom_openai",
            data_schema=vol.Schema({
                vol.Required(CONF_CUSTOM_OPENAI_ENDPOINT): str,
                vol.Optional(CONF_CUSTOM_OPENAI_API_KEY): str,
                vol.Optional(CONF_CUSTOM_OPENAI_MODEL, default=DEFAULT_MODELS["Custom OpenAI"]): str,
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS):
                    vol.All(vol.Coerce(int), vol.Range(min=100)),
            }),
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_mistral(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            return self.async_create_entry(title="AI Automation Suggester (Mistral AI)", data=self.data)
        return self.async_show_form(
            step_id="mistral",
            data_schema=vol.Schema({
                vol.Required(CONF_MISTRAL_API_KEY): str,
                vol.Required(CONF_MISTRAL_MODEL, default="mistral-large-latest"): str,
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS):
                    vol.All(vol.Coerce(int), vol.Range(min=100)),
            }),
            errors=errors
        )


class AIAutomationOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the AI Automation Suggester."""

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        provider = self.config_entry.data.get(CONF_PROVIDER)
        options = {
            vol.Optional(
                CONF_MAX_TOKENS,
                default=self.config_entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            ): vol.All(vol.Coerce(int), vol.Range(min=100))
        }
        if provider == "OpenAI":
            options[vol.Optional(CONF_OPENAI_API_KEY)] = str
            options[vol.Optional(CONF_OPENAI_MODEL, default=self.config_entry.data.get(CONF_OPENAI_MODEL, DEFAULT_MODELS["OpenAI"]))] = str
        elif provider == "Anthropic":
            options[vol.Optional(CONF_ANTHROPIC_API_KEY)] = str
            options[vol.Optional(CONF_ANTHROPIC_MODEL, default=self.config_entry.data.get(CONF_ANTHROPIC_MODEL, DEFAULT_MODELS["Anthropic"]))] = str
        elif provider == "Google":
            options[vol.Optional(CONF_GOOGLE_API_KEY)] = str
            options[vol.Optional(CONF_GOOGLE_MODEL, default=self.config_entry.data.get(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"]))] = str
        elif provider == "Groq":
            options[vol.Optional(CONF_GROQ_API_KEY)] = str
            options[vol.Optional(CONF_GROQ_MODEL, default=self.config_entry.data.get(CONF_GROQ_MODEL, DEFAULT_MODELS["Groq"]))] = str
        elif provider == "LocalAI":
            options[vol.Optional(CONF_LOCALAI_HTTPS)] = bool
            options[vol.Optional(CONF_LOCALAI_MODEL, default=self.config_entry.data.get(CONF_LOCALAI_MODEL, DEFAULT_MODELS["LocalAI"]))] = str
        elif provider == "Ollama":
            options[vol.Optional(CONF_OLLAMA_HTTPS)] = bool
            options[vol.Optional(CONF_OLLAMA_MODEL, default=self.config_entry.data.get(CONF_OLLAMA_MODEL, DEFAULT_MODELS["Ollama"]))] = str
        elif provider == "Custom OpenAI":
            options[vol.Optional(CONF_CUSTOM_OPENAI_ENDPOINT)] = str
            options[vol.Optional(CONF_CUSTOM_OPENAI_API_KEY)] = str
            options[vol.Optional(CONF_CUSTOM_OPENAI_MODEL, default=self.config_entry.data.get(CONF_CUSTOM_OPENAI_MODEL, DEFAULT_MODELS["Custom OpenAI"]))] = str
        elif provider == "Mistral AI":
            options[vol.Required(CONF_MISTRAL_API_KEY)] = str
            options[vol.Required(CONF_MISTRAL_MODEL, default=self.config_entry.data.get(CONF_MISTRAL_MODEL, "mistral-large-latest"))] = str

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options)
        )

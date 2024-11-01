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
)

_LOGGER = logging.getLogger(__name__)

class ProviderValidator:
    """Validate provider configurations."""
    def __init__(self, hass):
        """Initialize validator."""
        self.hass = hass
        self.session = async_get_clientsession(hass)

    async def validate_openai(self, api_key: str) -> bool:
        """Validate OpenAI configuration."""
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json',
        }
        try:
            _LOGGER.debug("Validating OpenAI API key")
            response = await self.session.get(
                "https://api.openai.com/v1/models",
                headers=headers
            )
            is_valid = response.status == 200
            _LOGGER.debug("OpenAI validation result: %s", is_valid)
            return is_valid
        except Exception as err:
            _LOGGER.error("OpenAI validation error: %s", err)
            return False

    async def validate_anthropic(self, api_key: str) -> bool:
        """Validate Anthropic configuration."""
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
                    "prompt": "\n\nTest",
                    "model": DEFAULT_MODELS["Anthropic"],
                    "max_tokens_to_sample": 1,
                }
            )
            is_valid = response.status == 200
            _LOGGER.debug("Anthropic validation result: %s", is_valid)
            return is_valid
        except Exception as err:
            _LOGGER.error("Anthropic validation error: %s", err)
            return False

    async def validate_google(self, api_key: str) -> bool:
        """Validate Google configuration."""
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json',
        }
        try:
            _LOGGER.debug("Validating Google API key")
            # Placeholder URL; replace with the actual Google API endpoint
            response = await self.session.get(
                "https://api.google.com/v1/models",
                headers=headers
            )
            is_valid = response.status == 200
            _LOGGER.debug("Google validation result: %s", is_valid)
            return is_valid
        except Exception as err:
            _LOGGER.error("Google validation error: %s", err)
            return False

    async def validate_groq(self, api_key: str) -> bool:
        """Validate Groq configuration."""
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json',
        }
        try:
            _LOGGER.debug("Validating Groq API key")
            # Placeholder URL; replace with the actual Groq API endpoint
            response = await self.session.get(
                "https://api.groq.com/v1/models",
                headers=headers
            )
            is_valid = response.status == 200
            _LOGGER.debug("Groq validation result: %s", is_valid)
            return is_valid
        except Exception as err:
            _LOGGER.error("Groq validation error: %s", err)
            return False

    async def validate_localai(
        self, ip_address: str, port: int, https: bool = False
    ) -> bool:
        """Validate LocalAI configuration."""
        protocol = "https" if https else "http"
        url = f"{protocol}://{ip_address}:{port}/v1/models"
        try:
            _LOGGER.debug("Validating LocalAI connection to %s", url)
            response = await self.session.get(url)
            is_valid = response.status == 200
            _LOGGER.debug("LocalAI validation result: %s", is_valid)
            return is_valid
        except Exception as err:
            _LOGGER.error("LocalAI validation error: %s", err)
            return False

    async def validate_ollama(
        self, ip_address: str, port: int, https: bool = False
    ) -> bool:
        """Validate Ollama configuration."""
        protocol = "https" if https else "http"
        url = f"{protocol}://{ip_address}:{port}/api/tags"
        try:
            _LOGGER.debug("Validating Ollama connection to %s", url)
            response = await self.session.get(url)
            is_valid = response.status == 200
            _LOGGER.debug("Ollama validation result: %s", is_valid)
            return is_valid
        except Exception as err:
            _LOGGER.error("Ollama validation error: %s", err)
            return False

class AIAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI Automation Suggester."""
    
    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self.provider = None
        self.data = {}
        self.validator = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return AIAutomationOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self.provider = user_input[CONF_PROVIDER]
            self.data.update(user_input)
            
            # Move to provider-specific configuration
            provider_steps = {
                "OpenAI": self.async_step_openai,
                "Anthropic": self.async_step_anthropic,
                "Google": self.async_step_google,
                "Groq": self.async_step_groq,
                "LocalAI": self.async_step_localai,
                "Ollama": self.async_step_ollama,
                "Custom OpenAI": self.async_step_custom_openai,
            }
            return await provider_steps[self.provider]()

        providers = ["OpenAI", "Anthropic", "Google", "Groq", "LocalAI", "Ollama", "Custom OpenAI"]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_PROVIDER): vol.In(providers),
            }),
            errors=errors
        )

    async def async_step_openai(self, user_input: Optional[Dict[str, Any]] = None):
        """Configure OpenAI settings."""
        errors = {}
        
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            is_valid = await self.validator.validate_openai(user_input[CONF_OPENAI_API_KEY])
            
            if is_valid:
                self.data.update(user_input)
                return self.async_create_entry(
                    title="AI Automation Suggester (OpenAI)",
                    data=self.data
                )
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="openai",
            data_schema=vol.Schema({
                vol.Required(CONF_OPENAI_API_KEY): str,
                vol.Optional(CONF_OPENAI_MODEL, default=DEFAULT_MODELS["OpenAI"]): str,
            }),
            errors=errors
        )

    async def async_step_anthropic(self, user_input: Optional[Dict[str, Any]] = None):
        """Configure Anthropic settings."""
        errors = {}
        
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            is_valid = await self.validator.validate_anthropic(
                user_input[CONF_ANTHROPIC_API_KEY]
            )
            
            if is_valid:
                self.data.update(user_input)
                return self.async_create_entry(
                    title="AI Automation Suggester (Anthropic)",
                    data=self.data
                )
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="anthropic",
            data_schema=vol.Schema({
                vol.Required(CONF_ANTHROPIC_API_KEY): str,
                vol.Optional(CONF_ANTHROPIC_MODEL, default=DEFAULT_MODELS["Anthropic"]): str,
            }),
            errors=errors
        )

    async def async_step_google(self, user_input: Optional[Dict[str, Any]] = None):
        """Configure Google settings."""
        errors = {}
        
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            is_valid = await self.validator.validate_google(user_input[CONF_GOOGLE_API_KEY])
            
            if is_valid:
                self.data.update(user_input)
                return self.async_create_entry(
                    title="AI Automation Suggester (Google)",
                    data=self.data
                )
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="google",
            data_schema=vol.Schema({
                vol.Required(CONF_GOOGLE_API_KEY): str,
                vol.Optional(CONF_GOOGLE_MODEL, default=DEFAULT_MODELS["Google"]): str,
            }),
            errors=errors
        )

    async def async_step_groq(self, user_input: Optional[Dict[str, Any]] = None):
        """Configure Groq settings."""
        errors = {}
        
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            is_valid = await self.validator.validate_groq(user_input[CONF_GROQ_API_KEY])
            
            if is_valid:
                self.data.update(user_input)
                return self.async_create_entry(
                    title="AI Automation Suggester (Groq)",
                    data=self.data
                )
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="groq",
            data_schema=vol.Schema({
                vol.Required(CONF_GROQ_API_KEY): str,
                vol.Optional(CONF_GROQ_MODEL, default=DEFAULT_MODELS["Groq"]): str,
            }),
            errors=errors
        )

    async def async_step_localai(self, user_input: Optional[Dict[str, Any]] = None):
        """Configure LocalAI settings."""
        errors = {}
        
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            is_valid = await self.validator.validate_localai(
                user_input[CONF_LOCALAI_IP_ADDRESS],
                user_input[CONF_LOCALAI_PORT],
                user_input[CONF_LOCALAI_HTTPS]
            )
            
            if is_valid:
                self.data.update(user_input)
                return self.async_create_entry(
                    title="AI Automation Suggester (LocalAI)",
                    data=self.data
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="localai",
            data_schema=vol.Schema({
                vol.Required(CONF_LOCALAI_IP_ADDRESS): str,
                vol.Required(CONF_LOCALAI_PORT, default=8080): int,
                vol.Required(CONF_LOCALAI_HTTPS, default=False): bool,
                vol.Optional(CONF_LOCALAI_MODEL, default=DEFAULT_MODELS["LocalAI"]): str,
            }),
            errors=errors
        )

    async def async_step_ollama(self, user_input: Optional[Dict[str, Any]] = None):
        """Configure Ollama settings."""
        errors = {}
        
        if user_input is not None:
            self.validator = ProviderValidator(self.hass)
            is_valid = await self.validator.validate_ollama(
                user_input[CONF_OLLAMA_IP_ADDRESS],
                user_input[CONF_OLLAMA_PORT],
                user_input[CONF_OLLAMA_HTTPS]
            )
            
            if is_valid:
                self.data.update(user_input)
                return self.async_create_entry(
                    title="AI Automation Suggester (Ollama)",
                    data=self.data
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="ollama",
            data_schema=vol.Schema({
                vol.Required(CONF_OLLAMA_IP_ADDRESS): str,
                vol.Required(CONF_OLLAMA_PORT, default=11434): int,
                vol.Required(CONF_OLLAMA_HTTPS, default=False): bool,
                vol.Optional(CONF_OLLAMA_MODEL, default=DEFAULT_MODELS["Ollama"]): str,
            }),
            errors=errors
        )

    async def async_step_custom_openai(self, user_input: Optional[Dict[str, Any]] = None):
        """Configure Custom OpenAI settings."""
        errors = {}
        
        if user_input is not None:
            # Minimal validation; you can add more if necessary
            self.data.update(user_input)
            return self.async_create_entry(
                title="AI Automation Suggester (Custom OpenAI)",
                data=self.data
            )

        return self.async_show_form(
            step_id="custom_openai",
            data_schema=vol.Schema({
                vol.Required(CONF_CUSTOM_OPENAI_ENDPOINT): str,
                vol.Optional(CONF_CUSTOM_OPENAI_API_KEY): str,
                vol.Optional(CONF_CUSTOM_OPENAI_MODEL, default=DEFAULT_MODELS["Custom OpenAI"]): str,
            }),
            errors=errors
        )

class AIAutomationOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the AI Automation Suggester."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        provider = self.config_entry.data.get(CONF_PROVIDER)
        options = {}

        # Add provider-specific options including model selection
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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options)
        )

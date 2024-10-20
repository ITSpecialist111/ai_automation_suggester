"""Config flow for AI Automation Suggester integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AIAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI Automation Suggester."""

    VERSION = 1.02

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate API key if using cloud AI
            if not user_input.get("use_local_ai") and not user_input.get("openai_api_key"):
                errors["openai_api_key"] = "required"
            else:
                return self.async_create_entry(title="AI Automation Suggester", data=user_input)

        data_schema = vol.Schema({
            vol.Required("scan_frequency", default=24): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required("use_local_ai", default=False): bool,
            vol.Optional("openai_api_key"): str,
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AIAutomationOptionsFlowHandler(config_entry)


class AIAutomationOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the AI Automation Suggester options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Required("scan_frequency", default=self.config_entry.options.get("scan_frequency", 24)):
                vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required("use_local_ai", default=self.config_entry.options.get("use_local_ai", False)): bool,
            vol.Optional("openai_api_key", default=self.config_entry.options.get("openai_api_key", "")): str,
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)

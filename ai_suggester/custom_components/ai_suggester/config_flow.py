"""Config flow for AI Suggester integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class AISuggesterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI Suggester."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate API key
            api_key = user_input.get("api_key")
            if await self._test_api_key(api_key):
                return self.async_create_entry(title="AI Suggester", data=user_input)
            else:
                errors["base"] = "invalid_api_key"

        data_schema = vol.Schema({
            vol.Required("api_key"): str,
            vol.Optional("scan_frequency", default=24): int,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_api_key(self, api_key):
        """Test if the provided API key is valid."""
        # Implement API key validation logic here
        return True  # Assuming the key is valid

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AISuggesterOptionsFlow(config_entry)

class AISuggesterOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Optional("scan_frequency", default=self.config_entry.options.get("scan_frequency", 24)): int,
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)

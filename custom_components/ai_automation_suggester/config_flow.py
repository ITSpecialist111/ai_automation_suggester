"""Config flow for AI Automation Suggester integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AIAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI Automation Suggester."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                # Validate API key if using cloud AI
                if not user_input.get("use_local_ai") and not user_input.get("openai_api_key"):
                    errors["openai_api_key"] = "required"
                else:
                    # Validate the OpenAI API key
                    if not user_input.get("use_local_ai"):
                        await self.hass.async_add_executor_job(
                            self.validate_openai_api_key,
                            user_input.get("openai_api_key")
                        )
                    return self.async_create_entry(title="AI Automation Suggester", data=user_input)
            except ValueError as e:
                _LOGGER.error(f"Error during config flow: {e}")
                errors["base"] = "invalid_api_key"
            except Exception as e:
                _LOGGER.error(f"Unexpected error during config flow: {e}")
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required("scan_frequency", default=24): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required("use_local_ai", default=False): bool,
            vol.Optional("openai_api_key"): str,
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    def validate_openai_api_key(self, api_key):
        """Validate the OpenAI API key."""
        import openai
        openai.api_key = api_key
        try:
            openai.Engine.list()
        except openai.error.AuthenticationError:
            raise ValueError("Invalid OpenAI API key")
        except Exception as e:
            raise e

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return AIAutomationOptionsFlowHandler(config_entry)


class AIAutomationOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the AI Automation Suggester options."""
        errors = {}
        if user_input is not None:
            try:
                # Validate API key if using cloud AI
                if not user_input.get("use_local_ai") and not user_input.get("openai_api_key"):
                    errors["openai_api_key"] = "required"
                else:
                    # Validate the OpenAI API key
                    if not user_input.get("use_local_ai"):
                        await self.hass.async_add_executor_job(
                            self.validate_openai_api_key,
                            user_input.get("openai_api_key")
                        )
                    return self.async_create_entry(title="", data=user_input)
            except ValueError as e:
                _LOGGER.error(f"Error during options flow: {e}")
                errors["base"] = "invalid_api_key"
            except Exception as e:
                _LOGGER.error(f"Unexpected error during options flow: {e}")
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required("scan_frequency", default=self.config_entry.options.get("scan_frequency", 24)):
                vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required("use_local_ai", default=self.config_entry.options.get("use_local_ai", False)): bool,
            vol.Optional("openai_api_key", default=self.config_entry.options.get("openai_api_key", "")): str,
        })

        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)

    def validate_openai_api_key(self, api_key):
        """Validate the OpenAI API key."""
        import openai
        openai.api_key = api_key
        try:
            openai.Engine.list()
        except openai.error.AuthenticationError:
            raise ValueError("Invalid OpenAI API key")
        except Exception as e:
            raise e

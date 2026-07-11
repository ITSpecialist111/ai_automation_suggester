"""The AI Automation Suggester integration."""
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers.typing import ConfigType

from .api import async_register_http_views
from .const import (
    ATTR_CUSTOM_PROMPT,
    ATTR_PROVIDER_CONFIG,
    CONF_PROVIDER,
    CONFIG_VERSION,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_HISTORY,
    SERVICE_GENERATE_SUGGESTIONS,
    SERVICE_UPDATE_SUGGESTION,
)
from .coordinator import AIAutomationCoordinator
from .error_utils import sanitize_provider_error
from .store import async_get_suggestion_store

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry if necessary."""
    _LOGGER.debug(f"async_migrate_entry {config_entry.version}")
    # Currently, no migration logic beyond ensuring version matches CONFIG_VERSION
    if config_entry.version < CONFIG_VERSION:
        _LOGGER.debug(f"Migrating config entry from version {config_entry.version} to {CONFIG_VERSION}")
        new_data = {**config_entry.data}
        new_data.pop('scan_frequency', None)
        new_data.pop('initial_lag_time', None)
        hass.config_entries.async_update_entry(config_entry, data=new_data, version=CONFIG_VERSION)
        _LOGGER.debug("Migration successful")
        return True
    return True


def _listish(value):
    """Schema helper for service fields that can be a CSV string, list, or object."""

    if value is None:
        return []
    if isinstance(value, (str, list, tuple, dict)):
        return value
    raise vol.Invalid("expected a list, comma-separated string, or object")


GENERATE_SUGGESTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_PROVIDER_CONFIG): str,
        vol.Optional(ATTR_CUSTOM_PROMPT): str,
        vol.Optional("all_entities", default=False): bool,
        vol.Optional("domains", default=[]): _listish,
        vol.Optional("exclude_domains", default=[]): _listish,
        vol.Optional("exclude_entities", default=[]): _listish,
        vol.Optional("exclude_areas", default=[]): _listish,
        vol.Optional("entity_limit", default=200): vol.All(vol.Coerce(int), vol.Range(min=1, max=2000)),
        vol.Optional("automation_read_yaml", default=False): bool,
        vol.Optional("automation_limit", default=100): vol.All(vol.Coerce(int), vol.Range(min=0, max=1000)),
        vol.Optional("script_read_yaml", default=False): bool,
        vol.Optional("script_limit", default=100): vol.All(vol.Coerce(int), vol.Range(min=0, max=1000)),
    }
)


UPDATE_SUGGESTION_SCHEMA = vol.Schema(
    {
        vol.Required("suggestion_id"): str,
        vol.Required("status"): vol.In(["accepted", "declined", "dismissed", "new"]),
    }
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AI Automation Suggester component."""
    hass.data.setdefault(DOMAIN, {})
    async_register_http_views(hass)

    async def handle_generate_suggestions(call: ServiceCall) -> None:
        """Handle the generate_suggestions service call."""
        try:
            coordinator = None
            provider_config = call.data.get(ATTR_PROVIDER_CONFIG)
            if provider_config:
                coordinator = hass.data[DOMAIN].get(provider_config)
            else:
                # Find first available coordinator if none specified
                for coord in hass.data[DOMAIN].values():
                    if isinstance(coord, AIAutomationCoordinator):
                        coordinator = coord
                        break

            if coordinator is None:
                raise ServiceValidationError("No AI Automation Suggester provider configured")

            await coordinator.async_generate_suggestions(
                custom_prompt=call.data.get(ATTR_CUSTOM_PROMPT),
                all_entities=call.data.get("all_entities", False),
                domains=call.data.get("domains", []),
                exclude_domains=call.data.get("exclude_domains", []),
                exclude_entities=call.data.get("exclude_entities", []),
                exclude_areas=call.data.get("exclude_areas", []),
                entity_limit=call.data.get("entity_limit", 200),
                automation_read_yaml=call.data.get("automation_read_yaml", False),
                automation_limit=call.data.get("automation_limit", 100),
                script_read_yaml=call.data.get("script_read_yaml", False),
                script_limit=call.data.get("script_limit", 100),
            )

        except ServiceValidationError:
            raise
        except KeyError as err:
            raise ServiceValidationError("Provider configuration not found") from err
        except Exception as err:
            safe_error = sanitize_provider_error(err)
            raise ServiceValidationError(f"Failed to generate suggestions: {safe_error}") from err

    async def handle_clear_history(call: ServiceCall) -> None:
        """Clear stored suggestion history."""

        await async_get_suggestion_store(hass).async_clear()

    async def handle_update_suggestion(call: ServiceCall) -> None:
        """Update a stored suggestion status."""

        suggestion = await async_get_suggestion_store(hass).async_update_status(
            call.data["suggestion_id"], call.data["status"]
        )
        if suggestion is None:
            raise ServiceValidationError("Suggestion not found")

    # Register the service
    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_SUGGESTIONS,
        handle_generate_suggestions,
        schema=GENERATE_SUGGESTIONS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_HISTORY,
        handle_clear_history,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_SUGGESTION,
        handle_update_suggestion,
        schema=UPDATE_SUGGESTION_SCHEMA,
    )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AI Automation Suggester from a config entry."""
    try:
        if CONF_PROVIDER not in entry.data:
            raise ConfigEntryNotReady("Provider not specified in config")

        coordinator = AIAutomationCoordinator(hass, entry)
        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Use the new async_forward_entry_setups method (plural) instead of the deprecated async_forward_entry_setup.
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        _LOGGER.debug(
            "Setup complete for %s with provider %s",
            entry.title,
            entry.data.get(CONF_PROVIDER)
        )

        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        @callback
        def handle_custom_event(event):
            _LOGGER.debug("Received custom event '%s', triggering suggestions with all_entities=True", event.event_type)
            hass.async_create_task(coordinator_request_all_suggestions())

        async def coordinator_request_all_suggestions():
            await coordinator.async_generate_suggestions(all_entities=True)

        entry.async_on_unload(hass.bus.async_listen("ai_automation_suggester_update", handle_custom_event))

        return True

    except Exception as err:
        _LOGGER.error("Failed to setup integration: %s", err)
        raise ConfigEntryNotReady from err

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)
        return unload_ok
    except Exception as err:
        _LOGGER.error("Error unloading entry: %s", err)
        return False

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry.

    Delegates to ``hass.config_entries.async_reload`` so the core reload path
    runs ``entry.async_on_unload`` callbacks (which detach the update listener
    registered in :func:`async_setup_entry`). Calling ``async_unload_entry``
    directly bypassed those callbacks, so every options save appended another
    listener and eventually locked up the event loop (issue #175).
    """
    await hass.config_entries.async_reload(entry.entry_id)

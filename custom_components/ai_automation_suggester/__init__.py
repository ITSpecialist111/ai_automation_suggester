# custom_components/ai_automation_suggester/__init__.py

"""The AI Automation Suggester integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_PROVIDER,
    SERVICE_GENERATE_SUGGESTIONS,
    ATTR_PROVIDER_CONFIG,
    ATTR_CUSTOM_PROMPT,
)
from .coordinator import AIAutomationCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1.07:
        # Already up to date
        return True

    # Handle migration from version 1.06 or earlier
    if config_entry.version <= 1.07:
        new_data = {**config_entry.data}
        
        # Add any new required fields with defaults
        if "scan_frequency" not in new_data:
            new_data["scan_frequency"] = DEFAULT_SCAN_FREQUENCY
        if "initial_lag_time" not in new_data:
            new_data["initial_lag_time"] = DEFAULT_INITIAL_LAG_TIME

        config_entry.version = 1.08
        hass.config_entries.async_update_entry(config_entry, data=new_data)

    return True

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AI Automation Suggester component."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_generate_suggestions(call: ServiceCall) -> None:
        """Handle the generate_suggestions service call."""
        provider_config = call.data.get(ATTR_PROVIDER_CONFIG)
        custom_prompt = call.data.get(ATTR_CUSTOM_PROMPT)
        
        try:
            coordinator = None
            if provider_config:
                coordinator = hass.data[DOMAIN][provider_config]
            else:
                for entry_id, coord in hass.data[DOMAIN].items():
                    if isinstance(coord, AIAutomationCoordinator):
                        coordinator = coord
                        break

            if coordinator is None:
                raise ServiceValidationError("No AI Automation Suggester provider configured")

            if custom_prompt:
                original_prompt = coordinator.SYSTEM_PROMPT
                try:
                    coordinator.SYSTEM_PROMPT = custom_prompt
                    await coordinator.async_request_refresh()
                finally:
                    coordinator.SYSTEM_PROMPT = original_prompt
            else:
                await coordinator.async_request_refresh()

        except KeyError:
            raise ServiceValidationError(f"Provider configuration not found")
        except Exception as err:
            raise ServiceValidationError(f"Failed to generate suggestions: {err}")

    # Register the service
    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_SUGGESTIONS,
        handle_generate_suggestions
    )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AI Automation Suggester from a config entry."""
    try:
        # Ensure required config values are present
        if CONF_PROVIDER not in entry.data:
            raise ConfigEntryNotReady("Provider not specified in config")

        # Create and store coordinator
        coordinator = AIAutomationCoordinator(hass, entry)
        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Set up platforms
        for platform in PLATFORMS:
            try:
                await hass.config_entries.async_forward_entry_setup(entry, platform)
            except Exception as err:
                _LOGGER.error("Failed to setup platform %s: %s", platform, err)
                raise ConfigEntryNotReady from err

        _LOGGER.debug(
            "Setup complete for %s with provider %s", 
            entry.title, 
            entry.data.get(CONF_PROVIDER)
        )

        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
        
        return True

    except Exception as err:
        _LOGGER.error("Failed to setup integration: %s", err)
        raise ConfigEntryNotReady from err

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        # Unload platforms
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        
        if unload_ok:
            # Clean up coordinator
            coordinator = hass.data[DOMAIN].pop(entry.entry_id)
            await coordinator.async_shutdown()

        return unload_ok

    except Exception as err:
        _LOGGER.error("Error unloading entry: %s", err)
        return False

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

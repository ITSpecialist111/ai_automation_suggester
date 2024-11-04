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

CURRENT_VERSION = 2  # Internal version number (1.0.9 = version 2)

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    # Convert old decimal versions to new integer version
    if isinstance(config_entry.version, float):
        old_version = config_entry.version
        if old_version <= 1.08:
            config_entry.version = 1
        _LOGGER.debug("Converted decimal version %s to integer version %s", 
                     old_version, config_entry.version)

    if config_entry.version == 1:
        _LOGGER.debug("Migrating config entry from version 1 to version 2")
        new_data = {**config_entry.data}
        
        # Remove old scheduling fields that are no longer used
        new_data.pop('scan_frequency', None)
        new_data.pop('initial_lag_time', None)
        
        # Update to current version
        config_entry.version = CURRENT_VERSION
        hass.config_entries.async_update_entry(config_entry, data=new_data)
        
        _LOGGER.debug("Migration to version %s successful", config_entry.version)
        return True

    _LOGGER.debug("No migration required for version %s", config_entry.version)
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
                # Find first available coordinator if no specific one is specified
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
        if CONF_PROVIDER not in entry.data:
            raise ConfigEntryNotReady("Provider not specified in config")

        coordinator = AIAutomationCoordinator(hass, entry)
        hass.data[DOMAIN][entry.entry_id] = coordinator

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
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        
        if unload_ok:
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
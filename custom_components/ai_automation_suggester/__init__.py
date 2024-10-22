"""The AI Automation Suggester integration."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, PLATFORMS
from .coordinator import AIAutomationCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the AI Automation Suggester component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up AI Automation Suggester from a config entry."""
    coordinator = AIAutomationCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_generate_suggestions(call):
        """Handle the service call to generate suggestions."""
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "generate_suggestions", handle_generate_suggestions)

    return True

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug(f"Starting migration for entry version {entry.version}")

    if entry.version == 1:
        # Example: If moving from version 1 to 2, make changes to the data
        new_data = {**entry.data}
        
        # Handle any changes in your schema or structure
        if 'scan_frequency' not in new_data:
            new_data['scan_frequency'] = 24  # Set a default scan frequency if it doesn't exist

        if 'initial_lag_time' not in new_data:
            new_data['initial_lag_time'] = 10  # Add default lag time if missing

        # Update the entry data
        entry.version = 2
        hass.config_entries.async_update_entry(entry, data=new_data)

        _LOGGER.info(f"Migration to version {entry.version} successful")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

# custom_components/ai_automation_suggester/sensor.py
"""Sensor platform for AI Automation Suggester."""

from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import (
    DOMAIN,
    CONF_PROVIDER,
    PROVIDER_STATUS_CONNECTED,
    PROVIDER_STATUS_DISCONNECTED,
    PROVIDER_STATUS_ERROR,
)

_LOGGER = logging.getLogger(__name__)

SUGGESTION_SENSOR = SensorEntityDescription(
    key="suggestions",
    name="AI Automation Suggestions",
    icon="mdi:robot",
)

STATUS_SENSOR = SensorEntityDescription(
    key="status",
    name="AI Provider Status",
    icon="mdi:check-network",
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AI Automation Suggester sensors."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AISuggestionsSensor(coordinator, entry, SUGGESTION_SENSOR),
        AIProviderStatusSensor(coordinator, entry, STATUS_SENSOR),
    ]
    async_add_entities(entities, True)
    _LOGGER.debug("Sensor platform setup complete")


# ─────────────────────────────────────────────────────────────
# Suggestions sensor
# ─────────────────────────────────────────────────────────────
class AISuggestionsSensor(CoordinatorEntity, SensorEntity):
    """Shows the availability of new AI suggestions and exposes them as attributes."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"AI Automation Suggester ({entry.data.get(CONF_PROVIDER, 'unknown')})",
            "manufacturer": "Community",
            "model": entry.data.get(CONF_PROVIDER, "unknown"),
            "sw_version": entry.version,
        }
        self._entry = entry
        self._previous_suggestions: str | None = None
        self._attr_native_value = "No Suggestions"

    @property
    def name(self) -> str:
        provider = self._entry.data.get(CONF_PROVIDER, "unknown")
        return f"AI Automation Suggestions ({provider})"

    @property
    def native_value(self) -> str:
        data = self.coordinator.data or {}
        suggestions = data.get("suggestions")

        if suggestions in (None, "No suggestions available", "No suggestions yet"):
            return "No Suggestions"

        if suggestions != self._previous_suggestions:
            return "New Suggestions Available"

        return "Suggestions Available"

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "suggestions": data.get("suggestions", "No suggestions available"),
            "description": data.get("description"),
            "yaml_block": data.get("yaml_block"),
            "last_update": data.get("last_update"),
            "entities_processed": data.get("entities_processed", []),
            "provider": self._entry.data.get(CONF_PROVIDER, "unknown"),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """React to coordinator updates by refreshing state."""
        if self.coordinator.data:
            suggestions = self.coordinator.data.get("suggestions")
            if suggestions and suggestions != self._previous_suggestions:
                self._previous_suggestions = suggestions
                self._attr_native_value = self.native_value
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        _LOGGER.debug("Suggestions sensor registered")


# ─────────────────────────────────────────────────────────────
# Provider‑status sensor
# ─────────────────────────────────────────────────────────────
class AIProviderStatusSensor(CoordinatorEntity, SensorEntity):
    """Indicates whether the configured provider is reachable and shows last error."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"AI Automation Suggester ({entry.data.get(CONF_PROVIDER, 'unknown')})",
            "manufacturer": "Community",
            "model": entry.data.get(CONF_PROVIDER, "unknown"),
            "sw_version": entry.version,
        }
        self._entry = entry
        self._attr_native_value = STATE_UNKNOWN
        self._last_error: str | None = None

    @property
    def name(self) -> str:
        provider = self._entry.data.get(CONF_PROVIDER, "unknown")
        return f"AI Provider Status ({provider})"

    def _compute_status(self) -> str:
        if not self.coordinator.last_update:
            return PROVIDER_STATUS_DISCONNECTED
        data = self.coordinator.data or {}
        return PROVIDER_STATUS_CONNECTED if "suggestions" in data else PROVIDER_STATUS_ERROR

    @property
    def extra_state_attributes(self) -> dict:
        return {"last_error": self._last_error}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update status and last_error attribute."""
        data = self.coordinator.data or {}
        self._last_error = data.get("last_error")
        self._attr_native_value = self._compute_status()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        _LOGGER.debug("Provider status sensor registered")

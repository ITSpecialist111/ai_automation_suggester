"""Sensor platform for AI Automation Suggester."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AISuggestionsSensor(coordinator)], True)


class AISuggestionsSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display AI suggestions."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "AI Automation Suggestions"
        self._attr_unique_id = "ai_automation_suggestions_sensor"
        self._attr_icon = "mdi:robot"

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return "Suggestions Available"
        return "No Suggestions"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {"suggestions": self.coordinator.data}

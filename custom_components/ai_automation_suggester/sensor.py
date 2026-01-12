# custom_components/ai_automation_suggester/sensor.py
"""Sensor platform for AI Automation Suggester."""

from __future__ import annotations

import logging
from typing import cast

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    INTEGRATION_NAME,
    CONF_PROVIDER,
    PROVIDER_STATUS_CONNECTED,
    PROVIDER_STATUS_DISCONNECTED,
    PROVIDER_STATUS_ERROR,
    PROVIDER_STATUS_INITIALIZING,
    CONF_MAX_INPUT_TOKENS,
    DEFAULT_MAX_INPUT_TOKENS,
    CONF_MAX_OUTPUT_TOKENS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TIMEOUT,
    CONF_TIMEOUT,
    CONF_MODEL,
    CONF_OPENAI_AZURE_DEPLOYMENT_ID,
    DEFAULT_MODELS,
    CONF_TEMPERATURE,
    DEFAULT_TEMPERATURE,
    # Sensor Keys from const.py
    SENSOR_KEY_SUGGESTIONS,
    SENSOR_KEY_STATUS,
    SENSOR_KEY_INPUT_TOKENS,
    SENSOR_KEY_OUTPUT_TOKENS,
    SENSOR_KEY_MODEL,
    SENSOR_KEY_LAST_ERROR,
    SENSOR_KEY_TIMEOUT,
    SENSOR_KEY_TEMPERATURE,
    MAX_ATTRIBUTE_SIZE,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=SENSOR_KEY_SUGGESTIONS,
        name="AI Automation Suggestions",
        icon="mdi:robot-happy-outline",
    ),
    SensorEntityDescription(
        key=SENSOR_KEY_STATUS,
        name="AI Provider Status",
        icon="mdi:lan-check",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key=SENSOR_KEY_INPUT_TOKENS,
        name="Max Input Tokens",
        icon="mdi:format-letter-starts-with",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="tokens",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SENSOR_KEY_OUTPUT_TOKENS,
        name="Max Output Tokens",
        icon="mdi:format-letter-ends-with",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="tokens",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SENSOR_KEY_MODEL,
        name="AI Model In Use",
        icon="mdi:brain",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key=SENSOR_KEY_LAST_ERROR,
        name="Last Error Message",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key=SENSOR_KEY_TIMEOUT,
        name="Timeout (seconds)",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="seconds",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SENSOR_KEY_TEMPERATURE,
        name="Temperature",
        icon="mdi:thermometer",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AI Automation Suggester sensors from a config entry."""
    coordinator = cast(DataUpdateCoordinator, hass.data[DOMAIN][entry.entry_id])
    provider_name = entry.data.get(CONF_PROVIDER, "Unknown Provider")

    entities: list[SensorEntity] = []
    for description in SENSOR_DESCRIPTIONS:
        formatted_name = f"{description.name} ({provider_name})"
        specific_description = SensorEntityDescription(
            key=description.key,
            name=formatted_name,
            icon=description.icon,
            entity_category=description.entity_category,
            native_unit_of_measurement=description.native_unit_of_measurement,
            state_class=description.state_class,
            device_class=description.device_class,
        )

        if description.key == SENSOR_KEY_SUGGESTIONS:
            entities.append(AISuggestionsSensor(coordinator, entry, specific_description))
        elif description.key == SENSOR_KEY_STATUS:
            entities.append(AIProviderStatusSensor(coordinator, entry, specific_description))
        elif description.key == SENSOR_KEY_INPUT_TOKENS:
            entities.append(MaxInputTokensSensor(coordinator, entry, specific_description))
        elif description.key == SENSOR_KEY_OUTPUT_TOKENS:
            entities.append(MaxOutputTokensSensor(coordinator, entry, specific_description))
        elif description.key == SENSOR_KEY_MODEL:
            entities.append(AIModelSensor(coordinator, entry, specific_description))
        elif description.key == SENSOR_KEY_LAST_ERROR:
            entities.append(AILastErrorSensor(coordinator, entry, specific_description))
        elif description.key == SENSOR_KEY_TIMEOUT:
            entities.append(TimeoutSensor(coordinator, entry, specific_description))
        elif description.key == SENSOR_KEY_TEMPERATURE:
            entities.append(TemperatureSensor(coordinator, entry, specific_description))
        else:
            entities.append(AIBaseSensor(coordinator, entry, specific_description))


    async_add_entities(entities, True)
    _LOGGER.debug("Sensor platform setup complete for provider: %s", provider_name)

# ─────────────────────────────────────────────────────────────
# Base sensor
# ─────────────────────────────────────────────────────────────
class AIBaseSensor(CoordinatorEntity[DataUpdateCoordinator], SensorEntity):
    """Base class for AI Automation Suggester sensors."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._entry = entry
        self._provider_name = entry.data.get(CONF_PROVIDER, "Unknown Provider")

        # Common device info for all sensors of this config entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"{INTEGRATION_NAME} ({self._provider_name})",
            manufacturer="Community",
            model=self._provider_name,
            sw_version=str(entry.version) if entry.version else "N/A",
            configuration_url=None, # Link Github?
        )

    @property
    def available(self) -> bool:
        """Return True if coordinator is available and has data."""
        return super().available and self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.last_update_success:
            self._update_state_and_attributes()
        super()._handle_coordinator_update()

    def _update_state_and_attributes(self) -> None:
        """Update the sensor's state and attributes based on coordinator data.

        This method should be overridden by subclasses.
        """
        self._attr_native_value = STATE_UNKNOWN
        _LOGGER.debug(
            "Sensor %s._update_state_and_attributes not fully implemented for key %s",
            self.__class__.__name__,
            self.entity_description.key
        )

# ─────────────────────────────────────────────────────────────
# Suggestions sensor
# ─────────────────────────────────────────────────────────────
class AISuggestionsSensor(AIBaseSensor):
    """Shows the availability of new AI suggestions."""
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)
        self._previous_suggestions_timestamp: float | None = None

        # Initialize state with default values
        self._attr_native_value = "No Suggestions"
        self._attr_extra_state_attributes = {
            "suggestions": "No suggestions yet",
            "description": None,
            "yaml_block": None,
            "debug_prompt": None,
            "last_update": None,
            "entities_processed": [],
            "provider": self._entry.data.get(CONF_PROVIDER, "unknown"),
            "entities_processed_count": 0,
        }

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()

        # Update initial state from coordinator if data exists
        if self.coordinator.data:
            self._update_state_and_attributes()


    def _update_state_and_attributes(self) -> None:
        """Update sensor state and attributes."""
        data = self.coordinator.data or {}
        suggestions = data.get("suggestions")
        last_update_timestamp = data.get("last_update")

        if suggestions and suggestions not in ("No suggestions available", "No suggestions yet"):
            if last_update_timestamp and (self._previous_suggestions_timestamp is None or last_update_timestamp > self._previous_suggestions_timestamp):
                self._attr_native_value = "New Suggestions Available"
                self._previous_suggestions_timestamp = last_update_timestamp
            else:
                self._attr_native_value = "Suggestions Available"
        else:
            self._attr_native_value = "No Suggestions"

        def truncate(val):
            if isinstance(val, str) and len(val) > MAX_ATTRIBUTE_SIZE:
                return val[:MAX_ATTRIBUTE_SIZE] + "... (truncated)"
            return val

        self._attr_extra_state_attributes = {
            "suggestions": suggestions,
            "description": truncate(data.get("description")),
            "yaml_block": truncate(data.get("yaml_block")),
            "debug_prompt": truncate(data.get("debug_prompt")),
            "last_update": data.get("last_update"),
            "entities_processed": data.get("entities_processed", [])[:50],  # Limit to 50 entities
            "provider": self._entry.data.get(CONF_PROVIDER, "unknown"),
            "entities_processed_count": len(data.get("entities_processed", [])),
        }

# ─────────────────────────────────────────────────────────────
# Provider‑status sensor
# ─────────────────────────────────────────────────────────────
class AIProviderStatusSensor(AIBaseSensor):
    """Indicates whether the configured provider is reachable."""
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)
        self._update_state_and_attributes()

    def _update_state_and_attributes(self) -> None:
        """Update sensor state and attributes."""
        data = self.coordinator.data or {}
        if not self.coordinator.last_update_success:
            self._attr_native_value = PROVIDER_STATUS_ERROR
        elif not data:
            self._attr_native_value = PROVIDER_STATUS_INITIALIZING
        elif data.get("last_error"):
            self._attr_native_value = PROVIDER_STATUS_ERROR
        elif "suggestions" in data:
             self._attr_native_value = PROVIDER_STATUS_CONNECTED
        else:
            self._attr_native_value = PROVIDER_STATUS_DISCONNECTED

        def truncate(val):
            if isinstance(val, str) and len(val) > MAX_ATTRIBUTE_SIZE:
                return val[:MAX_ATTRIBUTE_SIZE] + "... (truncated)"
            return val

        self._attr_extra_state_attributes = {
            "last_error_message": truncate(data.get("last_error")),
            "last_attempted_update": data.get("last_update"),
        }

# ─────────────────────────────────────────────────────────────
# Max Input Token Sensors
# ─────────────────────────────────────────────────────────────
class MaxInputTokensSensor(AIBaseSensor):
    """Shows the configured maximum input tokens."""
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)
        self._update_state_and_attributes() # Initial update

    def _update_state_and_attributes(self) -> None:
        """Update sensor state from config entry options or data."""
        self._attr_native_value = self._entry.options.get(
            CONF_MAX_INPUT_TOKENS,
            self._entry.data.get(CONF_MAX_INPUT_TOKENS, DEFAULT_MAX_INPUT_TOKENS)
        )

# ─────────────────────────────────────────────────────────────
# Max Output Token Sensors
# ─────────────────────────────────────────────────────────────
class MaxOutputTokensSensor(AIBaseSensor):
    """Shows the configured maximum output tokens."""
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)
        self._update_state_and_attributes() # Initial update

    def _update_state_and_attributes(self) -> None:
        """Update sensor state from config entry options or data."""
        self._attr_native_value = self._entry.options.get(
            CONF_MAX_OUTPUT_TOKENS,
            self._entry.data.get(CONF_MAX_OUTPUT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS)
        )

# ─────────────────────────────────────────────────────────────
# Model Sensor
# ─────────────────────────────────────────────────────────────
class AIModelSensor(AIBaseSensor):
    """Shows the currently configured AI model."""
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)
        self._update_state_and_attributes()

    def _update_state_and_attributes(self) -> None:
        """Update sensor state with the configured model."""
        provider = self._entry.data.get(CONF_PROVIDER)
        if not provider:
            self._attr_native_value = STATE_UNKNOWN
            return

        if provider == "OpenAI Azure":
            model_key = CONF_OPENAI_AZURE_DEPLOYMENT_ID
        else:
            model_key = CONF_MODEL

        self._attr_native_value = self._entry.options.get(
            model_key,
            self._entry.data.get(model_key, DEFAULT_MODELS.get(provider, "unknown"))
        )

# ─────────────────────────────────────────────────────────────
# Last Error sensor
# ─────────────────────────────────────────────────────────────
class AILastErrorSensor(AIBaseSensor):
    """Shows the last error message from the AI provider."""
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)
        self._update_state_and_attributes() # Initial update

    def _update_state_and_attributes(self) -> None:
        """Update sensor state with the last error message."""
        data = self.coordinator.data or {}
        last_error = data.get("last_error")
        def truncate(val):
            if isinstance(val, str) and len(val) > MAX_ATTRIBUTE_SIZE:
                return val[:MAX_ATTRIBUTE_SIZE] + "... (truncated)"
            return val

        self._attr_native_value = str(last_error)[:254] if last_error else "No Error"
        self._attr_extra_state_attributes = {
             "last_error_timestamp": data.get("last_update") if last_error else None,
             "full_error": truncate(str(last_error)) if last_error else None,
        }

# ─────────────────────────────────────────────────────────────
# Timeout sensor
# ─────────────────────────────────────────────────────────────
class TimeoutSensor(AIBaseSensor):
    """Shows the configured timeout for AI requests."""
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)
        self._update_state_and_attributes()  # Initial update

    def _update_state_and_attributes(self) -> None:
        """Update sensor state with the configured timeout."""
        self._attr_native_value = self._entry.options.get(
            "timeout",
            self._entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)  # Default to 30 seconds if not set
        )

# ─────────────────────────────────────────────────────────────
# Temperature sensor
# ─────────────────────────────────────────────────────────────
class TemperatureSensor(AIBaseSensor):
    """Shows the configured temperature for AI requests."""
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, description)
        self._update_state_and_attributes()  # Initial update

    def _update_state_and_attributes(self) -> None:
        """Update sensor state with the configured temperature."""
        self._attr_native_value = self._entry.options.get(
            CONF_TEMPERATURE,
            self._entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
        )

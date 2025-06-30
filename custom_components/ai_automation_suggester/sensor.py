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
    # Model configuration keys (used to display current model)
    CONF_OPENAI_MODEL,
    CONF_ANTHROPIC_MODEL,
    CONF_GOOGLE_MODEL,
    CONF_GROQ_MODEL,
    CONF_LOCALAI_MODEL,
    CONF_OLLAMA_MODEL,
    CONF_CUSTOM_OPENAI_MODEL,
    CONF_MISTRAL_MODEL,
    CONF_PERPLEXITY_MODEL,
    CONF_OPENROUTER_MODEL,
    CONF_OPENAI_AZURE_DEPLOYMENT_ID,
    CONF_GENERIC_OPENAI_MODEL,
    DEFAULT_MODELS,
    # Sensor Keys from const.py
    SENSOR_KEY_SUGGESTIONS,
    SENSOR_KEY_STATUS,
    SENSOR_KEY_INPUT_TOKENS,
    SENSOR_KEY_OUTPUT_TOKENS,
    SENSOR_KEY_MODEL,
    SENSOR_KEY_LAST_ERROR,
)

_LOGGER = logging.getLogger(__name__)

PROVIDER_TO_MODEL_KEY_MAP: dict[str, str] = {
    "OpenAI": CONF_OPENAI_MODEL,
    "Anthropic": CONF_ANTHROPIC_MODEL,
    "Google": CONF_GOOGLE_MODEL,
    "Groq": CONF_GROQ_MODEL,
    "LocalAI": CONF_LOCALAI_MODEL,
    "Ollama": CONF_OLLAMA_MODEL,
    "Custom OpenAI": CONF_CUSTOM_OPENAI_MODEL,
    "Mistral AI": CONF_MISTRAL_MODEL,
    "Perplexity AI": CONF_PERPLEXITY_MODEL,
    "OpenRouter": CONF_OPENROUTER_MODEL,
    "OpenAI Azure": CONF_OPENAI_AZURE_DEPLOYMENT_ID,
    "Generic OpenAI": CONF_GENERIC_OPENAI_MODEL,
}

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

        self._attr_extra_state_attributes = {
            "suggestions": suggestions,
            "description": data.get("description"),
            "yaml_block": data.get("yaml_block"),
            "last_update": data.get("last_update"),
            "entities_processed": data.get("entities_processed", []),
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

        self._attr_extra_state_attributes = {
            "last_error_message": data.get("last_error", None),
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

        model_key = PROVIDER_TO_MODEL_KEY_MAP.get(provider)
        if not model_key:
            self._attr_native_value = "Unknown Model Key"
            _LOGGER.warning("No model key found for provider: %s", provider)
            return

        self._attr_native_value = self._entry.options.get(
            model_key,
            self._entry.data.get(model_key, DEFAULT_MODELS.get(provider, "unknown"))
        ) if model_key else "unknown"

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
        self._attr_native_value = str(last_error) if last_error else "No Error"
        self._attr_extra_state_attributes = {
             "last_error_timestamp": data.get("last_update") if last_error else None,
        }

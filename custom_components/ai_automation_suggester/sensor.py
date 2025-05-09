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
    CONF_MAX_INPUT_TOKENS, 
    DEFAULT_MAX_INPUT_TOKENS,
    CONF_MAX_OUTPUT_TOKENS, 
    DEFAULT_MAX_OUTPUT_TOKENS,
    CONF_OPENAI_MODEL,
    CONF_ANTHROPIC_MODEL,
    CONF_GOOGLE_MODEL,
    CONF_GROQ_MODEL,
    CONF_LOCALAI_MODEL,
    CONF_OLLAMA_MODEL,
    CONF_CUSTOM_OPENAI_MODEL,
    CONF_MISTRAL_MODEL,
    CONF_PERPLEXITY_MODEL,
    DEFAULT_MODELS,
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

MAX_INPUT_TOKENS_SENSOR = SensorEntityDescription(
    key="input_tokens",
    name="Max Input Tokens",
    icon="mdi:numeric",
    entity_category=EntityCategory.DIAGNOSTIC,
)

MAX_OUTPUT_TOKENS_SENSOR = SensorEntityDescription(
    key="output_tokens",
    name="Max Output Tokens",
    icon="mdi:numeric",
    entity_category=EntityCategory.DIAGNOSTIC,
)

MODEL_SENSOR = SensorEntityDescription(
    key="model",
    name="AI Model",
    icon="mdi:brain",
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AI Automation Suggester sensors."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AISuggestionsSensor(coordinator, entry, SUGGESTION_SENSOR),
        AIProviderStatusSensor(coordinator, entry, STATUS_SENSOR),
        InputTokensSensor(coordinator, entry, MAX_INPUT_TOKENS_SENSOR),
        OutputTokensSensor(coordinator, entry, MAX_OUTPUT_TOKENS_SENSOR),
        AIModelSensor(coordinator, entry, MODEL_SENSOR), 
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
            "name": f"AI Automation Suggester ({entry.data.get(CONF_PROVIDER, "unknown")})",
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
            "name": f"AI Automation Suggester ({entry.data.get(CONF_PROVIDER, "unknown")})",
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

# ─────────────────────────────────────────────────────────────
# Token Sensors
# ─────────────────────────────────────────────────────────────
class InputTokensSensor(CoordinatorEntity, SensorEntity):
    """Shows the configured maximum input tokens."""

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
            "name": f"AI Automation Suggester ({entry.data.get(CONF_PROVIDER, "unknown")})",
            "manufacturer": "Community",
            "model": entry.data.get(CONF_PROVIDER, "unknown"),
            "sw_version": entry.version,
        }
        self._entry = entry
        self._attr_native_value = entry.options.get(
            CONF_MAX_INPUT_TOKENS, 
            entry.data.get(CONF_MAX_INPUT_TOKENS, DEFAULT_MAX_INPUT_TOKENS)
        )

    @property
    def name(self) -> str:
        provider = self._entry.data.get(CONF_PROVIDER, "unknown")
        return f"Max Input Tokens ({provider})"
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Update when options change."""
        self._attr_native_value = self._entry.options.get(
            CONF_MAX_INPUT_TOKENS, 
            self._entry.data.get(CONF_MAX_INPUT_TOKENS, DEFAULT_MAX_INPUT_TOKENS)
        )
        self.async_write_ha_state()    

class OutputTokensSensor(CoordinatorEntity, SensorEntity):
    """Shows the configured maximum output tokens."""

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
            "name": f"AI Automation Suggester ({entry.data.get(CONF_PROVIDER, "unknown")})",
            "manufacturer": "Community",
            "model": entry.data.get(CONF_PROVIDER, "unknown"),
            "sw_version": entry.version,
        }
        self._entry = entry
        self._attr_native_value = entry.options.get(
            CONF_MAX_OUTPUT_TOKENS, 
            entry.data.get(CONF_MAX_OUTPUT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS)
        )


    @property
    def name(self) -> str:
        provider = self._entry.data.get(CONF_PROVIDER, "unknown")
        return f"Max Output Tokens ({provider})"
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Update when options change."""
        self._attr_native_value = self._entry.options.get(
            CONF_MAX_OUTPUT_TOKENS, 
            self._entry.data.get(CONF_MAX_OUTPUT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS)
        )
        self.async_write_ha_state()

# ─────────────────────────────────────────────────────────────
# Model Sensor
# ─────────────────────────────────────────────────────────────
class AIModelSensor(CoordinatorEntity, SensorEntity):
    """Shows the currently configured AI model."""

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
            "name": f"AI Automation Suggester ({entry.data.get(CONF_PROVIDER, "unknown")})",
            "manufacturer": "Community",
            "model": entry.data.get(CONF_PROVIDER, "unknown"),
            "sw_version": entry.version,
        }
        self._entry = entry
        provider = entry.data.get(CONF_PROVIDER, "unknown")
        # Determinamos qué clave de modelo usar según el proveedor
        model_key = {
            "OpenAI": CONF_OPENAI_MODEL,
            "Anthropic": CONF_ANTHROPIC_MODEL,
            "Google": CONF_GOOGLE_MODEL,
            "Groq": CONF_GROQ_MODEL,
            "LocalAI": CONF_LOCALAI_MODEL,
            "Ollama": CONF_OLLAMA_MODEL,
            "Custom OpenAI": CONF_CUSTOM_OPENAI_MODEL,
            "Mistral AI": CONF_MISTRAL_MODEL,
            "Perplexity AI": CONF_PERPLEXITY_MODEL,
        }.get(provider)
        
        # Obtenemos el modelo configurado o el valor por defecto
        self._attr_native_value = entry.options.get(
            model_key, 
            entry.data.get(model_key, DEFAULT_MODELS.get(provider, "unknown"))
        ) if model_key else "unknown"

    @property
    def name(self) -> str:
        provider = self._entry.data.get(CONF_PROVIDER, "unknown")
        return f"AI Model ({provider})"
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Update when options change."""
        provider = self._entry.data.get(CONF_PROVIDER, "unknown")
        model_key = {
            "OpenAI": CONF_OPENAI_MODEL,
            "Anthropic": CONF_ANTHROPIC_MODEL,
            "Google": CONF_GOOGLE_MODEL,
            "Groq": CONF_GROQ_MODEL,
            "LocalAI": CONF_LOCALAI_MODEL,
            "Ollama": CONF_OLLAMA_MODEL,
            "Custom OpenAI": CONF_CUSTOM_OPENAI_MODEL,
            "Mistral AI": CONF_MISTRAL_MODEL,
            "Perplexity AI": CONF_PERPLEXITY_MODEL,
        }.get(provider)
        
        self._attr_native_value = self._entry.options.get(
            model_key, 
            self._entry.data.get(model_key, DEFAULT_MODELS.get(provider, "unknown"))
        ) if model_key else "unknown"
        
        self.async_write_ha_state()


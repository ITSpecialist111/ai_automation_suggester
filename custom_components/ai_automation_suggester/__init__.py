"""The AI Automation Suggester integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_PROVIDER,
    SERVICE_GENERATE_SUGGESTIONS,
    SERVICE_ANALYZE_ERROR,
    ATTR_PROVIDER_CONFIG,
    ATTR_CUSTOM_PROMPT,
    CONFIG_VERSION
)
from .coordinator import AIAutomationCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry if necessary."""
    if config_entry.version == 1:
        _LOGGER.info("Migrating config entry from version 1 to 2")
        new_data = {**config_entry.data}

        # Mapping from old provider-specific keys to new common keys
        key_mappings = {
            "openai_api_key": "api_key",
            "openai_model": "model",
            "openai_temperature": "temperature",
            "anthropic_api_key": "api_key",
            "anthropic_model": "model",
            "anthropic_temperature": "temperature",
            "google_api_key": "api_key",
            "google_model": "model",
            "google_temperature": "temperature",
            "groq_api_key": "api_key",
            "groq_model": "model",
            "groq_temperature": "temperature",
            "localai_model": "model",
            "localai_temperature": "temperature",
            "ollama_model": "model",
            "ollama_temperature": "temperature",
            "custom_openai_model": "model",
            "custom_openai_temperature": "temperature",
            "mistral_api_key": "api_key",
            "mistral_model": "model",
            "mistral_temperature": "temperature",
            "perplexity_api_key": "api_key",
            "perplexity_model": "model",
            "perplexity_temperature": "temperature",
            "openrouter_api_key": "api_key",
            "openrouter_model": "model",
            "openrouter_temperature": "temperature",
            "openai_azure_api_key": "api_key",
            "openai_azure_temperature": "temperature",
            "generic_openai_model": "model",
            "generic_openai_temperature": "temperature",
            "custom_openai_api_key": "api_key",
            "generic_openai_api_key": "api_key",
            "conf_codestral_api_key": "api_key",
            "conf_veniceai_api_key": "api_key",
            "conf_veniceai_temperature": "temperature",
            "conf_codestral_temperature": "temperature",
            "openwebui_model": "model",
            "openwebui_temperature": "temperature",
        }

        # Perform the migration
        for old_key, new_key in key_mappings.items():
            if old_key in new_data:
                new_data[new_key] = new_data.pop(old_key)

        # Update both data and version using async_update_entry
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            version=2
        )
        _LOGGER.info("Migration to version 2 successful")

    return True

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AI Automation Suggester component."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_generate_suggestions(call: ServiceCall) -> None:
        """Handle the generate_suggestions service call."""
        provider_config = call.data.get(ATTR_PROVIDER_CONFIG)
        custom_prompt = call.data.get(ATTR_CUSTOM_PROMPT)
        all_entities = call.data.get("all_entities", False)
        domains = call.data.get("domains", {})
        entity_limit = call.data.get("entity_limit", 200)
        automation_read_yaml = call.data.get("automation_read_yaml", False)
        automation_limit = call.data.get("automation_limit", 100)
        script_read_yaml = call.data.get("script_read_yaml", False)
        script_limit = call.data.get("script_limit", 100)
        include_entity_details = call.data.get("include_entity_details", True)
        debug_mode = call.data.get("debug_mode", False)

        # Parse domains if provided as a string or dict
        if isinstance(domains, str):
            domains = [d.strip() for d in domains.split(',') if d.strip()]
        elif isinstance(domains, dict):
            domains = list(domains.keys())

        try:
            coordinator = None
            if provider_config:
                coordinator = hass.data[DOMAIN].get(provider_config)
            else:
                # Find first available coordinator if none specified
                for entry_id, coord in hass.data[DOMAIN].items():
                    if isinstance(coord, AIAutomationCoordinator):
                        coordinator = coord
                        break

            if coordinator is None:
                raise ServiceValidationError("No AI Automation Suggester provider configured")

            if custom_prompt:
                original_prompt = coordinator.SYSTEM_PROMPT
                coordinator.SYSTEM_PROMPT = f"{coordinator.SYSTEM_PROMPT}\n\nAdditional instructions:\n{custom_prompt}"
            else:
                original_prompt = None

            coordinator.scan_all = all_entities
            coordinator.selected_domains = domains
            coordinator.entity_limit = entity_limit
            coordinator.automation_read_file = automation_read_yaml
            coordinator.automation_limit = automation_limit
            coordinator.script_read_file = script_read_yaml
            coordinator.script_limit = script_limit
            coordinator.include_entity_details = include_entity_details
            coordinator.debug_mode = debug_mode

            try:
                await coordinator.async_request_refresh()
            finally:
                if original_prompt is not None:
                    coordinator.SYSTEM_PROMPT = original_prompt
                coordinator.scan_all = False
                coordinator.selected_domains = []
                coordinator.entity_limit = 200
                coordinator.automation_read_file = False
                coordinator.automation_limit = 100
                coordinator.script_read_file = False
                coordinator.script_limit = 100
                coordinator.include_entity_details = True
                coordinator.debug_mode = False

        except KeyError:
            raise ServiceValidationError("Provider configuration not found")
        except Exception as err:
            raise ServiceValidationError(f"Failed to generate suggestions: {err}")

    async def handle_analyze_error(call: ServiceCall) -> None:
        """Handle the analyze_error service call."""
        provider_config = call.data.get(ATTR_PROVIDER_CONFIG)
        error_log = call.data.get("error_log")
        automation_id = call.data.get("automation_id")
        script_id = call.data.get("script_id")
        debug_mode = call.data.get("debug_mode", False)

        if not error_log:
            raise ServiceValidationError("error_log is required")

        try:
            coordinator = None
            if provider_config:
                coordinator = hass.data[DOMAIN].get(provider_config)
            else:
                for entry_id, coord in hass.data[DOMAIN].items():
                    if isinstance(coord, AIAutomationCoordinator):
                        coordinator = coord
                        break

            if coordinator is None:
                raise ServiceValidationError("No AI Automation Suggester provider configured")

            coordinator.debug_mode = debug_mode
            try:
                await coordinator.async_analyze_error(
                    error_log=error_log,
                    automation_id=automation_id,
                    script_id=script_id
                )
            finally:
                coordinator.debug_mode = False

        except KeyError:
            raise ServiceValidationError("Provider configuration not found")
        except Exception as err:
            _LOGGER.exception("Error during analyze_error service call")
            raise ServiceValidationError(f"Failed to analyze error: {err}")

    # Register the services
    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_SUGGESTIONS,
        handle_generate_suggestions
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ANALYZE_ERROR,
        handle_analyze_error
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
            coordinator.scan_all = True
            await coordinator.async_request_refresh()
            coordinator.scan_all = False

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

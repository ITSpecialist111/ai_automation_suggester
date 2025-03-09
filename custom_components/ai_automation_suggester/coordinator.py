# custom_components/ai_automation_suggester/coordinator.py

"""Coordinator for AI Automation Suggester."""
import logging
import random
from datetime import datetime
from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr, entity_registry as er, area_registry as ar

from .const import (
    DOMAIN,
    CONF_PROVIDER,
    DEFAULT_MODELS,
    CONF_MAX_TOKENS,
    CONF_OPENAI_API_KEY,
    CONF_OPENAI_MODEL,
    CONF_ANTHROPIC_API_KEY,
    CONF_ANTHROPIC_MODEL,
    CONF_GOOGLE_API_KEY,
    CONF_GOOGLE_MODEL,
    CONF_GROQ_API_KEY,
    CONF_GROQ_MODEL,
    CONF_LOCALAI_IP_ADDRESS,
    CONF_LOCALAI_PORT,
    CONF_LOCALAI_HTTPS,
    CONF_LOCALAI_MODEL,
    CONF_OLLAMA_IP_ADDRESS,
    CONF_OLLAMA_PORT,
    CONF_OLLAMA_HTTPS,
    CONF_OLLAMA_MODEL,
    CONF_CUSTOM_OPENAI_ENDPOINT,
    CONF_CUSTOM_OPENAI_API_KEY,
    CONF_CUSTOM_OPENAI_MODEL,
    # Mistral AI constants added:
    CONF_MISTRAL_API_KEY,
    CONF_MISTRAL_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    VERSION_ANTHROPIC,
    ENDPOINT_OPENAI,
    ENDPOINT_ANTHROPIC,
    ENDPOINT_GOOGLE,
    ENDPOINT_GROQ,
    ENDPOINT_LOCALAI,
    ENDPOINT_OLLAMA,
    # New Mistral AI endpoint constant:
    ENDPOINT_MISTRAL,
)

_LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI assistant that generates Home Assistant automations 
based on the types of entities, their areas, and their associated devices, as well as 
improving or suggesting new automations based on existing ones.

For each entity:
1. Understand its function, area, and device context.
2. Consider its current state and attributes.
3. Suggest contextually aware automations and improvements to existing automations.
4. Include actual entity IDs in your suggestions.

When focusing on custom aspects (like energy-saving or presence-based lighting), 
integrate those themes into the automations. Provide triggers, conditions, 
and detailed actions to refine the automations according to the instructions given in the custom prompt.

Also consider existing automations and how they can be improved or complemented.
"""

class AIAutomationCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from AI model."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self.previous_entities = {}
        self.last_update = None
        self.SYSTEM_PROMPT = SYSTEM_PROMPT
        self.scan_all = False      # Flag to consider all entities
        self.selected_domains = [] # Filter to specified domains if provided
        self.entity_limit = 200    # Limit number of entities considered

        self.data = {
            "suggestions": "No suggestions yet",
            "last_update": None,
            "entities_processed": [],
            "provider": entry.data.get(CONF_PROVIDER, "unknown")
        }

        # Prevent automatic updates by setting update_interval to None
        self.update_interval = None
        self.session = async_get_clientsession(hass)

        self.device_registry = None
        self.entity_registry = None
        self.area_registry = None

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=self.update_interval)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.device_registry = dr.async_get(self.hass)
        self.entity_registry = er.async_get(self.hass)
        self.area_registry = ar.async_get(self.hass)

    async def _async_update_data(self):
        try:
            current_time = datetime.now()
            _LOGGER.debug("Starting manual update at %s", current_time)

            self.last_update = current_time

            # Fetch current entities
            _LOGGER.debug("Fetching current entities")
            try:
                current_entities = {}
                for entity_id in self.hass.states.async_entity_ids():
                    # If user provided domains to filter, only include those domains
                    if self.selected_domains:
                        domain = entity_id.split('.')[0]
                        if domain not in self.selected_domains:
                            continue

                    state = self.hass.states.get(entity_id)
                    if state is not None:
                        friendly_name = state.attributes.get('friendly_name', entity_id)
                        current_entities[entity_id] = {
                            'state': state.state,
                            'attributes': state.attributes,
                            'last_changed': state.last_changed,
                            'last_updated': state.last_updated,
                            'friendly_name': friendly_name
                        }
            except Exception as err:
                _LOGGER.error("Error fetching entities: %s", err)
                return self.data

            if self.scan_all:
                selected_entities = current_entities
            else:
                # Only consider new entities if scan_all is False
                selected_entities = {
                    k: v for k, v in current_entities.items()
                    if k not in self.previous_entities
                }

            if not selected_entities:
                _LOGGER.debug("No entities selected for suggestions")
                self.previous_entities = current_entities
                return self.data

            ai_input_data = self.prepare_ai_input(selected_entities)
            suggestions = await self.get_ai_suggestions(ai_input_data)

            if suggestions:
                _LOGGER.debug("Received suggestions: %s", suggestions)
                try:
                    persistent_notification.async_create(
                        self.hass,
                        message=suggestions,
                        title="AI Automation Suggestions",
                        notification_id=f"ai_automation_suggestions_{current_time.timestamp()}"
                    )

                    self.data = {
                        "suggestions": suggestions,
                        "last_update": current_time,
                        "entities_processed": list(selected_entities.keys()),
                        "provider": self.entry.data.get(CONF_PROVIDER, "unknown")
                    }

                    await self.hass.services.async_call(
                        "logbook", 
                        "log", 
                        {"name": "AI Automation Suggester", "message": "New suggestions generated"}
                    )

                except Exception as err:
                    _LOGGER.error("Error creating notification: %s", err)
                    self.data = {
                        "suggestions": suggestions,
                        "last_update": current_time,
                        "entities_processed": list(selected_entities.keys()),
                        "provider": self.entry.data.get(CONF_PROVIDER, "unknown")
                    }
            else:
                _LOGGER.warning("No valid suggestions received from AI")
                self.data = {
                    "suggestions": "No suggestions available",
                    "last_update": current_time,
                    "entities_processed": [],
                    "provider": self.entry.data.get(CONF_PROVIDER, "unknown")
                }

            self.previous_entities = current_entities
            return self.data

        except Exception as err:
            _LOGGER.error("Unexpected error in update: %s", err)
            return self.data

    def prepare_ai_input(self, entities):
        _LOGGER.debug("Preparing AI input for %d entities", len(entities))

        MAX_ATTR_LENGTH = 500
        MAX_AUTOMATIONS = 100

        # Randomly pick entities up to entity_limit
        entity_list = list(entities.items())
        selected_entities = random.sample(entity_list, min(len(entity_list), self.entity_limit))

        entities_description = []
        for entity_id, entity_data in selected_entities:
            state = entity_data.get('state', 'unknown')
            attributes = entity_data.get('attributes', {})
            friendly_name = entity_data.get('friendly_name', entity_id)
            domain = entity_id.split('.')[0]

            attr_str = str(attributes)
            if len(attr_str) > MAX_ATTR_LENGTH:
                attr_str = attr_str[:MAX_ATTR_LENGTH] + "...(truncated)"

            ent_reg_entry = self.entity_registry.async_get(entity_id) if self.entity_registry else None
            device_info = None
            area_name = "Unknown Area"
            if ent_reg_entry:
                if ent_reg_entry.device_id and self.device_registry:
                    dev_reg_entry = self.device_registry.async_get(ent_reg_entry.device_id)
                    if dev_reg_entry:
                        device_info = {
                            "manufacturer": dev_reg_entry.manufacturer,
                            "model": dev_reg_entry.model,
                            "name": dev_reg_entry.name_by_user or dev_reg_entry.name,
                            "id": dev_reg_entry.id
                        }

                area_id = ent_reg_entry.area_id or (dev_reg_entry.area_id if dev_reg_entry and dev_reg_entry.area_id else None)
                if area_id and self.area_registry:
                    area_entry = self.area_registry.async_get_area(area_id)
                    if area_entry:
                        area_name = area_entry.name

            description = (
                f"Entity: {entity_id}\n"
                f"Friendly Name: {friendly_name}\n"
                f"Domain: {domain}\n"
                f"State: {state}\n"
                f"Attributes: {attr_str}\n"
                f"Area: {area_name}\n"
            )

            if device_info:
                description += (
                    f"Device Info:\n"
                    f"  Manufacturer: {device_info['manufacturer']}\n"
                    f"  Model: {device_info['model']}\n"
                    f"  Device Name: {device_info['name']}\n"
                    f"  Device ID: {device_info['id']}\n"
                )

            description += (
                f"Last Changed: {entity_data.get('last_changed', 'unknown')}\n"
                f"Last Updated: {entity_data.get('last_updated', 'unknown')}\n"
                f"---\n"
            )
            entities_description.append(description)

        # Gather existing automations, truncated
        automation_entities = []
        for auto_id in self.hass.states.async_entity_ids('automation'):
            state = self.hass.states.get(auto_id)
            if state is not None:
                friendly_name = state.attributes.get('friendly_name', auto_id)
                automation_entities.append({
                    'entity_id': auto_id,
                    'friendly_name': friendly_name,
                    'state': state.state,
                    'attributes': state.attributes
                })

        automation_entities = automation_entities[:MAX_AUTOMATIONS]

        automation_description = "Existing Automations:\n"
        if automation_entities:
            for auto in automation_entities:
                auto_attr_str = str(auto['attributes'])
                if len(auto_attr_str) > MAX_ATTR_LENGTH:
                    auto_attr_str = auto_attr_str[:MAX_ATTR_LENGTH] + "...(truncated)"

                automation_description += (
                    f"Entity: {auto['entity_id']}\n"
                    f"Friendly Name: {auto['friendly_name']}\n"
                    f"State: {auto['state']}\n"
                    f"Attributes: {auto_attr_str}\n"
                    f"---\n"
                )
        else:
            automation_description += "None found.\n"

        prompt = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"Entities in your Home Assistant (randomly selected and possibly domain-filtered):\n"
            f"{''.join(entities_description)}\n\n"
            f"{automation_description}\n\n"
            f"Please suggest detailed, specific automations and improvements, "
            f"considering device and area context. Only reference the entities provided above. "
            f"Adjust triggers, conditions, and actions to refine the automations according to the provided instructions."
        )

        return prompt

    async def get_ai_suggestions(self, prompt):
        provider = self.entry.data.get(CONF_PROVIDER, "OpenAI")
        _LOGGER.debug("Using AI provider: %s", provider)

        try:
            if provider == "OpenAI":
                return await self.process_with_openai(prompt)
            elif provider == "Anthropic":
                return await self.process_with_anthropic(prompt)
            elif provider == "Google":
                return await self.process_with_google(prompt)
            elif provider == "Groq":
                return await self.process_with_groq(prompt)
            elif provider == "LocalAI":
                return await self.process_with_localai(prompt)
            elif provider == "Ollama":
                return await self.process_with_ollama(prompt)
            elif provider == "Custom OpenAI":
                return await self.process_with_custom_openai(prompt)
            elif provider == "Mistral AI":
                return await self.process_with_mistral(prompt)
            else:
                _LOGGER.error("Unknown provider: %s", provider)
                return None
        except Exception as err:
            _LOGGER.error("Error getting suggestions: %s", err)
            return None

    # ------------------------------------------------------------------------
    # Updated process_with_openai for gpt-4o / o1-preview / 03
    # ------------------------------------------------------------------------
    async def process_with_openai(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_OPENAI_API_KEY)
            model = self.entry.data.get(CONF_OPENAI_MODEL, DEFAULT_MODELS["OpenAI"])
            max_tokens_conf = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            if not api_key:
                raise ValueError("OpenAI API key not configured")

            _LOGGER.debug("Making OpenAI API request with model %s", model)

            # Approximate token counting
            def count_tokens(text: str) -> int:
                return len(text) // 4  # rough approximation

            # Hard limit to avoid sending massive prompts (e.g., 32768 tokens)
            HARD_MAX = 32768
            max_tokens_used = min(max_tokens_conf, HARD_MAX)

            prompt_token_count = count_tokens(prompt)
            if prompt_token_count > max_tokens_used:
                _LOGGER.warning(
                    "Prompt is ~%d tokens, exceeding limit %d. Truncating...",
                    prompt_token_count, max_tokens_used
                )
                prompt = prompt[: max_tokens_used * 4]
                prompt_token_count = count_tokens(prompt)

            _LOGGER.debug("Prompt length after truncation: ~%d tokens", prompt_token_count)

            lower_model = model.lower()
            if lower_model in ["gpt-4o", "o1-preview", "o1", "o1-mini", "o1", "o3-mini", "o3", "gpt-4.5"]:
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_completion_tokens": max_tokens_used,
                    "temperature": DEFAULT_TEMPERATURE
                }
            else:
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens_used,
                    "temperature": DEFAULT_TEMPERATURE
                }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            async with self.session.post(ENDPOINT_OPENAI, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("OpenAI API error: %s", error_text)
                    return None

                result = await response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as err:
            _LOGGER.error("Error processing with OpenAI: %s", err)
            return None

    async def process_with_anthropic(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_ANTHROPIC_API_KEY)
            model = self.entry.data.get(CONF_ANTHROPIC_MODEL, DEFAULT_MODELS["Anthropic"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            if not api_key:
                raise ValueError("Anthropic API key not configured")

            _LOGGER.debug("Making Anthropic API request with model %s and max_tokens %d",
                          model, max_tokens)

            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "anthropic-version": VERSION_ANTHROPIC
            }

            data = {
                "model": model,
                "messages": [{
                    "role": "user", 
                    "content": [{"type": "text", "text": prompt}]
                }],
                "max_tokens": max_tokens,
                "temperature": DEFAULT_TEMPERATURE
            }

            async with self.session.post(ENDPOINT_ANTHROPIC, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Anthropic API error: %s", error_text)
                    return None

                result = await response.json()
                return result["content"][0]["text"]

        except Exception as err:
            _LOGGER.error("Error processing with Anthropic: %s", err)
            return None

    # ------------------------------------------------------------------------
    # Updated process_with_google removing gpt-4o / o1-preview checks
    # ------------------------------------------------------------------------
    async def process_with_google(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_GOOGLE_API_KEY)
            model = self.entry.data.get(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"])
            max_tokens = min(self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS), 30720)

            if not api_key:
                raise ValueError("Google API key not configured")

            _LOGGER.debug("Making Google API request with model %s", model)

            def count_tokens(text: str) -> int:
                return len(text) // 4

            prompt_token_count = count_tokens(prompt)
            if prompt_token_count > max_tokens:
                _LOGGER.warning(
                    "Prompt is ~%d tokens, exceeding limit %d. Truncating...",
                    prompt_token_count, max_tokens
                )
                prompt = prompt[: max_tokens * 4]
                prompt_token_count = count_tokens(prompt)

            _LOGGER.debug("Prompt length after truncation: ~%d tokens", prompt_token_count)

            data = {
                "contents": [
                    {"parts": [{"text": prompt}]}
                ],
                "generationConfig": {
                    "temperature": DEFAULT_TEMPERATURE,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": max_tokens
                }
            }

            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}

            async with self.session.post(endpoint, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Google API error: %s", error_text)
                    return None

                result = await response.json()
                try:
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError) as err:
                    _LOGGER.error("Error parsing Google API response: %s", err)
                    return None

        except Exception as err:
            _LOGGER.error("Error processing with Google: %s", err)
            return None

    # ------------------------------------------------------------------------
    async def process_with_groq(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_GROQ_API_KEY)
            model = self.entry.data.get(CONF_GROQ_MODEL, DEFAULT_MODELS["Groq"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            if not api_key:
                raise ValueError("Groq API key not configured")

            _LOGGER.debug("Making Groq API request with model %s and max_tokens %d", model, max_tokens)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            data = {
                "messages": [{
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }],
                "model": model,
                "max_tokens": max_tokens,
                "temperature": DEFAULT_TEMPERATURE
            }

            async with self.session.post(ENDPOINT_GROQ, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Groq API error: %s", error_text)
                    return None

                result = await response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as err:
            _LOGGER.error("Error processing with Groq: %s", err)
            return None

    async def process_with_localai(self, prompt):
        try:
            ip_address = self.entry.data.get(CONF_LOCALAI_IP_ADDRESS)
            port = self.entry.data.get(CONF_LOCALAI_PORT)
            https = self.entry.data.get(CONF_LOCALAI_HTTPS, False)
            model = self.entry.data.get(CONF_LOCALAI_MODEL, DEFAULT_MODELS["LocalAI"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            if not ip_address or not port:
                raise ValueError("LocalAI configuration incomplete")

            protocol = "https" if https else "http"
            endpoint = ENDPOINT_LOCALAI.format(protocol=protocol, ip_address=ip_address, port=port)
            _LOGGER.debug("Making LocalAI API request to %s with model %s and max_tokens %d", endpoint, model, max_tokens)

            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": DEFAULT_TEMPERATURE
            }

            async with self.session.post(endpoint, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("LocalAI API error: %s", error_text)
                    return None

                result = await response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as err:
            _LOGGER.error("Error processing with LocalAI: %s", err)
            return None

    async def process_with_ollama(self, prompt):
        try:
            ip_address = self.entry.data.get(CONF_OLLAMA_IP_ADDRESS)
            port = self.entry.data.get(CONF_OLLAMA_PORT)
            https = self.entry.data.get(CONF_OLLAMA_HTTPS, False)
            model = self.entry.data.get(CONF_OLLAMA_MODEL, DEFAULT_MODELS["Ollama"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            if not ip_address or not port:
                raise ValueError("Ollama configuration incomplete")

            protocol = "https" if https else "http"
            endpoint = ENDPOINT_OLLAMA.format(protocol=protocol, ip_address=ip_address, port=port)
            _LOGGER.debug("Making Ollama API request to %s with model %s and max_tokens %d", endpoint, model, max_tokens)

            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "temperature": DEFAULT_TEMPERATURE,
                    "num_predict": max_tokens
                }
            }

            async with self.session.post(endpoint, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Ollama API error: %s", error_text)
                    return None

                result = await response.json()
                return result["message"]["content"]

        except Exception as err:
            _LOGGER.error("Error processing with Ollama: %s", err)
            return None

    async def process_with_custom_openai(self, prompt):
        try:
            endpoint = self.entry.data.get(CONF_CUSTOM_OPENAI_ENDPOINT)
            api_key = self.entry.data.get(CONF_CUSTOM_OPENAI_API_KEY)
            model = self.entry.data.get(CONF_CUSTOM_OPENAI_MODEL, DEFAULT_MODELS["Custom OpenAI"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            if not endpoint:
                raise ValueError("Custom OpenAI endpoint not configured")

            _LOGGER.debug("Making Custom OpenAI API request to %s with model %s and max_tokens %d", endpoint, model, max_tokens)

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": DEFAULT_TEMPERATURE
            }

            async with self.session.post(endpoint, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Custom OpenAI API error: %s", error_text)
                    return None

                result = await response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as err:
            _LOGGER.error("Error processing with Custom OpenAI: %s", err)
            return None

    # ------------------------------------------------------------------------
    async def process_with_mistral(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_MISTRAL_API_KEY)
            model = self.entry.data.get(CONF_MISTRAL_MODEL, "mistral-medium")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": DEFAULT_TEMPERATURE,
                "max_tokens": 4096
            }
            async with self.session.post(ENDPOINT_MISTRAL, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Mistral AI API error: %s", error_text)
                    return f"Error: {error_text}"
                result = await response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            _LOGGER.error("Error calling Mistral AI API: %s", str(e))
            return f"Error: {str(e)}"
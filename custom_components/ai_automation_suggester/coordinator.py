# custom_components/ai_automation_suggester/coordinator.py
"""Coordinator for AI Automation Suggester."""

import logging
import random
from datetime import datetime

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    # Provider selector
    CONF_PROVIDER,
    DEFAULT_MODELS,
    # Generic limits
    CONF_MAX_TOKENS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    # OpenAI
    CONF_OPENAI_API_KEY,
    CONF_OPENAI_MODEL,
    ENDPOINT_OPENAI,
    # Anthropic
    CONF_ANTHROPIC_API_KEY,
    CONF_ANTHROPIC_MODEL,
    VERSION_ANTHROPIC,
    ENDPOINT_ANTHROPIC,
    # Google
    CONF_GOOGLE_API_KEY,
    CONF_GOOGLE_MODEL,
    ENDPOINT_GOOGLE,
    # Groq
    CONF_GROQ_API_KEY,
    CONF_GROQ_MODEL,
    ENDPOINT_GROQ,
    # LocalAI
    CONF_LOCALAI_IP_ADDRESS,
    CONF_LOCALAI_PORT,
    CONF_LOCALAI_HTTPS,
    CONF_LOCALAI_MODEL,
    ENDPOINT_LOCALAI,
    # Ollama
    CONF_OLLAMA_IP_ADDRESS,
    CONF_OLLAMA_PORT,
    CONF_OLLAMA_HTTPS,
    CONF_OLLAMA_MODEL,
    ENDPOINT_OLLAMA,
    # Custom OpenAI
    CONF_CUSTOM_OPENAI_ENDPOINT,
    CONF_CUSTOM_OPENAI_API_KEY,
    CONF_CUSTOM_OPENAI_MODEL,
    # Mistral
    CONF_MISTRAL_API_KEY,
    CONF_MISTRAL_MODEL,
    ENDPOINT_MISTRAL,
    # Perplexity
    CONF_PERPLEXITY_API_KEY,
    CONF_PERPLEXITY_MODEL,
    ENDPOINT_PERPLEXITY,
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

When focusing on custom aspects (like energy‑saving or presence‑based lighting),
integrate those themes into the automations. Provide triggers, conditions,
and detailed actions to refine the automations according to the instructions given
in the custom prompt.

Also consider existing automations and how they can be improved or complemented.
"""


class AIAutomationCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from AI model."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry

        self.previous_entities = {}
        self.last_update = None

        # Runtime‑tunable flags (set by service call)
        self.SYSTEM_PROMPT = SYSTEM_PROMPT
        self.scan_all = False
        self.selected_domains = []
        self.entity_limit = 200

        self.data = {
            "suggestions": "No suggestions yet",
            "last_update": None,
            "entities_processed": [],
            "provider": entry.data.get(CONF_PROVIDER, "unknown"),
        }

        # manual refresh only
        self.update_interval = None
        self.session = async_get_clientsession(hass)

        self.device_registry = None
        self.entity_registry = None
        self.area_registry = None

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=self.update_interval)

    # ------------------------------------------------------------------
    # HA lifecycle hooks
    # ------------------------------------------------------------------
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.device_registry = dr.async_get(self.hass)
        self.entity_registry = er.async_get(self.hass)
        self.area_registry = ar.async_get(self.hass)

    # ------------------------------------------------------------------
    # Main update routine (called by async_request_refresh)
    # ------------------------------------------------------------------
    async def _async_update_data(self):
        try:
            now = datetime.now()
            _LOGGER.debug("Starting manual update at %s", now)
            self.last_update = now

            # -------- Gather entities ----------
            current_entities = {}
            for entity_id in self.hass.states.async_entity_ids():
                domain = entity_id.split(".")[0]
                if self.selected_domains and domain not in self.selected_domains:
                    continue
                state_obj = self.hass.states.get(entity_id)
                if state_obj is None:
                    continue
                current_entities[entity_id] = {
                    "state": state_obj.state,
                    "attributes": state_obj.attributes,
                    "last_changed": state_obj.last_changed,
                    "last_updated": state_obj.last_updated,
                    "friendly_name": state_obj.attributes.get("friendly_name", entity_id),
                }

            # Determine which entities to send
            if self.scan_all:
                selected_entities = current_entities
            else:
                selected_entities = {k: v for k, v in current_entities.items() if k not in self.previous_entities}

            if not selected_entities:
                _LOGGER.debug("No entities selected for suggestions")
                self.previous_entities = current_entities
                return self.data

            prompt = self.prepare_ai_input(selected_entities)
            suggestions = await self.get_ai_suggestions(prompt)

            if suggestions:
                _LOGGER.debug("Received suggestions")
                persistent_notification.async_create(
                    self.hass,
                    message=suggestions,
                    title="AI Automation Suggestions",
                    notification_id=f"ai_automation_suggestions_{now.timestamp()}",
                )

                self.data = {
                    "suggestions": suggestions,
                    "last_update": now,
                    "entities_processed": list(selected_entities.keys()),
                    "provider": self.entry.data.get(CONF_PROVIDER, "unknown"),
                }

                await self.hass.services.async_call(
                    "logbook", "log", {"name": "AI Automation Suggester", "message": "New suggestions generated"}
                )
            else:
                _LOGGER.warning("No valid suggestions received")
                self.data = {
                    "suggestions": "No suggestions available",
                    "last_update": now,
                    "entities_processed": [],
                    "provider": self.entry.data.get(CONF_PROVIDER, "unknown"),
                }

            self.previous_entities = current_entities
            return self.data

        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Unexpected coordinator error: %s", err)
            return self.data

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------
    def prepare_ai_input(self, entities):
        _LOGGER.debug("Preparing AI input for %d entities", len(entities))

        MAX_ATTR_LENGTH = 500
        MAX_AUTOMATIONS = 100

        # Random subset respecting limit
        picks = random.sample(list(entities.items()), min(len(entities), self.entity_limit))

        entity_sections = []
        for entity_id, meta in picks:
            domain = entity_id.split(".")[0]
            attr_str = str(meta["attributes"])
            if len(attr_str) > MAX_ATTR_LENGTH:
                attr_str = attr_str[:MAX_ATTR_LENGTH] + "...(truncated)"

            ent_entry = self.entity_registry.async_get(entity_id) if self.entity_registry else None
            dev_entry = self.device_registry.async_get(ent_entry.device_id) if ent_entry and ent_entry.device_id else None

            area_id = ent_entry.area_id or (dev_entry.area_id if dev_entry else None)
            area_name = "Unknown Area"
            if area_id and self.area_registry:
                area = self.area_registry.async_get_area(area_id)
                if area:
                    area_name = area.name

            section = (
                f"Entity: {entity_id}\n"
                f"Friendly Name: {meta['friendly_name']}\n"
                f"Domain: {domain}\n"
                f"State: {meta['state']}\n"
                f"Attributes: {attr_str}\n"
                f"Area: {area_name}\n"
            )

            if dev_entry:
                section += (
                    "Device Info:\n"
                    f"  Manufacturer: {dev_entry.manufacturer}\n"
                    f"  Model: {dev_entry.model}\n"
                    f"  Device Name: {dev_entry.name_by_user or dev_entry.name}\n"
                    f"  Device ID: {dev_entry.id}\n"
                )

            section += (
                f"Last Changed: {meta['last_changed']}\n"
                f"Last Updated: {meta['last_updated']}\n"
                f"---\n"
            )
            entity_sections.append(section)

        # Existing automations (truncated list)
        auto_sections = []
        for auto_id in self.hass.states.async_entity_ids("automation")[:MAX_AUTOMATIONS]:
            a_state = self.hass.states.get(auto_id)
            if a_state is None:
                continue
            attr_s = str(a_state.attributes)
            if len(attr_s) > MAX_ATTR_LENGTH:
                attr_s = attr_s[:MAX_ATTR_LENGTH] + "...(truncated)"
            auto_sections.append(
                f"Entity: {auto_id}\n"
                f"Friendly Name: {a_state.attributes.get('friendly_name', auto_id)}\n"
                f"State: {a_state.state}\n"
                f"Attributes: {attr_s}\n"
                f"---\n"
            )

        prompt = (
            f"{self.SYSTEM_PROMPT}\n\n"
            "Entities in your Home Assistant (sampled):\n"
            f"{''.join(entity_sections)}\n"
            "Existing Automations:\n"
            f"{''.join(auto_sections) if auto_sections else 'None found.'}\n\n"
            "Please propose detailed automations and improvements that reference only the entity_ids given above."
        )
        return prompt

    # ------------------------------------------------------------------
    # Provider dispatch
    # ------------------------------------------------------------------
    async def get_ai_suggestions(self, prompt):
        provider = self.entry.data.get(CONF_PROVIDER, "OpenAI")
        _LOGGER.debug("Using AI provider: %s", provider)

        try:
            if provider == "OpenAI":
                return await self.process_with_openai(prompt)
            if provider == "Anthropic":
                return await self.process_with_anthropic(prompt)
            if provider == "Google":
                return await self.process_with_google(prompt)
            if provider == "Groq":
                return await self.process_with_groq(prompt)
            if provider == "LocalAI":
                return await self.process_with_localai(prompt)
            if provider == "Ollama":
                return await self.process_with_ollama(prompt)
            if provider == "Custom OpenAI":
                return await self.process_with_custom_openai(prompt)
            if provider == "Mistral AI":
                return await self.process_with_mistral(prompt)
            if provider == "Perplexity AI":
                return await self.process_with_perplexity(prompt)
            _LOGGER.error("Unknown provider: %s", provider)
            return None
        except Exception as err:
            _LOGGER.error("Error getting suggestions: %s", err)
            return None

    # ------------------------------------------------------------------
    # Individual provider handlers
    # ------------------------------------------------------------------
    async def process_with_openai(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_OPENAI_API_KEY)
            model = self.entry.data.get(CONF_OPENAI_MODEL, DEFAULT_MODELS["OpenAI"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            if not api_key:
                raise ValueError("OpenAI API key not configured")

            if len(prompt) // 4 > max_tok:  # approx tokens
                prompt = prompt[: max_tok * 4]

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tok,
                "temperature": DEFAULT_TEMPERATURE,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            async with self.session.post(ENDPOINT_OPENAI, headers=headers, json=body) as resp:
                if resp.status != 200:
                    _LOGGER.error("OpenAI API error: %s", await resp.text())
                    return None
                result = await resp.json()
                return result["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("OpenAI processing error: %s", err)
            return None

    async def process_with_anthropic(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_ANTHROPIC_API_KEY)
            model = self.entry.data.get(CONF_ANTHROPIC_MODEL, DEFAULT_MODELS["Anthropic"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": VERSION_ANTHROPIC,
            }
            body = {
                "model": model,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                "max_tokens": max_tok,
                "temperature": DEFAULT_TEMPERATURE,
            }

            async with self.session.post(ENDPOINT_ANTHROPIC, headers=headers, json=body) as resp:
                if resp.status != 200:
                    _LOGGER.error("Anthropic API error: %s", await resp.text())
                    return None
                result = await resp.json()
                return result["content"][0]["text"]
        except Exception as err:
            _LOGGER.error("Anthropic processing error: %s", err)
            return None

    async def process_with_google(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_GOOGLE_API_KEY)
            model = self.entry.data.get(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"])
            max_tok = min(self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS), 30720)

            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": DEFAULT_TEMPERATURE,
                    "maxOutputTokens": max_tok,
                    "topK": 40,
                    "topP": 0.95,
                },
            }
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

            async with self.session.post(endpoint, json=body) as resp:
                if resp.status != 200:
                    _LOGGER.error("Google API error: %s", await resp.text())
                    return None
                result = await resp.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as err:
            _LOGGER.error("Google processing error: %s", err)
            return None

    async def process_with_groq(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_GROQ_API_KEY)
            model = self.entry.data.get(CONF_GROQ_MODEL, DEFAULT_MODELS["Groq"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            body = {
                "model": model,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                "max_tokens": max_tok,
                "temperature": DEFAULT_TEMPERATURE,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            async with self.session.post(ENDPOINT_GROQ, headers=headers, json=body) as resp:
                if resp.status != 200:
                    _LOGGER.error("Groq API error: %s", await resp.text())
                    return None
                result = await resp.json()
                return result["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("Groq processing error: %s", err)
            return None

    async def process_with_localai(self, prompt):
        try:
            ip = self.entry.data.get(CONF_LOCALAI_IP_ADDRESS)
            port = self.entry.data.get(CONF_LOCALAI_PORT)
            https = self.entry.data.get(CONF_LOCALAI_HTTPS, False)
            model = self.entry.data.get(CONF_LOCALAI_MODEL, DEFAULT_MODELS["LocalAI"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            proto = "https" if https else "http"
            endpoint = ENDPOINT_LOCALAI.format(protocol=proto, ip_address=ip, port=port)

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tok,
                "temperature": DEFAULT_TEMPERATURE,
            }

            async with self.session.post(endpoint, json=body) as resp:
                if resp.status != 200:
                    _LOGGER.error("LocalAI API error: %s", await resp.text())
                    return None
                result = await resp.json()
                return result["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("LocalAI processing error: %s", err)
            return None

    async def process_with_ollama(self, prompt):
        try:
            ip = self.entry.data.get(CONF_OLLAMA_IP_ADDRESS)
            port = self.entry.data.get(CONF_OLLAMA_PORT)
            https = self.entry.data.get(CONF_OLLAMA_HTTPS, False)
            model = self.entry.data.get(CONF_OLLAMA_MODEL, DEFAULT_MODELS["Ollama"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            proto = "https" if https else "http"
            endpoint = ENDPOINT_OLLAMA.format(protocol=proto, ip_address=ip, port=port)

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": DEFAULT_TEMPERATURE, "num_predict": max_tok},
            }

            async with self.session.post(endpoint, json=body) as resp:
                if resp.status != 200:
                    _LOGGER.error("Ollama API error: %s", await resp.text())
                    return None
                result = await resp.json()
                return result["message"]["content"]
        except Exception as err:
            _LOGGER.error("Ollama processing error: %s", err)
            return None

    async def process_with_custom_openai(self, prompt):
        try:
            endpoint = self.entry.data.get(CONF_CUSTOM_OPENAI_ENDPOINT)
            api_key = self.entry.data.get(CONF_CUSTOM_OPENAI_API_KEY)
            model = self.entry.data.get(CONF_CUSTOM_OPENAI_MODEL, DEFAULT_MODELS["Custom OpenAI"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tok,
                "temperature": DEFAULT_TEMPERATURE,
            }

            async with self.session.post(endpoint, headers=headers, json=body) as resp:
                if resp.status != 200:
                    _LOGGER.error("Custom OpenAI error: %s", await resp.text())
                    return None
                result = await resp.json()
                return result["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("Custom OpenAI processing error: %s", err)
            return None

    async def process_with_mistral(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_MISTRAL_API_KEY)
            model = self.entry.data.get(CONF_MISTRAL_MODEL, "mistral-medium")

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": DEFAULT_TEMPERATURE,
                "max_tokens": 4096,
            }

            async with self.session.post(ENDPOINT_MISTRAL, headers=headers, json=body) as resp:
                if resp.status != 200:
                    _LOGGER.error("Mistral API error: %s", await resp.text())
                    return None
                result = await resp.json()
                return result["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("Mistral processing error: %s", err)
            return None

    # ------------------------------------------------------------------
    # Perplexity AI (NEW)
    # ------------------------------------------------------------------
    async def process_with_perplexity(self, prompt):
        try:
            api_key = self.entry.data.get(CONF_PERPLEXITY_API_KEY)
            model = self.entry.data.get(CONF_PERPLEXITY_MODEL, DEFAULT_MODELS["Perplexity AI"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

            if not api_key:
                raise ValueError("Perplexity API key not configured")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tok,
                "temperature": DEFAULT_TEMPERATURE,
            }

            async with self.session.post(ENDPOINT_PERPLEXITY, headers=headers, json=body) as resp:
                if resp.status != 200:
                    _LOGGER.error("Perplexity API error: %s", await resp.text())
                    return None
                result = await resp.json()
                return result["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("Perplexity processing error: %s", err)
            return None

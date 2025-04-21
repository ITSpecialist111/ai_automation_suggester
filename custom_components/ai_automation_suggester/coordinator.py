# custom_components/ai_automation_suggester/coordinator.py
"""Coordinator for AI Automation Suggester."""

from __future__ import annotations

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
    """Manage calls to the configured AI provider and expose results."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry

        # Track which entities we've already processed
        self.previous_entities: dict[str, dict] = {}
        self.last_update: datetime | None = None

        # Runtime‑tunable flags – overridden temporarily by the service
        self.SYSTEM_PROMPT: str = SYSTEM_PROMPT
        self.scan_all: bool = False
        self.selected_domains: list[str] = []
        self.entity_limit: int = 200

        # Data shared with sensors
        self.data: dict = {
            "suggestions": "No suggestions yet",
            "last_update": None,
            "entities_processed": [],
            "provider": entry.data.get(CONF_PROVIDER, "unknown"),
        }

        # Manual refresh only
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.session = async_get_clientsession(hass)

        # Registries (populated in async_added_to_hass)
        self.device_registry: dr.DeviceRegistry | None = None
        self.entity_registry: er.EntityRegistry | None = None
        self.area_registry: ar.AreaRegistry | None = None

    # ────────────────────────────────
    # Home‑Assistant life‑cycle hooks
    # ────────────────────────────────
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.device_registry = dr.async_get(self.hass)
        self.entity_registry = er.async_get(self.hass)
        self.area_registry = ar.async_get(self.hass)

    async def async_shutdown(self) -> None:  # called by __init__.py on unload
        """Nothing to clean up yet – placeholder for future."""
        return

    # ────────────────────────────────
    # Main polling routine
    # ────────────────────────────────
    async def _async_update_data(self) -> dict:
        try:
            now = datetime.now()
            self.last_update = now
            _LOGGER.debug("Starting manual update at %s", now)

            # ---------- collect entities ----------
            current_entities: dict[str, dict] = {}
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

            # pick new entities (or all, if scan_all True)
            selected = (
                current_entities
                if self.scan_all
                else {e: v for e, v in current_entities.items() if e not in self.previous_entities}
            )
            if not selected:
                _LOGGER.debug("No entities selected for suggestions")
                self.previous_entities = current_entities
                return self.data

            prompt = self._build_prompt(selected)
            suggestions = await self._dispatch(prompt)

            if suggestions:
                persistent_notification.async_create(
                    self.hass,
                    message=suggestions,
                    title="AI Automation Suggestions",
                    notification_id=f"ai_automation_suggestions_{now.timestamp()}",
                )
                self.data = {
                    "suggestions": suggestions,
                    "last_update": now,
                    "entities_processed": list(selected.keys()),
                    "provider": self.entry.data.get(CONF_PROVIDER, "unknown"),
                }
            else:
                self.data.update(
                    {
                        "suggestions": "No suggestions available",
                        "last_update": now,
                        "entities_processed": [],
                    }
                )

            self.previous_entities = current_entities
            return self.data

        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Unexpected coordinator error: %s", err)
            return self.data

    # ────────────────────────────────
    # Prompt builder
    # ────────────────────────────────
    def _build_prompt(self, entities: dict) -> str:
        MAX_ATTR = 500
        MAX_AUTOM = 100

        entity_sections: list[str] = []
        for entity_id, meta in random.sample(list(entities.items()), min(len(entities), self.entity_limit)):
            domain = entity_id.split(".")[0]
            attr_str = str(meta["attributes"])
            if len(attr_str) > MAX_ATTR:
                attr_str = f"{attr_str[:MAX_ATTR]}...(truncated)"

            # ---- registry lookups (safe) ----
            ent_entry = self.entity_registry.async_get(entity_id) if self.entity_registry else None
            dev_entry = (
                self.device_registry.async_get(ent_entry.device_id) if ent_entry and ent_entry.device_id else None
            )

            area_id = (
                ent_entry.area_id
                if ent_entry and ent_entry.area_id
                else (dev_entry.area_id if dev_entry and dev_entry.area_id else None)
            )
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
                "---\n"
            )
            entity_sections.append(section)

        # existing automations (truncate list)
        auto_sections: list[str] = []
        for aid in self.hass.states.async_entity_ids("automation")[:MAX_AUTOM]:
            st = self.hass.states.get(aid)
            if st is None:
                continue
            attr = str(st.attributes)
            if len(attr) > MAX_ATTR:
                attr = f"{attr[:MAX_ATTR]}...(truncated)"
            auto_sections.append(
                f"Entity: {aid}\n"
                f"Friendly Name: {st.attributes.get('friendly_name', aid)}\n"
                f"State: {st.state}\n"
                f"Attributes: {attr}\n"
                "---\n"
            )

        return (
            f"{self.SYSTEM_PROMPT}\n\n"
            "Entities in your Home Assistant (sampled):\n"
            f"{''.join(entity_sections)}\n"
            "Existing Automations:\n"
            f"{''.join(auto_sections) if auto_sections else 'None found.'}\n\n"
            "Please propose detailed automations and improvements that reference only the entity_ids above."
        )

    # ────────────────────────────────
    # Provider dispatch
    # ────────────────────────────────
    async def _dispatch(self, prompt: str) -> str | None:
        provider = self.entry.data.get(CONF_PROVIDER, "OpenAI")
        try:
            return await {
                "OpenAI": self._openai,
                "Anthropic": self._anthropic,
                "Google": self._google,
                "Groq": self._groq,
                "LocalAI": self._localai,
                "Ollama": self._ollama,
                "Custom OpenAI": self._custom_openai,
                "Mistral AI": self._mistral,
                "Perplexity AI": self._perplexity,
            }[provider](prompt)
        except KeyError:
            _LOGGER.error("Unknown provider: %s", provider)
            return None
        except Exception as err:
            _LOGGER.error("Error getting suggestions: %s", err)
            return None

    # ────────────────────────────────
    # Provider implementations
    # ────────────────────────────────
    async def _openai(self, prompt: str) -> str | None:
        try:
            api_key = self.entry.data.get(CONF_OPENAI_API_KEY)
            model = self.entry.data.get(CONF_OPENAI_MODEL, DEFAULT_MODELS["OpenAI"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            if not api_key:
                raise ValueError("OpenAI API key not configured")

            if len(prompt) // 4 > max_tok:
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
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("OpenAI processing error: %s", err)
            return None

    async def _anthropic(self, prompt: str) -> str | None:
        try:
            api_key = self.entry.data.get(CONF_ANTHROPIC_API_KEY)
            model = self.entry.data.get(CONF_ANTHROPIC_MODEL, DEFAULT_MODELS["Anthropic"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            if not api_key:
                raise ValueError("Anthropic API key not configured")

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
                res = await resp.json()
                return res["content"][0]["text"]
        except Exception as err:
            _LOGGER.error("Anthropic processing error: %s", err)
            return None

    async def _google(self, prompt: str) -> str | None:
        try:
            api_key = self.entry.data.get(CONF_GOOGLE_API_KEY)
            model = self.entry.data.get(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"])
            max_tok = min(self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS), 30720)
            if not api_key:
                raise ValueError("Google API key not configured")

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
                res = await resp.json()
                return res["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as err:
            _LOGGER.error("Google processing error: %s", err)
            return None

    async def _groq(self, prompt: str) -> str | None:
        try:
            api_key = self.entry.data.get(CONF_GROQ_API_KEY)
            model = self.entry.data.get(CONF_GROQ_MODEL, DEFAULT_MODELS["Groq"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            if not api_key:
                raise ValueError("Groq API key not configured")

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
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("Groq processing error: %s", err)
            return None

    async def _localai(self, prompt: str) -> str | None:
        try:
            ip = self.entry.data.get(CONF_LOCALAI_IP_ADDRESS)
            port = self.entry.data.get(CONF_LOCALAI_PORT)
            https = self.entry.data.get(CONF_LOCALAI_HTTPS, False)
            model = self.entry.data.get(CONF_LOCALAI_MODEL, DEFAULT_MODELS["LocalAI"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            if not ip or not port:
                raise ValueError("LocalAI not fully configured")

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
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("LocalAI processing error: %s", err)
            return None

    async def _ollama(self, prompt: str) -> str | None:
        try:
            ip = self.entry.data.get(CONF_OLLAMA_IP_ADDRESS)
            port = self.entry.data.get(CONF_OLLAMA_PORT)
            https = self.entry.data.get(CONF_OLLAMA_HTTPS, False)
            model = self.entry.data.get(CONF_OLLAMA_MODEL, DEFAULT_MODELS["Ollama"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            if not ip or not port:
                raise ValueError("Ollama not fully configured")

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
                res = await resp.json()
                return res["message"]["content"]
        except Exception as err:
            _LOGGER.error("Ollama processing error: %s", err)
            return None

    async def _custom_openai(self, prompt: str) -> str | None:
        try:
            endpoint = self.entry.data.get(CONF_CUSTOM_OPENAI_ENDPOINT)
            api_key = self.entry.data.get(CONF_CUSTOM_OPENAI_API_KEY)
            model = self.entry.data.get(CONF_CUSTOM_OPENAI_MODEL, DEFAULT_MODELS["Custom OpenAI"])
            max_tok = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            if not endpoint:
                raise ValueError("Custom OpenAI endpoint not configured")

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
                    _LOGGER.error("Custom OpenAI API error: %s", await resp.text())
                    return None
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("Custom OpenAI processing error: %s", err)
            return None

    async def _mistral(self, prompt: str) -> str | None:
        try:
            api_key = self.entry.data.get(CONF_MISTRAL_API_KEY)
            model = self.entry.data.get(CONF_MISTRAL_MODEL, DEFAULT_MODELS["Mistral AI"])
            if not api_key:
                raise ValueError("Mistral API key not configured")

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
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("Mistral processing error: %s", err)
            return None

    async def _perplexity(self, prompt: str) -> str | None:
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
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("Perplexity processing error: %s", err)
            return None

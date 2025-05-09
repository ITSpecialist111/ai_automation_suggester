# custom_components/ai_automation_suggester/coordinator.py
"""Coordinator for AI Automation Suggester."""

from __future__ import annotations

import logging
import random
import re
from datetime import datetime

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (  # noqa: E501
    DOMAIN,
    CONF_PROVIDER,
    # New token knobs
    CONF_MAX_INPUT_TOKENS,
    CONF_MAX_OUTPUT_TOKENS,
    # Legacy fallback
    CONF_MAX_TOKENS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_MODELS,
    # Provider‑specific keys + endpoints
    CONF_OPENAI_API_KEY,
    CONF_OPENAI_MODEL,
    ENDPOINT_OPENAI,
    CONF_ANTHROPIC_API_KEY,
    CONF_ANTHROPIC_MODEL,
    VERSION_ANTHROPIC,
    ENDPOINT_ANTHROPIC,
    CONF_GOOGLE_API_KEY,
    CONF_GOOGLE_MODEL,
    CONF_GROQ_API_KEY,
    CONF_GROQ_MODEL,
    ENDPOINT_GROQ,
    CONF_LOCALAI_IP_ADDRESS,
    CONF_LOCALAI_PORT,
    CONF_LOCALAI_HTTPS,
    CONF_LOCALAI_MODEL,
    ENDPOINT_LOCALAI,
    CONF_OLLAMA_IP_ADDRESS,
    CONF_OLLAMA_PORT,
    CONF_OLLAMA_HTTPS,
    CONF_OLLAMA_MODEL,
    ENDPOINT_OLLAMA,
    CONF_CUSTOM_OPENAI_ENDPOINT,
    CONF_CUSTOM_OPENAI_API_KEY,
    CONF_CUSTOM_OPENAI_MODEL,
    CONF_MISTRAL_API_KEY,
    CONF_MISTRAL_MODEL,
    ENDPOINT_MISTRAL,
    CONF_PERPLEXITY_API_KEY,
    CONF_PERPLEXITY_MODEL,
    ENDPOINT_PERPLEXITY,
)

_LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Regex to pull fenced YAML blocks out of the AI response
# ─────────────────────────────────────────────────────────────
YAML_RE = re.compile(r"```yaml\s*([\s\S]+?)\s*```", flags=re.IGNORECASE)

SYSTEM_PROMPT = """You are an AI assistant that generates Home Assistant automations
based on entities, areas and devices, and suggests improvements to existing automations.

For each entity:
1. Understand its function and context.
2. Consider its current state and attributes.
3. Suggest context‑aware automations or tweaks, including real entity_ids.

If asked to focus on a theme (energy saving, presence lighting, etc.), integrate it.
Also review existing automations and propose improvements.
If you see a lot of text in a different language, focus on it for a translation for your output.
"""


# =============================================================================
# Coordinator
# =============================================================================
class AIAutomationCoordinator(DataUpdateCoordinator):
    """Builds the prompt, sends it to the selected provider, shares results."""

    # --------------------------------------------------------------------- #
    # Init / lifecycle                                                      #
    # --------------------------------------------------------------------- #
    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry

        self.previous_entities: dict[str, dict] = {}
        self.last_update: datetime | None = None

        # Tunables modified by the generate_suggestions service
        self.SYSTEM_PROMPT = SYSTEM_PROMPT
        self.scan_all = False
        self.selected_domains: list[str] = []
        self.entity_limit = 200

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.session = async_get_clientsession(hass)

        self._last_error: str | None = None

        self.data: dict = {
            "suggestions": "No suggestions yet",
            "description": None,
            "yaml_block": None,
            "last_update": None,
            "entities_processed": [],
            "provider": self._opt(CONF_PROVIDER, "unknown"),
            "last_error": None,
        }

        # Registries (populated in async_added_to_hass)
        self.device_registry: dr.DeviceRegistry | None = None
        self.entity_registry: er.EntityRegistry | None = None
        self.area_registry: ar.AreaRegistry | None = None

    # ---------------------------------------------------------------------
    # Utility – options‑first lookup
    # ---------------------------------------------------------------------
    def _opt(self, key: str, default=None):
        """
        Return config value with this priority:
          1. entry.options  (saved via Options flow)
          2. entry.data     (initial setup)
          3. provided default
        """
        return self.entry.options.get(key, self.entry.data.get(key, default))

    # ---------------------------------------------------------------------
    # Helper – token budgets with legacy fallback
    # ---------------------------------------------------------------------
    def _budgets(self) -> tuple[int, int]:
        """Return (input_budget, output_budget) respecting new + old fields."""
        out_budget = self._opt(CONF_MAX_OUTPUT_TOKENS, self._opt(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS))
        in_budget = self._opt(CONF_MAX_INPUT_TOKENS, self._opt(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS))
        return in_budget, out_budget

    # ---------------------------------------------------------------------
    # HA lifecycle hooks
    # ---------------------------------------------------------------------
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.device_registry = dr.async_get(self.hass)
        self.entity_registry = er.async_get(self.hass)
        self.area_registry = ar.async_get(self.hass)

    async def async_shutdown(self):
        return

    # ---------------------------------------------------------------------
    # Main polling routine
    # ---------------------------------------------------------------------
    async def _async_update_data(self) -> dict:
        try:
            now = datetime.now()
            self.last_update = now
            self._last_error = None

            # -------------------------------------------------- gather entities
            current: dict[str, dict] = {}
            for eid in self.hass.states.async_entity_ids():
                if self.selected_domains and eid.split(".")[0] not in self.selected_domains:
                    continue
                st = self.hass.states.get(eid)
                if st:
                    current[eid] = {
                        "state": st.state,
                        "attributes": st.attributes,
                        "last_changed": st.last_changed,
                        "last_updated": st.last_updated,
                        "friendly_name": st.attributes.get("friendly_name", eid),
                    }

            picked = current if self.scan_all else {k: v for k, v in current.items() if k not in self.previous_entities}
            if not picked:
                self.previous_entities = current
                return self.data

            prompt = self._build_prompt(picked)
            response = await self._dispatch(prompt)

            if response:
                match = YAML_RE.search(response)
                yaml_block = match.group(1).strip() if match else None
                description = YAML_RE.sub("", response).strip() if match else None

                persistent_notification.async_create(
                    self.hass,
                    message=response,
                    title="AI Automation Suggestions",
                    notification_id=f"ai_automation_suggestions_{now.timestamp()}",
                )

                self.data = {
                    "suggestions": response,
                    "description": description,
                    "yaml_block": yaml_block,
                    "last_update": now,
                    "entities_processed": list(picked.keys()),
                    "provider": self._opt(CONF_PROVIDER, "unknown"),
                    "last_error": None,
                }
            else:
                self.data.update(
                    {
                        "suggestions": "No suggestions available",
                        "description": None,
                        "yaml_block": None,
                        "last_update": now,
                        "entities_processed": [],
                        "last_error": self._last_error,
                    }
                )

            self.previous_entities = current
            return self.data

        except Exception as err:  # noqa: BLE001
            self._last_error = str(err)
            _LOGGER.error("Coordinator fatal error: %s", err)
            self.data["last_error"] = self._last_error
            return self.data

    # ---------------------------------------------------------------------
    # Prompt builder (unchanged)
    # ---------------------------------------------------------------------
    def _build_prompt(self, entities: dict) -> str:  # noqa: C901
        MAX_ATTR = 500
        MAX_AUTOM = 100

        ent_sections: list[str] = []
        for eid, meta in random.sample(list(entities.items()), min(len(entities), self.entity_limit)):
            domain = eid.split(".")[0]
            attr_str = str(meta["attributes"])
            if len(attr_str) > MAX_ATTR:
                attr_str = f"{attr_str[:MAX_ATTR]}...(truncated)"

            ent_entry = self.entity_registry.async_get(eid) if self.entity_registry else None
            dev_entry = self.device_registry.async_get(ent_entry.device_id) if ent_entry and ent_entry.device_id else None

            area_id = ent_entry.area_id if ent_entry and ent_entry.area_id else (dev_entry.area_id if dev_entry else None)
            area_name = "Unknown Area"
            if area_id and self.area_registry:
                ar_entry = self.area_registry.async_get_area(area_id)
                if ar_entry:
                    area_name = ar_entry.name

            block = (
                f"Entity: {eid}\n"
                f"Friendly Name: {meta['friendly_name']}\n"
                f"Domain: {domain}\n"
                f"State: {meta['state']}\n"
                f"Attributes: {attr_str}\n"
                f"Area: {area_name}\n"
            )

            if dev_entry:
                block += (
                    "Device Info:\n"
                    f"  Manufacturer: {dev_entry.manufacturer}\n"
                    f"  Model: {dev_entry.model}\n"
                    f"  Device Name: {dev_entry.name_by_user or dev_entry.name}\n"
                    f"  Device ID: {dev_entry.id}\n"
                )

            block += (
                f"Last Changed: {meta['last_changed']}\n"
                f"Last Updated: {meta['last_updated']}\n"
                "---\n"
            )
            ent_sections.append(block)

        autom_sections: list[str] = []
        for aid in self.hass.states.async_entity_ids("automation")[:MAX_AUTOM]:
            st = self.hass.states.get(aid)
            if st:
                attr = str(st.attributes)
                if len(attr) > MAX_ATTR:
                    attr = f"{attr[:MAX_ATTR]}...(truncated)"
                autom_sections.append(
                    f"Entity: {aid}\n"
                    f"Friendly Name: {st.attributes.get('friendly_name', aid)}\n"
                    f"State: {st.state}\n"
                    f"Attributes: {attr}\n"
                    "---\n"
                )

        return (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"Entities in your Home Assistant (sampled):\n{''.join(ent_sections)}\n"
            "Existing Automations:\n"
            f"{''.join(autom_sections) if autom_sections else 'None found.'}\n\n"
            "Please propose detailed automations and improvements that reference only the entity_ids above."
        )

    # ---------------------------------------------------------------------
    # Provider dispatcher
    # ---------------------------------------------------------------------
    async def _dispatch(self, prompt: str) -> str | None:
        provider = self._opt(CONF_PROVIDER, "OpenAI")
        self._last_error = None
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
            self._last_error = f"Unknown provider '{provider}'"
            _LOGGER.error(self._last_error)
            return None
        except Exception as err:  # noqa: BLE001
            self._last_error = str(err)
            _LOGGER.error("Dispatch error: %s", err)
            return None

    # ---------------------------------------------------------------------
    # Provider implementations (OpenAI shown; the rest follow same pattern)
    # ---------------------------------------------------------------------
    async def _openai(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_OPENAI_API_KEY)
            model = self._opt(CONF_OPENAI_MODEL, DEFAULT_MODELS["OpenAI"])
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("OpenAI API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": out_budget,
                "temperature": DEFAULT_TEMPERATURE,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            async with self.session.post(ENDPOINT_OPENAI, headers=headers, json=body) as resp:
                if resp.status != 200:
                    self._last_error = f"OpenAI error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("OpenAI processing error: %s", err)
            return None

    # ---------------- Anthropic ------------------------------------------------
    async def _anthropic(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_ANTHROPIC_API_KEY)
            model = self._opt(CONF_ANTHROPIC_MODEL, DEFAULT_MODELS["Anthropic"])
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("Anthropic API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": VERSION_ANTHROPIC,
            }
            body = {
                "model": model,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                "max_tokens": out_budget,
                "temperature": DEFAULT_TEMPERATURE,
            }

            async with self.session.post(ENDPOINT_ANTHROPIC, headers=headers, json=body) as resp:
                if resp.status != 200:
                    self._last_error = f"Anthropic error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()
                return res["content"][0]["text"]
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("Anthropic processing error: %s", err)
            return None

    # ---------------- Google ---------------------------------------------------
    async def _google(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_GOOGLE_API_KEY)
            model = self._opt(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"])
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("Google API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": DEFAULT_TEMPERATURE,
                    "maxOutputTokens": out_budget,
                    "topK": 40,
                    "topP": 0.95,
                },
            }
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

            async with self.session.post(endpoint, json=body) as resp:
                if resp.status != 200:
                    self._last_error = f"Google error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()
                return res["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("Google processing error: %s", err)
            return None

    # ---------------- Groq -----------------------------------------------------
    async def _groq(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_GROQ_API_KEY)
            model = self._opt(CONF_GROQ_MODEL, DEFAULT_MODELS["Groq"])
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("Groq API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            body = {
                "model": model,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                "max_tokens": out_budget,
                "temperature": DEFAULT_TEMPERATURE,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            async with self.session.post(ENDPOINT_GROQ, headers=headers, json=body) as resp:
                if resp.status != 200:
                    self._last_error = f"Groq error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("Groq processing error: %s", err)
            return None

    # ---------------- LocalAI --------------------------------------------------
    async def _localai(self, prompt: str) -> str | None:
        try:
            ip = self._opt(CONF_LOCALAI_IP_ADDRESS)
            port = self._opt(CONF_LOCALAI_PORT)
            https = self._opt(CONF_LOCALAI_HTTPS, False)
            model = self._opt(CONF_LOCALAI_MODEL, DEFAULT_MODELS["LocalAI"])
            in_budget, out_budget = self._budgets()
            if not ip or not port:
                raise ValueError("LocalAI not fully configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            proto = "https" if https else "http"
            endpoint = ENDPOINT_LOCALAI.format(protocol=proto, ip_address=ip, port=port)

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": out_budget,
                "temperature": DEFAULT_TEMPERATURE,
            }
            async with self.session.post(endpoint, json=body) as resp:
                if resp.status != 200:
                    self._last_error = f"LocalAI error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("LocalAI processing error: %s", err)
            return None

    # ---------------- Ollama ---------------------------------------------------
    async def _ollama(self, prompt: str) -> str | None:
        try:
            ip     = self._opt(CONF_OLLAMA_IP_ADDRESS)
            port   = self._opt(CONF_OLLAMA_PORT)
            https  = self._opt(CONF_OLLAMA_HTTPS, False)
            model  = self._opt(CONF_OLLAMA_MODEL, DEFAULT_MODELS["Ollama"])
            in_budget, out_budget = self._budgets()
            if not ip or not port:
                raise ValueError("Ollama not fully configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            proto = "https" if https else "http"
            endpoint = ENDPOINT_OLLAMA.format(protocol=proto, ip_address=ip, port=port)

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": DEFAULT_TEMPERATURE, "num_predict": out_budget},
            }
            async with self.session.post(endpoint, json=body) as resp:
                if resp.status != 200:
                    self._last_error = f"Ollama error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()
                return res["message"]["content"]

        except Exception as err:                    # ← this whole block
            self._last_error = str(err)             #   was missing
            _LOGGER.error("Ollama processing error: %s", err)
            return None
    # ---------------- Custom‑endpoint OpenAI -------------------------------
    async def _custom_openai(self, prompt: str) -> str | None:
        try:
            endpoint = self._opt(CONF_CUSTOM_OPENAI_ENDPOINT)
            api_key  = self._opt(CONF_CUSTOM_OPENAI_API_KEY)
            model    = self._opt(CONF_CUSTOM_OPENAI_MODEL, DEFAULT_MODELS["Custom OpenAI"])
            in_budget, out_budget = self._budgets()
            if not endpoint:
                raise ValueError("Custom OpenAI endpoint not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": out_budget,
                "temperature": DEFAULT_TEMPERATURE,
            }
            async with self.session.post(endpoint, headers=headers, json=body) as resp:
                if resp.status != 200:
                    self._last_error = f"Custom OpenAI error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("Custom OpenAI processing error: %s", err)
            return None

    # ---------------- Mistral ----------------------------------------------
    async def _mistral(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_MISTRAL_API_KEY)
            model   = self._opt(CONF_MISTRAL_MODEL, DEFAULT_MODELS["Mistral AI"])
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("Mistral API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": DEFAULT_TEMPERATURE,
                "max_tokens": out_budget,
            }
            async with self.session.post(ENDPOINT_MISTRAL, headers=headers, json=body) as resp:
                if resp.status != 200:
                    self._last_error = f"Mistral error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("Mistral processing error: %s", err)
            return None

    # ---------------- Perplexity -------------------------------------------
    async def _perplexity(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_PERPLEXITY_API_KEY)
            model   = self._opt(CONF_PERPLEXITY_MODEL, DEFAULT_MODELS["Perplexity AI"])
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("Perplexity API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": out_budget,
                "temperature": DEFAULT_TEMPERATURE,
            }
            async with self.session.post(ENDPOINT_PERPLEXITY, headers=headers, json=body) as resp:
                if resp.status != 200:
                    self._last_error = f"Perplexity error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()
                return res["choices"][0]["message"]["content"]
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("Perplexity processing error: %s", err)
            return None

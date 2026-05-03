"""Coordinator for AI Automation Suggester."""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from pathlib import Path
import random
import re
from typing import Any

import aiohttp
import anyio
import yaml

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import *
from .endpoint_utils import bearer_auth_headers, ollama_api_candidates, ollama_base_url, openai_chat_endpoint
from .language_utils import suggestion_language_instruction
from .model_catalog import (
    chat_token_parameter,
    compatibility_warnings,
    json_schema_response_format,
    model_uses_responses_api,
    should_send_temperature,
    supports_json_schema,
)
from .store import async_get_suggestion_store
from .suggestions import (
    STRUCTURED_OUTPUT_INSTRUCTIONS,
    format_suggestion_notification,
    parse_suggestion_response,
)

_LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI assistant that generates Home Assistant automations
based on entities, areas and devices, and suggests improvements to existing automations.

For each entity:
1. Understand its function and context.
2. Consider its current state and attributes.
3. Suggest context-aware automations or tweaks, including real entity_ids.

If asked to focus on a theme (energy saving, presence lighting, etc.), integrate it.
Also review existing automations and propose improvements.
If you see a lot of text in a different language, focus on it for a translation for your output.
"""


class AIAutomationCoordinator(DataUpdateCoordinator):
    """Build prompts, call the configured provider, and publish suggestions."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self.previous_entities: dict[str, dict] = {}
        self.last_update: datetime | None = None
        self.session = async_get_clientsession(hass)
        self._generation_lock = asyncio.Lock()
        self._last_error: str | None = None
        self._last_response_metadata: dict[str, Any] = {}

        self.SYSTEM_PROMPT = SYSTEM_PROMPT
        self.scan_all = False
        self.selected_domains: list[str] = []
        self.excluded_domains: list[str] = self._opt_list(CONF_EXCLUDED_DOMAINS)
        self.excluded_entities: list[str] = self._opt_list(CONF_EXCLUDED_ENTITIES)
        self.excluded_areas: list[str] = self._opt_list(CONF_EXCLUDED_AREAS)
        self.entity_limit = 200
        self.automation_read_file = False
        self.automation_limit = 100

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)

        self.data: dict = {
            "suggestions": "No suggestions yet",
            "suggestion": None,
            "suggestion_history": [],
            "suggestion_count": 0,
            "description": None,
            "yaml_block": None,
            "last_update": None,
            "entities_processed": [],
            "provider": self._opt(CONF_PROVIDER, "unknown"),
            "model": self._current_model(),
            "warnings": [],
            "last_error": None,
            "response_metadata": {},
        }

        self.device_registry: dr.DeviceRegistry | None = None
        self.entity_registry: er.EntityRegistry | None = None
        self.area_registry: ar.AreaRegistry | None = None

    def _opt(self, key: str, default=None):
        """Return entry option, then setup data, then default."""

        return self.entry.options.get(key, self.entry.data.get(key, default))

    def _opt_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Return a normalized list option."""

        value = self._opt(key, default or [])
        return self._normalize_list(value)

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        """Normalize strings, dicts, tuples, and lists into a string list."""

        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, dict):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if str(value).strip() else []

    def _budgets(self) -> tuple[int, int]:
        """Return input and output token budgets with legacy fallback."""

        out_budget = self._opt(
            CONF_MAX_OUTPUT_TOKENS, self._opt(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        )
        in_budget = self._opt(
            CONF_MAX_INPUT_TOKENS, self._opt(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        )
        return int(in_budget), int(out_budget)

    def _timeout(self) -> aiohttp.ClientTimeout:
        seconds = int(self._opt(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT))
        return aiohttp.ClientTimeout(total=max(10, seconds))

    def _current_model(self, provider: str | None = None) -> str:
        provider = provider or self._opt(CONF_PROVIDER, "OpenAI")
        model_key_map = {
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
        model_key = model_key_map.get(provider)
        return self._opt(model_key, DEFAULT_MODELS.get(provider, "unknown")) if model_key else "unknown"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.device_registry = dr.async_get(self.hass)
        self.entity_registry = er.async_get(self.hass)
        self.area_registry = ar.async_get(self.hass)

    async def async_shutdown(self):
        return

    async def async_generate_suggestions(
        self,
        *,
        custom_prompt: str | None = None,
        all_entities: bool = False,
        domains: Any = None,
        exclude_domains: Any = None,
        exclude_entities: Any = None,
        exclude_areas: Any = None,
        entity_limit: int = 200,
        automation_read_yaml: bool = False,
        automation_limit: int = 100,
    ) -> None:
        """Run one suggestion generation with isolated request settings."""

        async with self._generation_lock:
            saved = {
                "SYSTEM_PROMPT": self.SYSTEM_PROMPT,
                "scan_all": self.scan_all,
                "selected_domains": self.selected_domains,
                "excluded_domains": self.excluded_domains,
                "excluded_entities": self.excluded_entities,
                "excluded_areas": self.excluded_areas,
                "entity_limit": self.entity_limit,
                "automation_read_file": self.automation_read_file,
                "automation_limit": self.automation_limit,
            }
            try:
                persistent_prompt = str(self._opt(CONF_CUSTOM_SYSTEM_PROMPT, "") or "").strip()
                prompt_parts = [SYSTEM_PROMPT]
                if persistent_prompt:
                    prompt_parts.append(f"Persistent user instructions:\n{persistent_prompt}")
                if custom_prompt:
                    prompt_parts.append(f"Request-specific instructions:\n{custom_prompt}")
                self.SYSTEM_PROMPT = "\n\n".join(prompt_parts)
                self.scan_all = all_entities
                self.selected_domains = self._normalize_list(domains)
                self.excluded_domains = self._normalize_list(exclude_domains) or self._opt_list(CONF_EXCLUDED_DOMAINS)
                self.excluded_entities = self._normalize_list(exclude_entities) or self._opt_list(CONF_EXCLUDED_ENTITIES)
                self.excluded_areas = self._normalize_list(exclude_areas) or self._opt_list(CONF_EXCLUDED_AREAS)
                self.entity_limit = int(entity_limit)
                self.automation_read_file = bool(automation_read_yaml)
                self.automation_limit = int(automation_limit)
                await self.async_request_refresh()
            finally:
                self.SYSTEM_PROMPT = saved["SYSTEM_PROMPT"]
                self.scan_all = saved["scan_all"]
                self.selected_domains = saved["selected_domains"]
                self.excluded_domains = saved["excluded_domains"]
                self.excluded_entities = saved["excluded_entities"]
                self.excluded_areas = saved["excluded_areas"]
                self.entity_limit = saved["entity_limit"]
                self.automation_read_file = saved["automation_read_file"]
                self.automation_limit = saved["automation_limit"]

    async def _async_update_data(self) -> dict:
        try:
            now = datetime.now()
            provider = self._opt(CONF_PROVIDER, "OpenAI")
            model = self._current_model(provider)
            warnings = compatibility_warnings(provider, model)
            self.last_update = now
            self._last_error = None
            self._last_response_metadata = {}

            current = self._collect_entities()
            picked = current if self.scan_all else {k: v for k, v in current.items() if k not in self.previous_entities}
            if not picked:
                self.previous_entities = current
                history = await async_get_suggestion_store(self.hass).async_list()
                self.data.update(
                    {
                        "suggestion_history": history,
                        "suggestion_count": len(history),
                        "provider": provider,
                        "model": model,
                        "warnings": warnings,
                        "last_update": now,
                    }
                )
                return self.data

            prompt = await self._build_prompt(picked)
            response = await self._dispatch(prompt)
            store = async_get_suggestion_store(self.hass)

            if response:
                parsed = parse_suggestion_response(
                    response,
                    provider=provider,
                    model=model,
                    created_at=now,
                    entities_processed=list(picked.keys()),
                    inherited_warnings=warnings,
                    response_metadata=self._last_response_metadata,
                )
                retention = int(self._opt(CONF_HISTORY_RETENTION, DEFAULT_HISTORY_RETENTION))
                history = await store.async_add_suggestions(parsed, retention=retention)
                latest = history[0] if history else parsed[0]

                persistent_notification.async_create(
                    self.hass,
                    message=format_suggestion_notification(latest),
                    title=f"AI Automation Suggestions ({provider})",
                    notification_id=f"ai_automation_suggestions_{now.timestamp()}",
                )

                self.data = {
                    "suggestions": response,
                    "suggestion": latest,
                    "suggestion_history": history,
                    "suggestion_count": len(history),
                    "description": latest.get("description"),
                    "yaml_block": latest.get("yamlCode"),
                    "last_update": now,
                    "entities_processed": list(picked.keys()),
                    "provider": provider,
                    "model": model,
                    "warnings": latest.get("warnings", warnings),
                    "last_error": None,
                    "response_metadata": self._last_response_metadata,
                }
            else:
                history = await store.async_list()
                self.data.update(
                    {
                        "suggestions": "No suggestions available",
                        "suggestion": None,
                        "suggestion_history": history,
                        "suggestion_count": len(history),
                        "description": None,
                        "yaml_block": None,
                        "last_update": now,
                        "entities_processed": [],
                        "provider": provider,
                        "model": model,
                        "warnings": warnings,
                        "last_error": self._last_error,
                        "response_metadata": self._last_response_metadata,
                    }
                )

            self.previous_entities = current
            return self.data

        except Exception as err:  # noqa: BLE001
            self._last_error = str(err)
            _LOGGER.exception("Coordinator fatal error")
            self.data["last_error"] = self._last_error
            return self.data

    def _collect_entities(self) -> dict[str, dict]:
        current: dict[str, dict] = {}
        selected_domains = set(self.selected_domains)
        for entity_id in self.hass.states.async_entity_ids():
            domain = entity_id.split(".", 1)[0]
            if selected_domains and domain not in selected_domains:
                continue
            if self._is_entity_excluded(entity_id):
                continue
            state = self.hass.states.get(entity_id)
            if state:
                current[entity_id] = {
                    "state": state.state,
                    "attributes": state.attributes,
                    "last_changed": state.last_changed,
                    "last_updated": state.last_updated,
                    "friendly_name": state.attributes.get("friendly_name", entity_id),
                }
        return current

    def _is_entity_excluded(self, entity_id: str) -> bool:
        domain = entity_id.split(".", 1)[0]
        if domain in set(self.excluded_domains):
            return True
        if entity_id in set(self.excluded_entities):
            return True
        if not self.excluded_areas or not self.entity_registry:
            return False

        entity_entry = self.entity_registry.async_get(entity_id)
        device_entry = None
        if entity_entry and entity_entry.device_id and self.device_registry:
            device_entry = self.device_registry.async_get(entity_entry.device_id)
        area_id = entity_entry.area_id if entity_entry and entity_entry.area_id else None
        if not area_id and device_entry:
            area_id = device_entry.area_id
        area_names = {area_id.lower()} if area_id else set()
        if area_id and self.area_registry:
            area_entry = self.area_registry.async_get_area(area_id)
            if area_entry:
                area_names.add(area_entry.name.lower())
        excluded = {area.lower() for area in self.excluded_areas}
        return bool(area_names & excluded)

    async def _build_prompt(self, entities: dict) -> str:
        max_attr = 500
        max_autom = self.automation_limit
        ent_sections: list[str] = []
        for entity_id, meta in random.sample(list(entities.items()), min(len(entities), self.entity_limit)):
            domain = entity_id.split(".", 1)[0]
            attr_str = str(meta["attributes"])
            if len(attr_str) > max_attr:
                attr_str = f"{attr_str[:max_attr]}...(truncated)"

            entity_entry = self.entity_registry.async_get(entity_id) if self.entity_registry else None
            device_entry = (
                self.device_registry.async_get(entity_entry.device_id)
                if entity_entry and entity_entry.device_id and self.device_registry
                else None
            )
            area_id = entity_entry.area_id if entity_entry and entity_entry.area_id else None
            if not area_id and device_entry:
                area_id = device_entry.area_id
            area_name = "Unknown Area"
            if area_id and self.area_registry:
                area_entry = self.area_registry.async_get_area(area_id)
                if area_entry:
                    area_name = area_entry.name

            block = (
                f"Entity: {entity_id}\n"
                f"Friendly Name: {meta['friendly_name']}\n"
                f"Domain: {domain}\n"
                f"State: {meta['state']}\n"
                f"Attributes: {attr_str}\n"
                f"Area: {area_name}\n"
            )
            if device_entry:
                block += (
                    "Device Info:\n"
                    f"  Manufacturer: {device_entry.manufacturer}\n"
                    f"  Model: {device_entry.model}\n"
                    f"  Device Name: {device_entry.name_by_user or device_entry.name}\n"
                    f"  Device ID: {device_entry.id}\n"
                )
            block += f"Last Changed: {meta['last_changed']}\nLast Updated: {meta['last_updated']}\n---\n"
            ent_sections.append(block)

        autom_sections = self._read_automations_default(max_autom, max_attr)
        autom_codes: list[str] = []
        if self.automation_read_file:
            autom_codes = await self._read_automations_file_method(max_autom)
        language_instruction = suggestion_language_instruction(getattr(self.hass.config, "language", None))
        language_block = f"{language_instruction}\n\n" if language_instruction else ""

        return (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"{STRUCTURED_OUTPUT_INSTRUCTIONS}\n\n"
            f"{language_block}"
            f"Entities in your Home Assistant (sampled):\n{''.join(ent_sections)}\n"
            "Existing Automations Overview:\n"
            f"{''.join(autom_sections) if autom_sections else 'None found.'}\n\n"
            "Automations YAML Code (for analysis and improvement):\n"
            f"{''.join(autom_codes) if autom_codes else 'No automations YAML code included.'}\n\n"
            "Analyze the entities and existing automations. Propose useful new automations or improvements "
            "that reference only the entity_ids shown above."
        )

    def _read_automations_default(self, max_autom: int, max_attr: int) -> list[str]:
        autom_sections: list[str] = []
        for automation_id in self.hass.states.async_entity_ids("automation")[:max_autom]:
            state = self.hass.states.get(automation_id)
            if state:
                attr = str(state.attributes)
                if len(attr) > max_attr:
                    attr = f"{attr[:max_attr]}...(truncated)"
                autom_sections.append(
                    f"Entity: {automation_id}\n"
                    f"Friendly Name: {state.attributes.get('friendly_name', automation_id)}\n"
                    f"State: {state.state}\n"
                    f"Attributes: {attr}\n"
                    "---\n"
                )
        return autom_sections

    async def _read_automations_file_method(self, max_autom: int) -> list[str]:
        automations_file = Path(self.hass.config.path()) / "automations.yaml"
        autom_codes: list[str] = []
        try:
            async with await anyio.open_file(automations_file, "r", encoding="utf-8") as file:
                content = await file.read()
            automations = yaml.safe_load(content) or []
            if not isinstance(automations, list):
                _LOGGER.warning("automations.yaml did not parse as a list")
                return autom_codes
            for automation in automations[:max_autom]:
                if not isinstance(automation, dict):
                    continue
                autom_codes.append(
                    "Automation YAML:\n```yaml\n"
                    f"{yaml.safe_dump([automation], sort_keys=False)}"
                    "```\n---\n"
                )
        except FileNotFoundError:
            _LOGGER.warning("automations.yaml file was not found")
        except yaml.YAMLError as err:
            _LOGGER.warning("Error parsing automations.yaml: %s", err)
        return autom_codes

    async def _dispatch(self, prompt: str) -> str | None:
        provider = self._opt(CONF_PROVIDER, "OpenAI")
        dispatch = {
            "OpenAI": self._openai,
            "Anthropic": self._anthropic,
            "Google": self._google,
            "Groq": self._groq,
            "LocalAI": self._localai,
            "Ollama": self._ollama,
            "Custom OpenAI": self._custom_openai,
            "Mistral AI": self._mistral,
            "Perplexity AI": self._perplexity,
            "OpenRouter": self._openrouter,
            "OpenAI Azure": self._openai_azure,
            "Generic OpenAI": self._generic_openai,
        }
        handler = dispatch.get(provider)
        if handler is None:
            self._last_error = f"Unknown provider '{provider}'"
            _LOGGER.error(self._last_error)
            return None
        try:
            return await handler(prompt)
        except Exception as err:  # noqa: BLE001
            self._last_error = str(err)
            _LOGGER.exception("Dispatch error for %s", provider)
            return None

    def _trim_prompt(self, prompt: str) -> str:
        in_budget, _ = self._budgets()
        if len(prompt) // 4 > in_budget:
            return prompt[: in_budget * 4]
        return prompt

    async def _post_json(
        self,
        endpoint: str,
        *,
        headers: dict[str, str] | None = None,
        body: dict[str, Any],
        provider_label: str,
    ) -> dict[str, Any] | None:
        async with self.session.post(
            endpoint,
            headers=headers,
            json=body,
            timeout=self._timeout(),
        ) as response:
            response_text = await response.text()
            if response.status != 200:
                self._last_error = f"{provider_label} error {response.status}: {response_text}"
                _LOGGER.error(self._last_error)
                return None
            try:
                return await response.json(content_type=None)
            except Exception as err:  # noqa: BLE001
                self._last_error = f"{provider_label} returned non-JSON response: {err}: {response_text[:500]}"
                _LOGGER.error(self._last_error)
                return None

    def _openai_compatible_body(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        temperature: float,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _, out_budget = self._budgets()
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            chat_token_parameter(provider, model): out_budget,
        }
        if should_send_temperature(provider, model):
            body["temperature"] = temperature
        if supports_json_schema(provider, model):
            body["response_format"] = json_schema_response_format()
        if extra:
            body.update(extra)
        return body

    def _extract_chat_content(self, response: dict[str, Any], provider_label: str) -> str | None:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError(f"{provider_label} response missing choices array: {response}")
        choice = choices[0]
        self._last_response_metadata = {
            "finish_reason": choice.get("finish_reason"),
            "native_finish_reason": choice.get("native_finish_reason"),
            "usage": response.get("usage"),
        }
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content if isinstance(part, dict))
        raise ValueError(f"{provider_label} message missing content: {message}")

    async def _openai(self, prompt: str) -> str | None:
        api_key = self._opt(CONF_OPENAI_API_KEY)
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        model = self._current_model("OpenAI")
        prompt = self._trim_prompt(prompt)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if model_uses_responses_api("OpenAI", model):
            return await self._openai_responses(prompt, model, headers)
        body = self._openai_compatible_body(
            provider="OpenAI",
            model=model,
            prompt=prompt,
            temperature=float(self._opt(CONF_OPENAI_TEMPERATURE, DEFAULT_TEMPERATURE)),
        )
        response = await self._post_json(ENDPOINT_OPENAI, headers=headers, body=body, provider_label="OpenAI")
        return self._extract_chat_content(response, "OpenAI") if response else None

    async def _openai_responses(self, prompt: str, model: str, headers: dict[str, str]) -> str | None:
        _, out_budget = self._budgets()
        body: dict[str, Any] = {
            "model": model,
            "input": [{"role": "user", "content": prompt}],
            "max_output_tokens": out_budget,
            "reasoning": {
                "effort": self._opt(CONF_OPENAI_REASONING_EFFORT, DEFAULT_OPENAI_REASONING_EFFORT)
            },
            "text": {"format": {"type": "json_schema", **json_schema_response_format()["json_schema"]}},
        }
        response = await self._post_json(
            "https://api.openai.com/v1/responses",
            headers=headers,
            body=body,
            provider_label="OpenAI Responses",
        )
        if not response:
            return None
        self._last_response_metadata = {
            "status": response.get("status"),
            "incomplete_details": response.get("incomplete_details"),
            "usage": response.get("usage"),
        }
        if isinstance(response.get("output_text"), str):
            return response["output_text"]
        output = response.get("output") or []
        text_parts: list[str] = []
        for item in output:
            for content in item.get("content", []) if isinstance(item, dict) else []:
                if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                    text_parts.append(str(content.get("text", "")))
        return "".join(text_parts) if text_parts else None

    async def _openai_azure(self, prompt: str) -> str | None:
        endpoint_base = self._opt(CONF_OPENAI_AZURE_ENDPOINT)
        api_key = self._opt(CONF_OPENAI_AZURE_API_KEY)
        deployment_id = self._opt(CONF_OPENAI_AZURE_DEPLOYMENT_ID)
        api_version = self._opt(CONF_OPENAI_AZURE_API_VERSION, "2025-01-01-preview")
        if not endpoint_base or not deployment_id or not api_key:
            raise ValueError("Azure OpenAI endpoint, deployment, or API key not configured")
        endpoint_base = str(endpoint_base).rstrip("/")
        if not re.match(r"^https?://", endpoint_base):
            endpoint_base = f"https://{endpoint_base}"
        endpoint = f"{endpoint_base}/openai/deployments/{deployment_id}/chat/completions?api-version={api_version}"
        _, out_budget = self._budgets()
        model = self._current_model("OpenAI Azure")
        body: dict[str, Any] = {
            "messages": [{"role": "user", "content": self._trim_prompt(prompt)}],
            chat_token_parameter("OpenAI Azure", model): out_budget,
        }
        if should_send_temperature("OpenAI Azure", model):
            body["temperature"] = float(self._opt(CONF_OPENAI_AZURE_TEMPERATURE, DEFAULT_TEMPERATURE))
        response = await self._post_json(
            endpoint,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            body=body,
            provider_label="Azure OpenAI",
        )
        return self._extract_chat_content(response, "Azure OpenAI") if response else None

    async def _generic_openai(self, prompt: str) -> str | None:
        endpoint = str(self._opt(CONF_GENERIC_OPENAI_ENDPOINT) or "").rstrip("/")
        if not endpoint or not re.match(r"^https?://", endpoint):
            raise ValueError("Generic OpenAI endpoint must be a full http(s) URL")
        api_key = self._opt(CONF_GENERIC_OPENAI_API_KEY)
        model = self._current_model("Generic OpenAI")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        body = self._openai_compatible_body(
            provider="Generic OpenAI",
            model=model,
            prompt=self._trim_prompt(prompt),
            temperature=float(self._opt(CONF_GENERIC_OPENAI_TEMPERATURE, DEFAULT_TEMPERATURE)),
        )
        response = await self._post_json(endpoint, headers=headers, body=body, provider_label="Generic OpenAI")
        return self._extract_chat_content(response, "Generic OpenAI") if response else None

    async def _anthropic(self, prompt: str) -> str | None:
        api_key = self._opt(CONF_ANTHROPIC_API_KEY)
        if not api_key:
            raise ValueError("Anthropic API key not configured")
        _, out_budget = self._budgets()
        model = self._current_model("Anthropic")
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": [{"type": "text", "text": self._trim_prompt(prompt)}]}],
            "max_tokens": out_budget,
            "temperature": float(self._opt(CONF_ANTHROPIC_TEMPERATURE, DEFAULT_TEMPERATURE)),
        }
        response = await self._post_json(
            ENDPOINT_ANTHROPIC,
            headers={"x-api-key": api_key, "Content-Type": "application/json", "anthropic-version": VERSION_ANTHROPIC},
            body=body,
            provider_label="Anthropic",
        )
        if not response:
            return None
        self._last_response_metadata = {
            "stop_reason": response.get("stop_reason"),
            "usage": response.get("usage"),
        }
        content = response.get("content") or []
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"]
        if text_parts:
            return "".join(text_parts)
        raise ValueError(f"Anthropic response missing text content: {response}")

    async def _google(self, prompt: str) -> str | None:
        api_key = self._opt(CONF_GOOGLE_API_KEY)
        if not api_key:
            raise ValueError("Google API key not configured")
        _, out_budget = self._budgets()
        model = self._current_model("Google")
        generation_config: dict[str, Any] = {
            "temperature": float(self._opt(CONF_GOOGLE_TEMPERATURE, DEFAULT_TEMPERATURE)),
            "maxOutputTokens": out_budget,
        }
        if supports_json_schema("Google", model):
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = json_schema_response_format()["json_schema"]["schema"]
        body = {"contents": [{"parts": [{"text": self._trim_prompt(prompt)}]}], "generationConfig": generation_config}
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        response = await self._post_json(endpoint, body=body, provider_label="Google")
        if not response:
            return None
        candidates = response.get("candidates") or []
        if not candidates:
            raise ValueError(f"Google response missing candidates: {response}")
        self._last_response_metadata = {
            "finish_reason": candidates[0].get("finishReason"),
            "usage": response.get("usageMetadata"),
        }
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "".join(text_parts) if text_parts else None

    async def _groq(self, prompt: str) -> str | None:
        api_key = self._opt(CONF_GROQ_API_KEY)
        if not api_key:
            raise ValueError("Groq API key not configured")
        model = self._current_model("Groq")
        body = self._openai_compatible_body(
            provider="Groq",
            model=model,
            prompt=self._trim_prompt(prompt),
            temperature=float(self._opt(CONF_GROQ_TEMPERATURE, DEFAULT_TEMPERATURE)),
        )
        response = await self._post_json(
            ENDPOINT_GROQ,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            body=body,
            provider_label="Groq",
        )
        return self._extract_chat_content(response, "Groq") if response else None

    async def _localai(self, prompt: str) -> str | None:
        ip = self._opt(CONF_LOCALAI_IP_ADDRESS)
        port = self._opt(CONF_LOCALAI_PORT)
        if not ip or not port:
            raise ValueError("LocalAI not fully configured")
        proto = "https" if self._opt(CONF_LOCALAI_HTTPS, False) else "http"
        endpoint = ENDPOINT_LOCALAI.format(protocol=proto, ip_address=ip, port=port)
        model = self._current_model("LocalAI")
        body = self._openai_compatible_body(
            provider="LocalAI",
            model=model,
            prompt=self._trim_prompt(prompt),
            temperature=float(self._opt(CONF_LOCALAI_TEMPERATURE, DEFAULT_TEMPERATURE)),
        )
        response = await self._post_json(endpoint, body=body, provider_label="LocalAI")
        return self._extract_chat_content(response, "LocalAI") if response else None

    async def _ollama(self, prompt: str) -> str | None:
        ip = self._opt(CONF_OLLAMA_IP_ADDRESS)
        port = self._opt(CONF_OLLAMA_PORT)
        base = ollama_base_url(
            base_url=self._opt(CONF_OLLAMA_BASE_URL),
            ip_address=ip,
            port=port,
            https=self._opt(CONF_OLLAMA_HTTPS, False),
        )
        if not base:
            raise ValueError("Ollama host/port or base URL is not configured")
        messages = []
        if self._opt(CONF_OLLAMA_DISABLE_THINK, False):
            messages.append({"role": "system", "content": "/no_think"})
        messages.append({"role": "user", "content": self._trim_prompt(prompt)})
        _, out_budget = self._budgets()
        body = {
            "model": self._current_model("Ollama"),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": float(self._opt(CONF_OLLAMA_TEMPERATURE, DEFAULT_TEMPERATURE)),
                "num_predict": out_budget,
            },
        }
        response = None
        headers = bearer_auth_headers(self._opt(CONF_OLLAMA_API_KEY))
        for endpoint in ollama_api_candidates(base, "api/chat"):
            response = await self._post_json(endpoint, headers=headers, body=body, provider_label="Ollama")
            if response:
                break
        if not response:
            return None
        self._last_response_metadata = {"done_reason": response.get("done_reason"), "usage": response.get("eval_count")}
        return response.get("message", {}).get("content")

    async def _custom_openai(self, prompt: str) -> str | None:
        endpoint = str(self._opt(CONF_CUSTOM_OPENAI_ENDPOINT) or "").rstrip("/")
        if not endpoint:
            raise ValueError("Custom OpenAI endpoint not configured")
        completions_endpoint = openai_chat_endpoint(endpoint)
        headers = {"Content-Type": "application/json"}
        api_key = self._opt(CONF_CUSTOM_OPENAI_API_KEY)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        model = self._current_model("Custom OpenAI")
        body = self._openai_compatible_body(
            provider="Custom OpenAI",
            model=model,
            prompt=self._trim_prompt(prompt),
            temperature=float(self._opt(CONF_CUSTOM_OPENAI_TEMPERATURE, DEFAULT_TEMPERATURE)),
        )
        response = await self._post_json(completions_endpoint, headers=headers, body=body, provider_label="Custom OpenAI")
        return self._extract_chat_content(response, "Custom OpenAI") if response else None

    async def _mistral(self, prompt: str) -> str | None:
        api_key = self._opt(CONF_MISTRAL_API_KEY)
        if not api_key:
            raise ValueError("Mistral API key not configured")
        model = self._current_model("Mistral AI")
        body = self._openai_compatible_body(
            provider="Mistral AI",
            model=model,
            prompt=self._trim_prompt(prompt),
            temperature=float(self._opt(CONF_MISTRAL_TEMPERATURE, DEFAULT_TEMPERATURE)),
        )
        response = await self._post_json(
            ENDPOINT_MISTRAL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            body=body,
            provider_label="Mistral",
        )
        return self._extract_chat_content(response, "Mistral") if response else None

    async def _perplexity(self, prompt: str) -> str | None:
        api_key = self._opt(CONF_PERPLEXITY_API_KEY)
        if not api_key:
            raise ValueError("Perplexity API key not configured")
        model = self._current_model("Perplexity AI")
        body = self._openai_compatible_body(
            provider="Perplexity AI",
            model=model,
            prompt=self._trim_prompt(prompt),
            temperature=float(self._opt(CONF_PERPLEXITY_TEMPERATURE, DEFAULT_TEMPERATURE)),
        )
        response = await self._post_json(
            ENDPOINT_PERPLEXITY,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"},
            body=body,
            provider_label="Perplexity",
        )
        return self._extract_chat_content(response, "Perplexity") if response else None

    async def _openrouter(self, prompt: str) -> str | None:
        api_key = self._opt(CONF_OPENROUTER_API_KEY)
        if not api_key:
            raise ValueError("OpenRouter API key not configured")
        model = self._current_model("OpenRouter")
        extra: dict[str, Any] = {}
        reasoning_max_tokens = int(self._opt(CONF_OPENROUTER_REASONING_MAX_TOKENS, 0))
        if reasoning_max_tokens > 0:
            extra["reasoning"] = {"max_tokens": reasoning_max_tokens}
        body = self._openai_compatible_body(
            provider="OpenRouter",
            model=model,
            prompt=self._trim_prompt(prompt),
            temperature=float(self._opt(CONF_OPENROUTER_TEMPERATURE, DEFAULT_TEMPERATURE)),
            extra=extra,
        )
        response = await self._post_json(
            ENDPOINT_OPENROUTER,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            body=body,
            provider_label="OpenRouter",
        )
        return self._extract_chat_content(response, "OpenRouter") if response else None
# custom_components/ai_automation_suggester/coordinator.py
"""Coordinator for AI Automation Suggester."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import random
import re

import aiohttp
import anyio
import yaml
import json

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
        self.automation_read_file = False  # Default automation reading mode
        self.automation_limit = 100
        self.script_read_file = False  # Default script reading mode
        self.script_limit = 100
        self.include_entity_details = True  # Default to include detailed entity info

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
        out_budget = self._opt(
            CONF_MAX_OUTPUT_TOKENS, self._opt(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        )
        in_budget = self._opt(
            CONF_MAX_INPUT_TOKENS, self._opt(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        )

        _LOGGER.debug("Input budget: %d, Output budget: %d", in_budget, out_budget)

        return in_budget, out_budget

    # --------------------------------------------------------------------- #
    # Helper – model compatibility detector
    # --------------------------------------------------------------------- #
    def _get_model_parameters(self, model_name: str) -> dict:
        """
        Return appropriate parameters based on model capabilities.
        GPT-5 variants use max_completion_tokens, older models use max_tokens.
        """
        # GPT-5 variants that require max_completion_tokens
        gpt5_variants = [
            'gpt-5', 'gpt-5-mini', 'gpt-5-nano',
            'gpt-5-',  # Catch any gpt-5-* variants
        ]

        model_lower = model_name.lower()

        # Check if it's a GPT-5 variant
        is_gpt5 = any(variant in model_lower for variant in gpt5_variants)

        if is_gpt5:
            _LOGGER.debug("Using max_completion_tokens for GPT-5 model: %s", model_name)
            return {
                'max_tokens_param': 'max_completion_tokens',
                'supports_completion_tokens': True
            }
        else:
            _LOGGER.debug("Using max_tokens for model: %s", model_name)
            return {
                'max_tokens_param': 'max_tokens',
                'supports_completion_tokens': False
            }

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
                if (
                    self.selected_domains
                    and eid.split(".")[0] not in self.selected_domains
                ):
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

            picked = (
                current
                if self.scan_all
                else {
                    k: v for k, v in current.items() if k not in self.previous_entities
                }
            )
            if not picked:
                self.previous_entities = current
                return self.data

            prompt = await self._build_prompt(picked)
            _LOGGER.debug("Built prompt with %d entities: %s", len(picked), prompt)

            response = await self._dispatch(prompt)
            _LOGGER.debug("Received response from provider: %s", response)
            
            if response:
                match = YAML_RE.search(response)
                yaml_block = match.group(1).strip() if match else None
                description = YAML_RE.sub("", response).strip() if match else None

                persistent_notification.async_create(
                    self.hass,
                    message=response,
                    title="AI Automation Suggestions (%s)" % self._opt(CONF_PROVIDER, "unknown"),
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
    # Prompt builder (updated)
    # ---------------------------------------------------------------------
    async def _build_prompt(self, entities: dict) -> str:  # noqa: C901
        """Build the prompt based on entities and automations."""
        MAX_ATTR = 500
        MAX_AUTOM = getattr(self, "automation_limit", 100)

        ent_sections: list[str] = []
        for eid, meta in random.sample(
            list(entities.items()), min(len(entities), self.entity_limit)
        ):
            if self.include_entity_details:
                block = self._format_entity_detailed(eid, meta, MAX_ATTR)
            else:
                block = self._format_entity_summarized(eid, meta)
            ent_sections.append(block)

        # Choose automation reading method
        if self.automation_read_file:
            autom_sections = self._read_automations_default(MAX_AUTOM, MAX_ATTR)
            autom_codes = await self._read_automations_file_method(MAX_AUTOM, MAX_ATTR)

            builded_prompt = (
                f"{self.SYSTEM_PROMPT}\n\n"
                f"Entities in your Home Assistant (sampled):\n{''.join(ent_sections)}\n"
                "Existing Automations Overview:\n"
                f"{''.join(autom_sections) if autom_sections else 'None found.'}\n\n"
                "Automations YAML Code (for analysis and improvement):\n"
                f"{''.join(autom_codes) if autom_codes else 'No automations YAML code available.'}\n\n"
                "Please analyze both the entities and existing automations. "
                "Propose detailed improvements to existing automations and suggest new ones "
                "that reference only the entity_ids shown above."
            )
        else:
            autom_sections = self._read_automations_default(MAX_AUTOM, MAX_ATTR)

            builded_prompt = (
                f"{self.SYSTEM_PROMPT}\n\n"
                f"Entities in your Home Assistant (sampled):\n{''.join(ent_sections)}\n"
                "Existing Automations:\n"
                f"{''.join(autom_sections) if autom_sections else 'None found.'}\n\n"
                "Please propose detailed automations and improvements that reference only the entity_ids above."
            )

        # -------------------------------------------------- gather scripts
        MAX_SCRIPTS = getattr(self, "script_limit", 100)
        if self.script_read_file:
            script_sections = self._read_scripts_default(MAX_SCRIPTS, MAX_ATTR)
            script_codes = await self._read_scripts_file_method(MAX_SCRIPTS, MAX_ATTR)

            builded_prompt += (
                "\n\nExisting Scripts Overview:\n"
                f"{''.join(script_sections) if script_sections else 'None found.'}\n\n"
                "Scripts YAML Code (for analysis and improvement):\n"
                f"{''.join(script_codes) if script_codes else 'No scripts YAML code available.'}\n\n"
                "Please also analyze the existing scripts. "
                "Propose detailed improvements to existing scripts and suggest new ones "
                "that reference only the entity_ids shown above."
            )
        else:
            script_sections = self._read_scripts_default(MAX_SCRIPTS, MAX_ATTR)
            if script_sections:
                builded_prompt += (
                    "\n\nExisting Scripts:\n"
                    f"{''.join(script_sections)}\n\n"
                    "Please also propose improvements to existing scripts or suggest new ones."
                )

        return builded_prompt

    def _format_entity_detailed(self, eid: str, meta: dict, max_attr: int) -> str:
        """Format entity with detailed information including attributes and device info."""
        domain = eid.split(".")[0]
        attr_str = str(meta["attributes"])
        if len(attr_str) > max_attr:
            attr_str = f"{attr_str[:max_attr]}...(truncated)"

        ent_entry = (
            self.entity_registry.async_get(eid) if self.entity_registry else None
        )
        dev_entry = (
            self.device_registry.async_get(ent_entry.device_id)
            if ent_entry and ent_entry.device_id
            else None
        )

        area_id = (
            ent_entry.area_id
            if ent_entry and ent_entry.area_id
            else (dev_entry.area_id if dev_entry else None)
        )
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
        return block

    def _format_entity_summarized(self, eid: str, meta: dict) -> str:
        """Format entity with summarized information (no attributes or device info)."""
        domain = eid.split(".")[0]
        
        ent_entry = (
            self.entity_registry.async_get(eid) if self.entity_registry else None
        )
        dev_entry = (
            self.device_registry.async_get(ent_entry.device_id)
            if ent_entry and ent_entry.device_id
            else None
        )

        area_id = (
            ent_entry.area_id
            if ent_entry and ent_entry.area_id
            else (dev_entry.area_id if dev_entry else None)
        )
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
            f"Area: {area_name}\n"
            f"Last Changed: {meta['last_changed']}\n"
            f"Last Updated: {meta['last_updated']}\n"
            "---\n"
        )
        return block

    def _read_automations_default(self, max_autom: int, max_attr: int) -> list[str]:
        """Default method for reading automations."""
        autom_sections: list[str] = []
        for aid in self.hass.states.async_entity_ids("automation")[:max_autom]:
            st = self.hass.states.get(aid)
            if st:
                attr = str(st.attributes)
                if len(attr) > max_attr:
                    attr = f"{attr[:max_attr]}...(truncated)"
                autom_sections.append(
                    f"Entity: {aid}\n"
                    f"Friendly Name: {st.attributes.get('friendly_name', aid)}\n"
                    f"State: {st.state}\n"
                    f"Attributes: {attr}\n"
                    "---\n"
                )
        return autom_sections

    async def _read_automations_file_method(self, max_autom: int, max_attr: int) -> list[str]:
        """File method for reading automations."""
        automations_file = Path(self.hass.config.path()) / "automations.yaml"
        autom_codes: list[str] = []

        try:
            async with await anyio.open_file(
                automations_file, "r", encoding="utf-8"
            ) as file:
                content = await file.read()
                automations = yaml.safe_load(content)

            for automation in automations[:max_autom]:
                aid = automation.get("id", "unknown_id")
                alias = automation.get("alias", "Unnamed Automation")
                description = automation.get("description", "")
                trigger = automation.get("trigger", []) + automation.get("triggers", [])
                condition = automation.get("condition", []) + automation.get(
                    "conditions", []
                )
                action = automation.get("action", []) + automation.get("actions", [])

                # YAML
                code_block = (
                    f"Automation Code for automation.{aid}:\n"
                    "```yaml\n"
                    f"- id: '{aid}'\n"
                    f"  alias: '{alias}'\n"
                    f"  description: '{description}'\n"
                    f"  trigger: {trigger}\n"
                    f"  condition: {condition}\n"
                    f"  action: {action}\n"
                    "```\n"
                    "---\n"
                )
                autom_codes.append(code_block)

        except FileNotFoundError:
            _LOGGER.error("The automations.yaml file was not found.")
        except yaml.YAMLError as err:
            _LOGGER.error("Error parsing automations.yaml: %s", err)

        return autom_codes

    def _read_scripts_default(self, max_scripts: int, max_attr: int) -> list[str]:
        """Default method for reading scripts."""
        script_sections: list[str] = []
        for sid in self.hass.states.async_entity_ids("script")[:max_scripts]:
            st = self.hass.states.get(sid)
            if st:
                attr = str(st.attributes)
                if len(attr) > max_attr:
                    attr = f"{attr[:max_attr]}...(truncated)"
                script_sections.append(
                    f"Entity: {sid}\n"
                    f"Friendly Name: {st.attributes.get('friendly_name', sid)}\n"
                    f"State: {st.state}\n"
                    f"Attributes: {attr}\n"
                    "---\n"
                )
        return script_sections

    async def _read_scripts_file_method(self, max_scripts: int, max_attr: int) -> list[str]:
        """File method for reading scripts."""
        scripts_file = Path(self.hass.config.path()) / "scripts.yaml"
        script_codes: list[str] = []

        try:
            async with await anyio.open_file(
                scripts_file, "r", encoding="utf-8"
            ) as file:
                content = await file.read()
                scripts = yaml.safe_load(content)

            if isinstance(scripts, dict):
                # scripts.yaml can be a dict where keys are the script IDs
                count = 0
                for sid, script in scripts.items():
                    if count >= max_scripts:
                        break
                    
                    alias = script.get("alias", sid)
                    description = script.get("description", "")
                    sequence = script.get("sequence", [])

                    code_block = (
                        f"Script Code for script.{sid}:\n"
                        "```yaml\n"
                        f"{sid}:\n"
                        f"  alias: '{alias}'\n"
                        f"  description: '{description}'\n"
                        f"  sequence: {sequence}\n"
                        "```\n"
                        "---\n"
                    )
                    script_codes.append(code_block)
                    count += 1
            elif isinstance(scripts, list):
                # or a list (less common for scripts.yaml, but possible in some setups)
                for script in scripts[:max_scripts]:
                    sid = script.get("id", "unknown_id")
                    alias = script.get("alias", sid)
                    description = script.get("description", "")
                    sequence = script.get("sequence", [])

                    code_block = (
                        f"Script Code for script.{sid}:\n"
                        "```yaml\n"
                        f"- alias: '{alias}'\n"
                        f"  description: '{description}'\n"
                        f"  sequence: {sequence}\n"
                        "```\n"
                        "---\n"
                    )
                    script_codes.append(code_block)

        except FileNotFoundError:
            _LOGGER.error("The scripts.yaml file was not found.")
        except yaml.YAMLError as err:
            _LOGGER.error("Error parsing scripts.yaml: %s", err)

        return script_codes

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
                "OpenRouter": self._openrouter,
                "OpenAI Azure": self._openai_azure,
                "Generic OpenAI": self._generic_openai,
                "Codestral": self._codestral,
                "Venice AI": self._veniceai,
                "Open Web UI": self._openwebui,
                "ZhipuAI": self._zhipuai,
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
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["OpenAI"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("OpenAI API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            # Get model-specific parameters
            model_params = self._get_model_parameters(model)

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                model_params['max_tokens_param']: out_budget,
                "temperature": temperature,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(
                ENDPOINT_OPENAI, headers=headers, json=body, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"OpenAI error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")
                
            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")
                
            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")
                
            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")
                
            return res["choices"][0]["message"]["content"]
        
        except Exception as err:
            self._last_error = f"OpenAI processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in OpenAI API call:")
            return None

    # ---------------- OpenAI Azure ---------------------------------------------------
    async def _openai_azure(self, prompt: str) -> str | None:
        """Send prompt to OpenAI Azure endpoint."""
        try:
            endpoint_base = self._opt(CONF_OPENAI_AZURE_ENDPOINT)
            api_key = self._opt(CONF_API_KEY)
            deployment_id = self._opt(CONF_OPENAI_AZURE_DEPLOYMENT_ID)
            api_version = self._opt(CONF_OPENAI_AZURE_API_VERSION, "2025-01-01-preview")
            in_budget, out_budget = self._budgets()
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)

            if not endpoint_base or not deployment_id or not api_version or not api_key:
                raise ValueError("OpenAI Azure endpoint, deployment, api version or API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            endpoint = f"https://{endpoint_base}/openai/deployments/{deployment_id}/chat/completions?api-version={api_version}"

            headers = {
                "api-key": api_key,
                "Content-Type": "application/json",
            }

            # Get model-specific parameters (deployment_id is used as model identifier)
            model_params = self._get_model_parameters(deployment_id)

            body = {
                "messages": [{"role": "user", "content": prompt}],
                model_params['max_tokens_param']: out_budget,
                "temperature": temperature,
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(endpoint, headers=headers, json=body, timeout=timeout) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"OpenAI Azure error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")

            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")

            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")

            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")

            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")

            return res["choices"][0]["message"]["content"]

        except Exception as err:
            self._last_error = f"OpenAI Azure processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in OpenAI Azure API call:")
            return None

    # ---------------- Generic OpenAI ---------------------------------------------
    async def _generic_openai(self, prompt: str) -> str | None:
        try:
            endpoint = self._opt(CONF_GENERIC_OPENAI_ENDPOINT) 
            if not endpoint:
                raise ValueError("Generic OpenAI endpoint not configured")

            # Remove trailing slash if present
            endpoint = endpoint.rstrip('/')
            
            # Ensure the endpoint is a valid URL
            if not re.match(r"^https?://", endpoint):
                raise ValueError("Generic OpenAI endpoint must start with http:// or https://")

            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["Generic OpenAI"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            in_budget, out_budget = self._budgets()

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {"Content-Type": "application/json"}

            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # OpenRouter specific headers
            if "openrouter.ai" in endpoint:
                headers["HTTP-Referer"] = "https://home-assistant.io"
                headers["X-Title"] = "Home Assistant AI Automation Suggester"

            # Get model-specific parameters
            model_params = self._get_model_parameters(model)

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                model_params['max_tokens_param']: out_budget,
                "temperature": temperature,
            }
            timeout = aiohttp.ClientTimeout(total=900)
            async with self.session.post(endpoint, headers=headers, json=body, timeout=timeout) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"Generic OpenAI error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None
                
                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")
                
            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")
                
            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")
                
            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")
                
            return res["choices"][0]["message"]["content"]
        
        except Exception as err:
            self._last_error = f"Generic OpenAI processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Generic OpenAI API call:")
            return None

    # ---------------- Anthropic ------------------------------------------------
    async def _anthropic(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["Anthropic"])
            in_budget, out_budget = self._budgets()
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
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
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": prompt}]}
                ],
                "max_tokens": out_budget,
                "temperature": temperature,
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(
                ENDPOINT_ANTHROPIC, headers=headers, json=body, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"Anthropic error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "content" not in res:
                raise ValueError(f"Response missing 'content' array: {res}")
                
            if not res["content"] or not isinstance(res["content"], list):
                raise ValueError(f"Empty or invalid 'content' array: {res}")
                
            if "text" not in res["content"][0]:
                raise ValueError(f"First choice missing 'text': {res['content'][0]}")
                       
            return res["content"][0]["text"]
        
        except Exception as err:
            self._last_error = f"Anthropic processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Anthropic API call:")
            return None
                

    # ---------------- Google ---------------------------------------------------
    async def _google(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["Google"])
            in_budget, out_budget = self._budgets()
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            thinking_budget = "-1"
            google_search = self._opt(CONF_GOOGLE_ENABLE_SEARCH, False)



            if not api_key:
                raise ValueError("Google API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": out_budget,
                    "topK": 40,
                    "topP": 0.95,
                    "thinkingConfig": {
                        "thinkingBudget": thinking_budget,
                    },
                },
            }

            if google_search:
                body["tools"] = {
                    "google_search": {}
                }
            
            if self._opt(CONF_GOOGLE_THINKING_MODE, "default") == "custom":
                body["generationConfig"]["thinkingConfig"] = {
                    "thinkingBudget": self._opt(CONF_GOOGLE_THINKING_BUDGET, "-1"),
                }
            elif self._opt(CONF_GOOGLE_THINKING_MODE, "default") == "disabled":
                body["generationConfig"]["thinkingConfig"] = {
                    "thinkingBudget": "0"  # Disable thinking budget
                }


            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(endpoint, json=body, timeout=timeout) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"Google error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "candidates" not in res:
                raise ValueError(f"Response missing 'candidates' array: {res}")
                
            if not res["candidates"] or not isinstance(res["candidates"], list):
                raise ValueError(f"Empty or invalid 'candidates' array: {res}")
                
            if "content" not in res["candidates"][0]:
                raise ValueError(f"First choice missing 'content': {res['candidates'][0]}")
                
            if "parts" not in res["candidates"][0]["content"]:
                raise ValueError(f"content missing 'parts': {res['candidates'][0]['content']}")
            
            if not res["candidates"][0]["content"]["parts"] or not isinstance(res["candidates"][0]["content"]["parts"], list):
                raise ValueError(f"Empty or invalid 'parts' array: {res['candidates'][0]['content']}")
            
            if "text" not in res["candidates"][0]["content"]["parts"][0]:
                raise ValueError(f"parts missing 'text': {res['candidates'][0]['content']['parts']}")
            
                
            return res["candidates"][0]["content"]["parts"][0]["text"]
        
        except Exception as err:
            self._last_error = f"Google processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            _LOGGER.error("Response: %s", res)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Google API call:")
            return None
                
    # ---------------- Groq -----------------------------------------------------
    async def _groq(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["Groq"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("Groq API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            body = {
                "model": model,
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": prompt}]}
                ],
                "max_tokens": out_budget,
                "temperature": temperature,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(
                ENDPOINT_GROQ, headers=headers, json=body, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    self._last_error = f"Groq error {resp.status}: {await resp.text()}"
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")
                
            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")
                
            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")
                
            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")
                
            return res["choices"][0]["message"]["content"]
        
        except Exception as err:
            self._last_error = f"Groq processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Groq API call:")
            return None

    # ---------------- LocalAI --------------------------------------------------
    async def _localai(self, prompt: str) -> str | None:
        try:
            ip = self._opt(CONF_LOCALAI_IP_ADDRESS)
            port = self._opt(CONF_LOCALAI_PORT)
            https = self._opt(CONF_LOCALAI_HTTPS, False)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["LocalAI"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
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
                "temperature": temperature,
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(endpoint, json=body, timeout=timeout) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"LocalAI error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")
                
            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")
                
            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")
                
            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")
                
            return res["choices"][0]["message"]["content"]
        
        except Exception as err:
            self._last_error = f"LocalAI processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in LocalAI API call:")
            return None

    # ---------------- Ollama ---------------------------------------------------
    async def _ollama(self, prompt: str) -> str | None:
        try:
            ip = self._opt(CONF_OLLAMA_IP_ADDRESS)
            port = self._opt(CONF_OLLAMA_PORT)
            https = self._opt(CONF_OLLAMA_HTTPS, False)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["Ollama"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            disable_think = self._opt(CONF_OLLAMA_DISABLE_THINK, False)
            in_budget, out_budget = self._budgets()
            if not ip or not port:
                raise ValueError("Ollama not fully configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            proto = "https" if https else "http"
            endpoint = ENDPOINT_OLLAMA.format(protocol=proto, ip_address=ip, port=port)

            messages = []
            if disable_think:
                messages.append({"role": "system", "content": "/no_think"})
            messages.append({"role": "user", "content": prompt})

            body = {
                "model": model,
                "format": "json",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": out_budget,
                },
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(endpoint, json=body, timeout=timeout) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"Ollama error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                # Handle different content types - Ollama may return errors as text/plain
                if resp.content_type != 'application/json':
                    _LOGGER.debug("Ollama response content type: %s", resp.content_type)
                    # Try to parse JSON from the text body; if parsing fails, treat body as plain text
                    resp_text = await resp.text()
                    
                    try:
                        resp_text = await resp.text()
                        res = json.loads(resp_text)
                    except ValueError:
                        # Not JSON — return raw text (server may return plain text with the generated content)
                        return resp_text
                else:
                    res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")

            if "response" not in res:
                raise ValueError(f"Response missing 'response' field: {res}")

            return res["response"]
        
        except Exception as err:
            self._last_error = f"Ollama processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Ollama API call:")            
            return None

    # ---------------- Open Web UI ---------------------------------------------------
    async def _openwebui(self, prompt: str) -> str | None:
        try:
            ip = self._opt(CONF_OPENWEBUI_IP_ADDRESS)
            port = self._opt(CONF_OPENWEBUI_PORT)
            https = self._opt(CONF_OPENWEBUI_HTTPS, False)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["Open Web UI"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            disable_think = self._opt(CONF_OPENWEBUI_DISABLE_THINK, False)
            in_budget, out_budget = self._budgets()
            if not ip or not port:
                raise ValueError("Open Web UI not fully configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            proto = "https" if https else "http"
            endpoint = ENDPOINT_OPENWEBUI.format(protocol=proto, ip_address=ip, port=port)

            messages = []
            if disable_think:
                messages.append({"role": "system", "content": "/no_think"})
            messages.append({"role": "user", "content": prompt})

            headers = {"Content-Type": "application/json"}

            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            body = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": out_budget,
                },
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(endpoint, headers=headers, json=body, timeout=timeout) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"Open Web UI error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "message" not in res:
                raise ValueError(f"Response missing 'message' array: {res}")
                
            if "content" not in res["message"]:
                raise ValueError(f"Message missing 'content': {res['message']}")
                
            return res["message"]["content"]
        
        except Exception as err:
            self._last_error = f"Open Web UI processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Open Web UI API call:")            
            return None

    # ---------------- Custom‑endpoint OpenAI -------------------------------
    async def _custom_openai(self, prompt: str) -> str | None:
        try:
            endpoint = self._opt(CONF_CUSTOM_OPENAI_ENDPOINT) + "/v1/chat/completions"
            if not endpoint:
                raise ValueError("Custom OpenAI endpoint not configured")
            
            if not endpoint.endswith("/v1/chat/completions"):
                endpoint = endpoint.rstrip("/") + "/v1/chat/completions"

            api_key  = self._opt(CONF_API_KEY)
            model    = self._opt(CONF_MODEL, DEFAULT_MODELS["Custom OpenAI"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            in_budget, out_budget = self._budgets()


            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {"Content-Type": "application/json"}

            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # OpenRouter specific headers
            if "openrouter.ai" in endpoint:
                headers["HTTP-Referer"] = "https://home-assistant.io"
                headers["X-Title"] = "Home Assistant AI Automation Suggester"

            # Get model-specific parameters
            model_params = self._get_model_parameters(model)

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                model_params['max_tokens_param']: out_budget,
                "temperature": temperature,
            }
            timeout = aiohttp.ClientTimeout(total=900)
            async with self.session.post(endpoint, headers=headers, json=body, timeout=timeout) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"Custom OpenAI error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None
                
                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")
                
            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")
                
            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")
                
            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")
                
            return res["choices"][0]["message"]["content"]
        
        except Exception as err:
            self._last_error = f"Custom OpenAI processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Custom OpenAI API call:")
            return None

    # ---------------- Mistral ----------------------------------------------
    async def _mistral(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["Mistral AI"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("Mistral API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": out_budget,
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(
                ENDPOINT_MISTRAL, headers=headers, json=body, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"Mistral error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None
                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")
                
            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")
                
            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")
                
            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")
                
            return res["choices"][0]["message"]["content"]
        
        except Exception as err:
            self._last_error = f"Mistral processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Mistral API call:")
            return None

    # ---------------- Codestral ---------------------------------------------
    async def _codestral(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["Codestral"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("Codestral API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": out_budget,
                "temperature": temperature,
            }
            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(
                ENDPOINT_CODESTRAL, headers=headers, json=body, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"Codestral error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")

            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")

            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")

            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")

            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")

            return res["choices"][0]["message"]["content"]

        except Exception as err:
            self._last_error = f"Codestral processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Codestral API call:")
            return None

    # ---------------- Perplexity -------------------------------------------
    async def _perplexity(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["Perplexity AI"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
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
                "temperature": temperature,
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(
                ENDPOINT_PERPLEXITY, headers=headers, json=body, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"Perplexity error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")
                
            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")
                
            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")
                
            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")
                
            return res["choices"][0]["message"]["content"]
        
        except Exception as err:
            self._last_error = f"Perplexity processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in Perplexity API call:")
            return None

    # ---------------- OpenRouter -------------------------------------------
    async def _openrouter(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["OpenRouter"])
            reasoning_max_tokens = self._opt(CONF_OPENROUTER_REASONING_MAX_TOKENS, 0)
            in_budget, out_budget = self._budgets()

            if not api_key:
                raise ValueError("OpenRouter API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://home-assistant.io", 
                "X-Title": "Home Assistant AI Automation Suggester",
            }
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": out_budget,
                "temperature": self._opt(
                    CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                ),
            }

            if reasoning_max_tokens > 0:
                body["reasoning"] = {"max_tokens": reasoning_max_tokens}

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(
                ENDPOINT_OPENROUTER, headers=headers, json=body, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"OpenRouter error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")

            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")

            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")

            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")

            if "content" not in res["choices"][0]["message"]:
                raise ValueError(
                    f"Message missing 'content': {res['choices'][0]['message']}"
                )

            return res["choices"][0]["message"]["content"]

        except Exception as err:
            self._last_error = f"OpenRouter processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in OpenRouter API call:")
            return None

    # ---------------- Venice AI -------------------------------------------
    async def _veniceai(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["VeniceAI"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("VeniceAI API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": out_budget,
                "temperature": temperature,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            timeout = aiohttp.ClientTimeout(total=self._opt(CONF_TIMEOUT, DEFAULT_TIMEOUT))

            async with self.session.post(
                ENDPOINT_VENICEAI, headers=headers, json=body, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"VeniceAI error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")
                
            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")
                
            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")
                
            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")
                
            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")
                
            return res["choices"][0]["message"]["content"]
        
        except Exception as err:
            self._last_error = f"VeniceAI processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in VeniceAI API call:")
            return None

    # ---------------- ZhipuAI --------------------------------------------------
    async def _zhipuai(self, prompt: str) -> str | None:
        try:
            api_key = self._opt(CONF_API_KEY)
            model = self._opt(CONF_MODEL, DEFAULT_MODELS["ZhipuAI"])
            temperature = self._opt(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            in_budget, out_budget = self._budgets()
            if not api_key:
                raise ValueError("ZhipuAI API key not configured")

            if len(prompt) // 4 > in_budget:
                prompt = prompt[: in_budget * 4]

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": out_budget,
                "temperature": temperature,
            }

            timeout = aiohttp.ClientTimeout(total=900)

            async with self.session.post(
                ENDPOINT_ZHIPUAI, headers=headers, json=body, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    self._last_error = (
                        f"ZhipuAI error {resp.status}: {await resp.text()}"
                    )
                    _LOGGER.error(self._last_error)
                    return None

                res = await resp.json()

            if not isinstance(res, dict):
                raise ValueError(f"Unexpected response format: {res}")

            if "choices" not in res:
                raise ValueError(f"Response missing 'choices' array: {res}")

            if not res["choices"] or not isinstance(res["choices"], list):
                raise ValueError(f"Empty or invalid 'choices' array: {res}")

            if "message" not in res["choices"][0]:
                raise ValueError(f"First choice missing 'message': {res['choices'][0]}")

            if "content" not in res["choices"][0]["message"]:
                raise ValueError(f"Message missing 'content': {res['choices'][0]['message']}")

            return res["choices"][0]["message"]["content"]

        except Exception as err:
            self._last_error = f"ZhipuAI processing error: {str(err)}"
            _LOGGER.error(self._last_error)
            # Log stack trace for unexpected errors
            _LOGGER.exception("Unexpected error in ZhipuAI API call:")
            return None

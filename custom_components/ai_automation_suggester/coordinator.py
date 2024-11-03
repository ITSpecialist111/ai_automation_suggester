# custom_components/ai_automation_suggester/coordinator.py

"""Coordinator for AI Automation Suggester."""
import logging
from datetime import datetime
import aiohttp
import json
from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    VERSION_ANTHROPIC,
    ENDPOINT_OPENAI,
    ENDPOINT_ANTHROPIC,
    ENDPOINT_GOOGLE,
    ENDPOINT_GROQ,
    ENDPOINT_LOCALAI,
    ENDPOINT_OLLAMA,
)

_LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI assistant that generates Home Assistant automations 
based on the types of new entities discovered in the system. Your goal 
is to provide detailed and useful automation suggestions tailored to 
the specific types and functions of the entities, avoiding generic recommendations.

For each entity:
1. Understand its function (e.g., sensor, switch, light, climate control).
2. Consider its current state (e.g., 'on', 'off', 'open', 'closed', 'temperature').
3. Suggest automations based on common use cases for similar entities.
4. Avoid generic suggestions. Instead, provide detailed scenarios such as:
   - 'If the front door sensor detects it is open for more than 5 minutes, send a notification.'
   - 'If no motion is detected for 10 minutes, turn off all lights.'
   - 'If the temperature sensor detects a rise above 25°C, turn on the air conditioner.'
5. Consider combining multiple entities to create context-aware automations.
6. Include appropriate conditions and triggers for time of day, presence, or other contextual factors.
7. Format suggestions in clear, implementable steps.
8. When suggesting scenes, include all relevant entities that should be controlled.
9. Consider energy efficiency and user convenience in your suggestions.
10. Include the actual entity IDs in your suggestions so they can be easily implemented.
11. Suggest automations that make sense based on the entity's domain and capabilities.
12. Consider security implications for sensitive automations (like doors or windows)."""

class AIAutomationCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from AI model."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self.previous_entities = {}
        self.last_update = None
        self.SYSTEM_PROMPT = SYSTEM_PROMPT

        # Initialize data
        self.data = {
            "suggestions": "No suggestions yet",
            "last_update": None,
            "entities_processed": [],
            "provider": entry.data.get(CONF_PROVIDER, "unknown")
        }

        # Prevent automatic updates by setting update_interval to None
        self.update_interval = None

        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self.update_interval,
        )

    async def _async_update_data(self):
        """Fetch data from AI model."""
        try:
            current_time = datetime.now()
            
            _LOGGER.debug("Starting manual update at %s", current_time)

            self.last_update = current_time

            # Fetch current entities
            _LOGGER.debug("Fetching current entities")
            try:
                current_entities = {}
                for entity_id in self.hass.states.async_entity_ids():
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

            # Detect newly added entities
            new_entities = {
                k: v for k, v in current_entities.items()
                if k not in self.previous_entities
            }

            if not new_entities:
                _LOGGER.debug("No new entities detected")
                return self.data

            # Limit processing to 10 entities if needed
            if len(new_entities) > 10:
                _LOGGER.debug("Limiting to 10 entities for processing")
                new_entities = dict(list(new_entities.items())[:10])

            # Prepare AI input
            ai_input_data = self.prepare_ai_input(new_entities)
            
            # Get suggestions from AI
            suggestions = await self.get_ai_suggestions(ai_input_data)
            
            if suggestions:
                _LOGGER.debug("Received suggestions: %s", suggestions)
                try:
                    # Create notification only if suggestions is not None
                    notification = await persistent_notification.async_create(
                        self.hass,
                        message=suggestions,
                        title="AI Automation Suggestions",
                        notification_id=f"ai_automation_suggestions_{current_time.timestamp()}"
                    )
                    
                    # Update data regardless of notification success
                    self.data = {
                        "suggestions": suggestions,
                        "last_update": current_time,
                        "entities_processed": list(new_entities.keys()),
                        "provider": self.entry.data.get(CONF_PROVIDER, "unknown")
                    }
                except Exception as err:
                    _LOGGER.error("Error creating notification: %s", err)
                    # Still update data even if notification fails
                    self.data = {
                        "suggestions": suggestions,
                        "last_update": current_time,
                        "entities_processed": list(new_entities.keys()),
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

            # Always update previous entities list
            self.previous_entities = current_entities
            
            return self.data

        except Exception as err:
            _LOGGER.error("Unexpected error in update: %s", err)
            return self.data

    def prepare_ai_input(self, new_entities):
        """Prepare the input data for AI processing."""
        _LOGGER.debug("Preparing AI input for %d entities", len(new_entities))
        
        entities_description = []
        for entity_id, entity_data in new_entities.items():
            state = entity_data.get('state', 'unknown')
            attributes = entity_data.get('attributes', {})
            friendly_name = entity_data.get('friendly_name', entity_id)
            domain = entity_id.split('.')[0]
            
            # Enhanced entity description
            description = (
                f"Entity: {entity_id}\n"
                f"Friendly Name: {friendly_name}\n"
                f"Domain: {domain}\n"
                f"State: {state}\n"
                f"Attributes: {attributes}\n"
                f"Last Changed: {entity_data.get('last_changed', 'unknown')}\n"
                f"Last Updated: {entity_data.get('last_updated', 'unknown')}\n"
                f"---\n"
            )
            entities_description.append(description)

        prompt = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"New entities discovered:\n"
            f"{''.join(entities_description)}\n"
            f"Please suggest detailed and specific automations for these entities, "
            f"using their exact entity IDs in the suggestions."
        )
        return prompt

    async def get_ai_suggestions(self, prompt):
        """Get suggestions from the configured AI provider."""
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
            else:
                _LOGGER.error("Unknown provider: %s", provider)
                return None
        except Exception as err:
            _LOGGER.error("Error getting suggestions: %s", err)
            return None

    async def process_with_openai(self, prompt):
        """Process the prompt with OpenAI."""
        try:
            api_key = self.entry.data.get(CONF_OPENAI_API_KEY)
            model = self.entry.data.get(CONF_OPENAI_MODEL, DEFAULT_MODELS["OpenAI"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            
            if not api_key:
                raise ValueError("OpenAI API key not configured")

            _LOGGER.debug("Making OpenAI API request with model %s and max_tokens %d", 
                        model, max_tokens)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": DEFAULT_TEMPERATURE
            }
            
            async with self.session.post(
                ENDPOINT_OPENAI,
                headers=headers,
                json=data
            ) as response:
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
        """Process the prompt with Anthropic."""
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
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": DEFAULT_TEMPERATURE
            }
            
            async with self.session.post(
                ENDPOINT_ANTHROPIC,
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Anthropic API error: %s", error_text)
                    return None
                    
                result = await response.json()
                return result["content"][0]["text"]

        except Exception as err:
            _LOGGER.error("Error processing with Anthropic: %s", err)
            return None

    async def process_with_google(self, prompt):
        """Process the prompt with Google."""
        try:
            api_key = self.entry.data.get(CONF_GOOGLE_API_KEY)
            model = self.entry.data.get(CONF_GOOGLE_MODEL, DEFAULT_MODELS["Google"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            
            if not api_key:
                raise ValueError("Google API key not configured")

            _LOGGER.debug("Making Google API request with model %s and max_tokens %d", 
                        model, max_tokens)
            
            headers = {
                "Content-Type": "application/json",
            }
            
            data = {
                "prompt": {
                    "text": prompt
                },
                "temperature": DEFAULT_TEMPERATURE,
                "candidate_count": 1,
                "max_output_tokens": max_tokens
            }
            
            endpoint = ENDPOINT_GOOGLE.format(model=model, api_key=api_key)
            
            async with self.session.post(
                endpoint,
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Google API error: %s", error_text)
                    return None
                    
                result = await response.json()
                return result["candidates"][0]["output"]

        except Exception as err:
            _LOGGER.error("Error processing with Google: %s", err)
            return None

    async def process_with_groq(self, prompt):
        """Process the prompt with Groq."""
        try:
            api_key = self.entry.data.get(CONF_GROQ_API_KEY)
            model = self.entry.data.get(CONF_GROQ_MODEL, DEFAULT_MODELS["Groq"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            
            if not api_key:
                raise ValueError("Groq API key not configured")

            _LOGGER.debug("Making Groq API request with model %s and max_tokens %d", 
                        model, max_tokens)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            data = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                "model": model,
                "max_tokens": max_tokens,
                "temperature": DEFAULT_TEMPERATURE
            }
            
            async with self.session.post(
                ENDPOINT_GROQ,
                headers=headers,
                json=data
            ) as response:
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
        """Process the prompt with LocalAI."""
        try:
            ip_address = self.entry.data.get(CONF_LOCALAI_IP_ADDRESS)
            port = self.entry.data.get(CONF_LOCALAI_PORT)
            https = self.entry.data.get(CONF_LOCALAI_HTTPS, False)
            model = self.entry.data.get(CONF_LOCALAI_MODEL, DEFAULT_MODELS["LocalAI"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            
            if not ip_address or not port:
                raise ValueError("LocalAI configuration incomplete")

            protocol = "https" if https else "http"
            endpoint = ENDPOINT_LOCALAI.format(
                protocol=protocol,
                ip_address=ip_address,
                port=port
            )
            
            _LOGGER.debug("Making LocalAI API request to %s with model %s and max_tokens %d", 
                        endpoint, model, max_tokens)
            
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": DEFAULT_TEMPERATURE
            }
            
            async with self.session.post(
                endpoint,
                json=data
            ) as response:
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
        """Process the prompt with Ollama."""
        try:
            ip_address = self.entry.data.get(CONF_OLLAMA_IP_ADDRESS)
            port = self.entry.data.get(CONF_OLLAMA_PORT)
            https = self.entry.data.get(CONF_OLLAMA_HTTPS, False)
            model = self.entry.data.get(CONF_OLLAMA_MODEL, DEFAULT_MODELS["Ollama"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            
            if not ip_address or not port:
                raise ValueError("Ollama configuration incomplete")

            protocol = "https" if https else "http"
            endpoint = ENDPOINT_OLLAMA.format(
                protocol=protocol,
                ip_address=ip_address,
                port=port
            )
            
            _LOGGER.debug("Making Ollama API request to %s with model %s and max_tokens %d", 
                        endpoint, model, max_tokens)
            
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": DEFAULT_TEMPERATURE,
                    "num_predict": max_tokens
                }
            }
            
            async with self.session.post(
                endpoint,
                json=data
            ) as response:
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
        """Process the prompt with Custom OpenAI-compatible API."""
        try:
            endpoint = self.entry.data.get(CONF_CUSTOM_OPENAI_ENDPOINT)
            api_key = self.entry.data.get(CONF_CUSTOM_OPENAI_API_KEY)
            model = self.entry.data.get(CONF_CUSTOM_OPENAI_MODEL, DEFAULT_MODELS["Custom OpenAI"])
            max_tokens = self.entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            
            if not endpoint:
                raise ValueError("Custom OpenAI endpoint not configured")

            _LOGGER.debug("Making Custom OpenAI API request to %s with model %s and max_tokens %d", 
                        endpoint, model, max_tokens)
            
            headers = {
                "Content-Type": "application/json",
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": DEFAULT_TEMPERATURE
            }
            
            async with self.session.post(
                endpoint,
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Custom OpenAI API error: %s", error_text)
                    return None
                    
                result = await response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as err:
            _LOGGER.error("Error processing with Custom OpenAI: %s", err)
            return None

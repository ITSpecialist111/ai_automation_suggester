"""Coordinator for AI Automation Suggester."""
import logging
from datetime import timedelta

from homeassistant.components.persistent_notification import async_create
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AIAutomationCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from AI model."""

    def __init__(self, hass: HomeAssistant, entry):
        """Initialize."""
        self.hass = hass
        self.entry = entry
        update_interval = timedelta(hours=entry.data.get("scan_frequency", 24))
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.previous_entities = {}

    async def _async_update_data(self):
        """Fetch data from AI model."""
        # Fetch the list of current entities
        current_entities = {
            entity_id: self.hass.states.get(entity_id).as_dict()
            for entity_id in self.hass.states.async_entity_ids()
        }

        # Detect newly added entities
        new_entities = {
            k: v for k, v in current_entities.items() if k not in self.previous_entities
        }

        # Limit the number of new entities to process
        MAX_NEW_ENTITIES = 10
        total_new_entities = len(new_entities)
        if total_new_entities > MAX_NEW_ENTITIES:
            # Limit the new_entities to MAX_NEW_ENTITIES
            new_entities = dict(list(new_entities.items())[:MAX_NEW_ENTITIES])

        # Prepare data for AI analysis
        ai_input_data = {
            "new_entities": new_entities,
        }

        # Process data with AI model
        suggestions = await self.hass.async_add_executor_job(
            self.get_ai_suggestions, ai_input_data
        )

        # Update previous entities
        self.previous_entities = current_entities

        # Create a persistent notification with suggestions
        if suggestions:
            async_create(
                hass=self.hass,
                title="AI Automation Suggestions",
                message=suggestions,
                notification_id="ai_automation_suggestions"
            )

        return suggestions

    def get_ai_suggestions(self, ai_input_data):
        """Process data with AI model (synchronously)."""
        use_local_ai = self.entry.data.get("use_local_ai", False)
        if use_local_ai:
            # Implement local AI processing
            return self.local_ai_analysis(ai_input_data)
        else:
            # Implement cloud AI processing
            return self.cloud_ai_analysis(ai_input_data)

    def local_ai_analysis(self, ai_input_data):
        """Analyze data using a local AI model."""
        # Placeholder for local AI logic
        return "Local AI analysis is not yet implemented."

    def cloud_ai_analysis(self, ai_input_data):
        """Analyze data using the OpenAI ChatCompletion API."""
        import openai

        api_key = self.entry.data.get("openai_api_key")
        if not api_key:
            _LOGGER.error("OpenAI API key is missing.")
            return "OpenAI API key is missing."

        openai.api_key = api_key

        prompt = self.generate_prompt(ai_input_data)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant that suggests Home Assistant automations based on new entities.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                n=1,
                temperature=0.7,
            )

            suggestions = response.choices[0].message.content.strip()
            return suggestions
        except Exception as e:
            _LOGGER.error(f"Error communicating with OpenAI: {e}")
            return f"Error communicating with OpenAI: {e}"

    def generate_prompt(self, ai_input_data):
        """Generate prompt for AI model."""
        # Simplify the data to make the prompt manageable
        new_entities_list = [
            f"{entity_id}: {entity['state']}"
            for entity_id, entity in ai_input_data['new_entities'].items()
        ]

        # Limit the number of entities included
        MAX_ENTITIES = 10
        total_new_entities = len(new_entities_list)
        if total_new_entities > MAX_ENTITIES:
            new_entities_list = new_entities_list[:MAX_ENTITIES]
            entities_info = f"{MAX_ENTITIES} of {total_new_entities} new entities"
        else:
            entities_info = f"{total_new_entities} new entities"

        prompt = (
            f"Analyze the following {entities_info} added to my Home Assistant setup and suggest potential automations:\n"
        )
        prompt += "\n".join(new_entities_list)
        prompt += "\n\nProvide the suggestions in a clear and concise manner."
        return prompt

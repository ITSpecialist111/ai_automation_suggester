"""Coordinator for AI Automation Suggester."""
import logging
from datetime import timedelta, datetime
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
        self.previous_entities = {}  # Initialize previous_entities to an empty dictionary
        self.last_update = None  # Track the last update time
        scan_frequency = entry.data.get("scan_frequency", 24)
        initial_lag_time = entry.data.get("initial_lag_time", 10)  # Default to 10 minutes lag

        if scan_frequency == 0:
            self.update_interval = None  # Disable automatic updates
        else:
            self.update_interval = timedelta(hours=scan_frequency)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=self.update_interval)

        # Set the initial update delay
        if initial_lag_time > 0:
            _LOGGER.debug(f"Delaying initial suggestions by {initial_lag_time} minutes.")
            self.hass.loop.call_later(initial_lag_time * 60, self.async_request_refresh)

    async def _async_update_data(self):
        """Fetch data from AI model."""
        current_time = datetime.now()

        # Check if scan frequency has passed
        if self.last_update and current_time - self.last_update < self.update_interval:
            _LOGGER.debug("Skipping update, scan frequency interval not reached.")
            return self.previous_entities  # Return previous data without update

        # Proceed with the regular update process
        self.last_update = current_time  # Update the last fetch time

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
            new_entities = dict(list(new_entities.items())[:MAX_NEW_ENTITIES])

        ai_input_data = {"new_entities": new_entities}

        suggestions = await self.hass.async_add_executor_job(
            self.get_ai_suggestions, ai_input_data
        )

        self.previous_entities = current_entities  # Update previous_entities with current ones

        if suggestions:
            async_create(
                hass=self.hass,
                title="AI Automation Suggestions",
                message=suggestions,
                notification_id="ai_automation_suggestions"
            )

        return suggestions


    def get_ai_suggestions(self, ai_input_data):
        """Process data with AI model."""
        use_local_ai = self.entry.data.get("use_local_ai", False)
        if use_local_ai:
            return self.local_ai_analysis(ai_input_data)
        else:
            return self.cloud_ai_analysis(ai_input_data)

    def local_ai_analysis(self, ai_input_data):
        """Analyze data using a local AI model."""
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
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI assistant that generates Home Assistant automations "
                            "based on the types of new entities discovered in the system. Your goal "
                            "is to provide detailed and useful automation suggestions tailored to "
                            "the specific types and functions of the entities, avoiding generic recommendations. "
                            "For each entity:\n"
                            "1. Understand its function (e.g., sensor, switch, light, climate control).\n"
                            "2. Consider its current state (e.g., 'on', 'off', 'open', 'closed', 'temperature').\n"
                            "3. Suggest automations based on common use cases for similar entities.\n"
                            "4. Avoid generic suggestions. Instead, provide detailed scenarios such as:\n"
                            "- 'If the front door sensor detects it is open for more than 5 minutes, send a notification.'\n"
                            "- 'If no motion is detected for 10 minutes, turn off all lights.'\n"
                            "- 'If the temperature sensor detects a rise above 25°C, turn on the air conditioner.'\n"
                            "5. Consider combining multiple entities to create context-aware automations."
                        )
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
        new_entities_list = [
            f"{entity_id}: {entity['state']}"
            for entity_id, entity in ai_input_data['new_entities'].items()
        ]

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

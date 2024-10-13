"""Main logic for the AI Suggester integration."""
import json
import os
import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, ENTITY_DATA_FILE, SUGGESTIONS_FILE

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the AI Suggester component."""
    # Register services
    async def scan_entities(call: ServiceCall):
        """Scan entities and process AI suggestions."""
        await scan_and_process(hass)

    hass.services.async_register(DOMAIN, "scan_entities", scan_entities)

    return True

async def scan_and_process(hass: HomeAssistant):
    """Scan entities and process suggestions."""
    current_entities = {state.entity_id: state.as_dict() for state in hass.states.async_all()}
    entity_data_path = hass.config.path(ENTITY_DATA_FILE)

    if os.path.exists(entity_data_path):
        with open(entity_data_path, 'r') as f:
            previous_entities = json.load(f)
    else:
        previous_entities = {}

    # Identify newly added entities
    new_entities = {eid: data for eid, data in current_entities.items() if eid not in previous_entities}

    # Save current entities for the next comparison
    with open(entity_data_path, 'w') as f:
        json.dump(current_entities, f)

    # Proceed with AI analysis
    await analyze_entities(hass, current_entities, new_entities)

async def analyze_entities(hass: HomeAssistant, all_entities: dict, new_entities: dict):
    """Analyze entities and get AI suggestions."""
    # Prepare data for AI model
    data = {
        "all_entities": summarize_entities(all_entities),
        "new_entities": summarize_entities(new_entities),
    }

    # Call AI model integration
    suggestions = await hass.async_add_executor_job(call_ai_model, data, hass)

    # Process suggestions
    await process_suggestions(hass, suggestions)

def summarize_entities(entities):
    """Summarize entities for AI processing."""
    summarized = []
    for entity_id, data in entities.items():
        entity_info = {
            "entity_id": entity_id,
            "state": data["state"],
            "attributes": data["attributes"],
        }
        summarized.append(entity_info)
    return summarized

def call_ai_model(data, hass):
    """Call the AI model to get automation suggestions."""
    import openai
    ##The OpenAI API key is accessed from hass.data[DOMAIN]["api_key"], which should be stored during configuration.##
    openai.api_key = hass.data[DOMAIN]["api_key"]
    ##Replace "GPT-40" with the appropriate model##
    prompt = generate_prompt(data)
    response = openai.Completion.create(
        engine="gpt-4o",
        prompt=prompt,
        max_tokens=500,
        temperature=0.7,
    )
    suggestions = parse_ai_response(response.choices[0].text)
    return suggestions

def generate_prompt(data):
    """Generate prompt for AI model."""
    prompt = (
        "Based on the following Home Assistant entities, suggest possible automations. "
        "Use placeholders for entity names. Do not include actual entity IDs.\n\n"
        f"All Entities:\n{data['all_entities']}\n\n"
        f"New Entities:\n{data['new_entities']}\n\n"
        "Provide suggestions in the following JSON format:\n"
        "{\n"
        "  \"suggestions\": [\n"
        "    {\n"
        "      \"description\": \"...\",\n"
        "      \"placeholders\": [\"...\"],\n"
        "      \"template\": \"...\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )
    return prompt

def parse_ai_response(response_text):
    """Parse the AI model's response."""
    try:
        suggestions = json.loads(response_text)
    except json.JSONDecodeError:
        suggestions = {"suggestions": []}
    return suggestions

async def process_suggestions(hass: HomeAssistant, suggestions: dict):
    """Store suggestions and notify user."""
    suggestions_file_path = hass.config.path(SUGGESTIONS_FILE)
    with open(suggestions_file_path, 'w') as f:
        json.dump(suggestions, f)

    # Create a persistent notification
    await hass.services.async_call(
        'persistent_notification',
        'create',
        {
            'title': 'New Automation Suggestions',
            'message': 'AI-generated automation suggestions are available.',
            'notification_id': 'ai_automation_suggestions'
        }
    )

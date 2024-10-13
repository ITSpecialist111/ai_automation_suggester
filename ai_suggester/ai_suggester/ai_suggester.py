"""Main logic for the AI Suggester integration."""
import json
import os
import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, ENTITY_DATA_FILE, SUGGESTIONS_FILE

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the AI Suggester component."""
    # Register services
    async def scan_entities(call: ServiceCall):
        """Scan entities and process AI suggestions."""
        await scan_and_process(hass)

    async def accept_suggestion(call: ServiceCall):
        """Handle accepting a suggestion."""
        index = call.data.get('index')
        await handle_accept_suggestion(hass, index)

    async def reject_suggestion(call: ServiceCall):
        """Handle rejecting a suggestion."""
        index = call.data.get('index')
        await handle_reject_suggestion(hass, index)

    hass.services.async_register(DOMAIN, "scan_entities", scan_entities)
    hass.services.async_register(DOMAIN, "accept_suggestion", accept_suggestion)
    hass.services.async_register(DOMAIN, "reject_suggestion", reject_suggestion)

    return True


async def scan_and_process(hass: HomeAssistant):
    """Scan entities and process suggestions."""
    current_entities = {
        state.entity_id: state.as_dict() for state in hass.states.async_all()
    }
    entity_data_path = hass.config.path(ENTITY_DATA_FILE)

    if os.path.exists(entity_data_path):
        with open(entity_data_path, 'r') as f:
            previous_entities = json.load(f)
    else:
        previous_entities = {}

    # Identify newly added entities
    new_entities = {
        eid: data for eid, data in current_entities.items() if eid not in previous_entities
    }

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

    openai.api_key = hass.data[DOMAIN]["api_key"]

    prompt = generate_prompt(data)
    response = openai.Completion.create(
        engine="text-davinci-003",
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
        _LOGGER.error("Failed to parse AI response as JSON.")
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


async def handle_accept_suggestion(hass: HomeAssistant, index: int):
    """Process accepted suggestion."""
    suggestions_file_path = hass.config.path(SUGGESTIONS_FILE)
    if os.path.exists(suggestions_file_path):
        with open(suggestions_file_path, 'r') as f:
            suggestions = json.load(f)
    else:
        suggestions = {"suggestions": []}

    if index < 0 or index >= len(suggestions['suggestions']):
        _LOGGER.error(f"Invalid suggestion index: {index}")
        return

    suggestion = suggestions['suggestions'].pop(index)

    # Save updated suggestions
    with open(suggestions_file_path, 'w') as f:
        json.dump(suggestions, f)

    # Proceed to entity mapping and automation creation
    await process_accepted_suggestion(hass, suggestion)


async def handle_reject_suggestion(hass: HomeAssistant, index: int):
    """Process rejected suggestion."""
    suggestions_file_path = hass.config.path(SUGGESTIONS_FILE)
    if os.path.exists(suggestions_file_path):
        with open(suggestions_file_path, 'r') as f:
            suggestions = json.load(f)
    else:
        suggestions = {"suggestions": []}

    if index < 0 or index >= len(suggestions['suggestions']):
        _LOGGER.error(f"Invalid suggestion index: {index}")
        return

    suggestions['suggestions'].pop(index)

    # Save updated suggestions
    with open(suggestions_file_path, 'w') as f:
        json.dump(suggestions, f)

    # Optionally, store feedback for AI model
    _LOGGER.info(f"Suggestion at index {index} rejected by user.")


async def process_accepted_suggestion(hass: HomeAssistant, suggestion: dict):
    """Map placeholders to entities and create automation."""
    placeholders = suggestion.get('placeholders', [])
    description = suggestion.get('description', 'No description provided.')
    template = suggestion.get('template', '')

    if not template:
        _LOGGER.error("No template provided in the suggestion.")
        return

    # Prompt user for entity mapping
    entity_mapping = await prompt_user_for_entity_mapping(hass, placeholders, description)

    # Generate automation
    automation_yaml = generate_automation(template, entity_mapping)

    # Add automation to Home Assistant
    await add_automation(hass, automation_yaml)


async def prompt_user_for_entity_mapping(hass: HomeAssistant, placeholders: list, description: str):
    """Prompt the user to map placeholders to actual entities."""
    # Implement a user interface or notification to collect this information
    # For demonstration purposes, we'll log the placeholders and use mock inputs
    _LOGGER.info(f"Placeholders to map: {placeholders}")
    _LOGGER.info(f"Automation description: {description}")

    # TODO: Replace this with actual user input mechanism
    entity_mapping = {}
    for placeholder in placeholders:
        # In a real implementation, you would present the user with a selection of entities
        # Here, we'll just use a dummy entity ID
        entity_mapping[placeholder] = "dummy_entity_id"
    return entity_mapping


def generate_automation(template: str, entity_mapping: dict):
    """Generate automation YAML from template and entity mapping."""
    try:
        automation_yaml = template.format(**entity_mapping)
        return automation_yaml
    except KeyError as e:
        _LOGGER.error(f"Placeholder missing in entity mapping: {e}")
        return None


async def add_automation(hass: HomeAssistant, automation_yaml: str):
    """Add the generated automation to Home Assistant."""
    if not automation_yaml:
        _LOGGER.error("No automation YAML to add.")
        return

    automations_path = hass.config.path('automations.yaml')

    # Check if automations.yaml exists; create if it doesn't
    if not os.path.exists(automations_path):
        with open(automations_path, 'w') as f:
            f.write('')

    # Append the new automation
    try:
        with open(automations_path, 'a') as f:
            f.write('\n')
            f.write(automation_yaml)
            f.write('\n')
    except Exception as e:
        _LOGGER.error(f"Failed to write automation to file: {e}")
        return

    # Reload automations
    await hass.services.async_call('automation', 'reload')
    _LOGGER.info("Automation added and reloaded successfully.")

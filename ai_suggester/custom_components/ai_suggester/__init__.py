"""Initialize the AI Suggester integration."""
import logging
import os
import json

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView  # Import HomeAssistantView
# If you use any other imports, include them here

from .const import DOMAIN, SUGGESTIONS_FILE  # Ensure SUGGESTIONS_FILE is imported

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the AI Suggester integration."""
    hass.data.setdefault(DOMAIN, {})

    # Register the HTTP view to serve suggestions
    hass.http.register_view(AISuggestionsView)

    # If you have other setup tasks, include them here
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up AI Suggester from a config entry."""
    hass.data[DOMAIN][entry.entry_id] = {}

    # Store the API key from the config entry for use in other components
    hass.data[DOMAIN]["api_key"] = entry.data.get("api_key")

    # If you have other entry setup tasks, include them here

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Perform any necessary cleanup

    hass.data[DOMAIN].pop(entry.entry_id)

    return True

# Add the AISuggestionsView class here
class AISuggestionsView(HomeAssistantView):
    """View to serve AI suggestions."""

    url = "/api/ai_suggester/suggestions"
    name = "api:ai_suggester:suggestions"
    requires_auth = True  # Ensure that only authenticated users can access this view

    async def get(self, request):
        """Return AI suggestions."""
        hass = request.app["hass"]
        suggestions_file_path = hass.config.path(SUGGESTIONS_FILE)

        if os.path.exists(suggestions_file_path):
            with open(suggestions_file_path, 'r') as f:
                suggestions = json.load(f)
        else:
            suggestions = {"suggestions": []}

        return self.json(suggestions)

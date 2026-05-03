"""HTTP API endpoints for stored automation suggestions."""

from __future__ import annotations

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .store import async_get_suggestion_store


class AISuggestionsView(HomeAssistantView):
    """Return stored suggestions for Lovelace cards and dashboards."""

    url = "/api/ai_automation_suggester/suggestions"
    name = "api:ai_automation_suggester:suggestions"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        store = async_get_suggestion_store(hass)
        return self.json(await store.async_list())


class AISuggestionActionView(HomeAssistantView):
    """Update a suggestion action from the existing custom card."""

    url = "/api/ai_automation_suggester/{action}/{suggestion_id}"
    name = "api:ai_automation_suggester:suggestion_action"
    requires_auth = True

    async def post(self, request: web.Request, action: str, suggestion_id: str) -> web.Response:
        status_map = {
            "accept": "accepted",
            "decline": "declined",
            "dismiss": "dismissed",
        }
        if action not in status_map:
            return self.json({"success": False, "error": "Unsupported action"}, status_code=400)

        hass: HomeAssistant = request.app["hass"]
        store = async_get_suggestion_store(hass)
        suggestion = await store.async_update_status(suggestion_id, status_map[action])
        if suggestion is None:
            return self.json({"success": False, "error": "Suggestion not found"}, status_code=404)
        return self.json({"success": True, "suggestion": suggestion})


def async_register_http_views(hass: HomeAssistant) -> None:
    """Register HTTP API views."""

    hass.http.register_view(AISuggestionsView())
    hass.http.register_view(AISuggestionActionView())
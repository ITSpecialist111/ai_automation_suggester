"""Persistent suggestion history storage."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DEFAULT_HISTORY_RETENTION, DOMAIN

STORE_VERSION = 1
STORE_KEY = f"{DOMAIN}.suggestions"
STORE_DATA_KEY = "suggestions"
HASS_STORE_KEY = "_suggestion_store"


class SuggestionStore:
    """Small wrapper around Home Assistant storage helper."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, STORE_KEY)
        self._data: dict[str, Any] | None = None
        self._load_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    async def _async_load(self) -> dict[str, Any]:
        if self._data is None:
            async with self._load_lock:
                if self._data is None:
                    self._data = await self._store.async_load() or {STORE_DATA_KEY: []}
                    self._data.setdefault(STORE_DATA_KEY, [])
        return self._data

    async def async_list(self) -> list[dict[str, Any]]:
        """Return stored suggestions, newest first."""

        data = await self._async_load()
        return deepcopy(data.get(STORE_DATA_KEY, []))

    async def async_add_suggestions(
        self,
        suggestions: list[dict[str, Any]],
        retention: int = DEFAULT_HISTORY_RETENTION,
    ) -> list[dict[str, Any]]:
        """Persist suggestions and return the new stored list."""

        async with self._write_lock:
            data = await self._async_load()
            current = list(data.get(STORE_DATA_KEY, []))
            data[STORE_DATA_KEY] = suggestions + current
            if retention > 0:
                data[STORE_DATA_KEY] = data[STORE_DATA_KEY][:retention]
            await self._store.async_save(data)
            return deepcopy(data[STORE_DATA_KEY])

    async def async_update_status(self, suggestion_id: str, status: str) -> dict[str, Any] | None:
        """Update a suggestion status such as accepted, declined, or dismissed."""

        async with self._write_lock:
            data = await self._async_load()
            for suggestion in data.get(STORE_DATA_KEY, []):
                if suggestion.get("id") == suggestion_id:
                    suggestion["status"] = status
                    await self._store.async_save(data)
                    return deepcopy(suggestion)
        return None

    async def async_clear(self) -> None:
        """Clear all stored suggestions."""

        async with self._write_lock:
            data = await self._async_load()
            data[STORE_DATA_KEY] = []
            await self._store.async_save(data)


def async_get_suggestion_store(hass: HomeAssistant) -> SuggestionStore:
    """Return the singleton suggestion store for this Home Assistant instance."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get(HASS_STORE_KEY)
    if store is None:
        store = SuggestionStore(hass)
        domain_data[HASS_STORE_KEY] = store
    return store
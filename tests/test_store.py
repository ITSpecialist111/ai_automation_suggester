"""Tests for atomic suggestion storage operations."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.ai_automation_suggester import store as store_module


class MemoryStore:
    def __init__(self, *args):
        self.data = None
        self.saved = []

    async def async_load(self):
        await asyncio.sleep(0)
        return self.data

    async def async_save(self, data):
        await asyncio.sleep(0)
        self.data = {"suggestions": [dict(item) for item in data["suggestions"]]}
        self.saved.append(self.data)


def make_store(monkeypatch):
    monkeypatch.setattr(store_module, "Store", MemoryStore)
    return store_module.SuggestionStore(SimpleNamespace())


def test_concurrent_adds_do_not_lose_suggestions(monkeypatch):
    suggestion_store = make_store(monkeypatch)

    async def run():
        await asyncio.gather(
            suggestion_store.async_add_suggestions([{"id": "one"}], retention=10),
            suggestion_store.async_add_suggestions([{"id": "two"}], retention=10),
        )
        return await suggestion_store.async_list()

    history = asyncio.run(run())

    assert {item["id"] for item in history} == {"one", "two"}


def test_status_update_and_clear_are_persisted(monkeypatch):
    suggestion_store = make_store(monkeypatch)

    async def run():
        await suggestion_store.async_add_suggestions([{"id": "one", "status": "new"}])
        updated = await suggestion_store.async_update_status("one", "accepted")
        await suggestion_store.async_clear()
        return updated, await suggestion_store.async_list()

    updated, history = asyncio.run(run())

    assert updated["status"] == "accepted"
    assert history == []

"""Coordinator regression tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from custom_components.ai_automation_suggester import coordinator as coordinator_module


class FakeSession:
    pass


class FakeStates:
    def __init__(self, states):
        self._states = states

    def async_entity_ids(self, domain=None):
        if domain is None:
            return list(self._states)
        return [entity_id for entity_id in self._states if entity_id.startswith(f"{domain}.")]

    def get(self, entity_id):
        return self._states.get(entity_id)


class FakeServices:
    def __init__(self, services=()):
        self._services = set(services)

    def has_service(self, domain, service):
        return f"{domain}.{service}" in self._services


class FakeRegistry:
    def __init__(self, entries=None):
        self.entries = entries or {}

    def async_get(self, key):
        return self.entries.get(key)


class FakeAreaRegistry(FakeRegistry):
    def async_get_area(self, key):
        return self.entries.get(key)


@dataclass
class FakeEntry:
    data: dict
    options: dict

    def async_on_unload(self, callback):
        return callback


class FakeHass:
    def __init__(self, states):
        self.states = FakeStates(states)
        self.services = FakeServices({"light.turn_on"})
        self.config = SimpleNamespace(language="en", path=lambda: ".")
        self.session = FakeSession()
        self.data = {}


def make_state(entity_id: str, state: str, attributes=None):
    timestamp = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    return SimpleNamespace(
        entity_id=entity_id,
        state=state,
        attributes=attributes or {"friendly_name": entity_id},
        last_changed=timestamp,
        last_updated=timestamp,
    )


def make_coordinator(monkeypatch, *, states, options=None):
    device_registry = FakeRegistry()
    entity_registry = FakeRegistry()
    area_registry = FakeAreaRegistry()
    monkeypatch.setattr(coordinator_module, "async_get_clientsession", lambda hass: hass.session)
    monkeypatch.setattr(coordinator_module.dr, "async_get", lambda hass: device_registry)
    monkeypatch.setattr(coordinator_module.er, "async_get", lambda hass: entity_registry)
    monkeypatch.setattr(coordinator_module.ar, "async_get", lambda hass: area_registry)
    hass = FakeHass(states)
    entry = FakeEntry(data={"provider": "OpenAI"}, options=options or {})
    coordinator = coordinator_module.AIAutomationCoordinator(hass, entry)
    return coordinator, entity_registry, area_registry


def test_registries_are_initialized_during_construction(monkeypatch):
    coordinator, entity_registry, area_registry = make_coordinator(monkeypatch, states={})

    assert coordinator.entity_registry is entity_registry
    assert coordinator.area_registry is area_registry
    assert coordinator.config_entry.data["provider"] == "OpenAI"


def test_legacy_coordinator_signature_remains_supported(monkeypatch):
    def legacy_init(self, hass, logger, *, name, update_interval=None):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None
        self.last_update_success = True

    monkeypatch.setattr(coordinator_module.DataUpdateCoordinator, "__init__", legacy_init)

    coordinator, _, _ = make_coordinator(monkeypatch, states={})

    assert coordinator.name == "ai_automation_suggester"


def test_area_exclusion_uses_area_name_from_registry(monkeypatch):
    states = {"person.alex": make_state("person.alex", "home")}
    coordinator, entity_registry, area_registry = make_coordinator(
        monkeypatch,
        states=states,
        options={"excluded_areas": "Bedroom"},
    )
    entity_registry.entries["person.alex"] = SimpleNamespace(area_id="bedroom", device_id=None)
    area_registry.entries["bedroom"] = SimpleNamespace(name="Bedroom")

    assert coordinator._is_entity_excluded("person.alex") is True
    assert coordinator._collect_entities() == {}


def test_prompt_records_only_entities_that_fit_budget(monkeypatch):
    states = {
        "sensor.one": make_state("sensor.one", "1", {"friendly_name": "One", "detail": "x" * 400}),
        ("sensor.two_with_a_deliberately_long_entity_identifier_that_does_not_fit_the_remaining_budget"): make_state(
            "sensor.two_with_a_deliberately_long_entity_identifier_that_does_not_fit_the_remaining_budget",
            "2",
            {"friendly_name": "Two", "detail": "y" * 400},
        ),
    }
    coordinator, _, _ = make_coordinator(
        monkeypatch,
        states=states,
        options={"max_input_tokens": 130},
    )
    coordinator.SYSTEM_PROMPT = "Suggest useful Home Assistant automations."
    monkeypatch.setattr(coordinator_module, "STRUCTURED_OUTPUT_INSTRUCTIONS", "Return structured suggestions.")
    coordinator.entity_limit = 2
    monkeypatch.setattr(coordinator_module.random, "sample", lambda values, count: list(values)[:count])

    result = asyncio.run(coordinator._build_prompt(coordinator._collect_entities()))

    assert 1 <= len(result.entity_ids) < 2
    assert all(entity_id in result.prompt for entity_id in result.entity_ids)
    assert any("input budget included" in warning for warning in result.warnings)


def test_only_sent_entities_are_marked_processed(monkeypatch):
    states = {
        "sensor.one": make_state("sensor.one", "1"),
        "sensor.two": make_state("sensor.two", "2"),
    }
    coordinator, _, _ = make_coordinator(monkeypatch, states=states)
    current = coordinator._collect_entities()

    coordinator._mark_entities_processed(current, ("sensor.one",))

    assert set(coordinator.previous_entities) == {"sensor.one"}


def test_generated_reference_validation_checks_runtime(monkeypatch):
    states = {"binary_sensor.motion": make_state("binary_sensor.motion", "off")}
    coordinator, _, _ = make_coordinator(monkeypatch, states=states)
    suggestions = [
        {
            "entities_used": ["binary_sensor.motion", "light.missing"],
            "automation_ids_used": ["automation.missing"],
            "script_ids_used": ["script.missing"],
            "services_used": ["light.turn_on", "notify.unknown"],
            "warnings": [],
        }
    ]

    coordinator._validate_generated_suggestions(suggestions)

    warnings = suggestions[0]["warnings"]
    assert not any("binary_sensor.motion" in warning for warning in warnings)
    assert not any("light.turn_on" in warning for warning in warnings)
    assert any("light.missing" in warning for warning in warnings)
    assert any("automation.missing" in warning for warning in warnings)
    assert any("script.missing" in warning for warning in warnings)
    assert any("notify.unknown" in warning for warning in warnings)


def test_generate_refreshes_immediately_and_restores_request_settings(monkeypatch):
    coordinator, _, _ = make_coordinator(monkeypatch, states={})
    observed = {}

    async def immediate_refresh():
        observed["scan_all"] = coordinator.scan_all
        observed["domains"] = coordinator.selected_domains
        observed["entity_limit"] = coordinator.entity_limit
        coordinator.data["request_succeeded"] = True

    async def debounced_refresh():
        raise AssertionError("Explicit generation must not use the debounced refresh path")

    coordinator.async_refresh = immediate_refresh
    coordinator.async_request_refresh = debounced_refresh

    asyncio.run(
        coordinator.async_generate_suggestions(
            all_entities=True,
            domains=["person", "light"],
            entity_limit=42,
        )
    )

    assert observed == {"scan_all": True, "domains": ["person", "light"], "entity_limit": 42}
    assert coordinator.scan_all is False
    assert coordinator.selected_domains == []
    assert coordinator.entity_limit == 200


def test_generate_propagates_provider_failure(monkeypatch):
    coordinator, _, _ = make_coordinator(monkeypatch, states={})

    async def failed_refresh():
        coordinator.data.update(
            {
                "request_succeeded": False,
                "last_error": "OpenAI error 429: rate limited",
            }
        )

    coordinator.async_refresh = failed_refresh

    with pytest.raises(ValueError, match="rate limited"):
        asyncio.run(coordinator.async_generate_suggestions(all_entities=True))

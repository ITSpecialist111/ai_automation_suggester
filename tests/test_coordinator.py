"""Coordinator regression tests."""

from __future__ import annotations

import asyncio
import logging
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


def test_minimax_uses_provider_specific_configuration(monkeypatch):
    coordinator, _, _ = make_coordinator(
        monkeypatch,
        states={},
        options={
            "provider": "MiniMax",
            "minimax_api_key": "secret",
            "minimax_model": "MiniMax-M2.7",
            "minimax_base_url": "https://api.minimaxi.com/v1",
            "minimax_temperature": 0.4,
        },
    )
    request = {}

    async def post_json(endpoint, *, headers=None, body=None, provider_label=None):
        request.update(endpoint=endpoint, headers=headers, body=body, provider_label=provider_label)
        return {"choices": [{"message": {"content": "ok"}}]}

    coordinator._post_json = post_json

    result = asyncio.run(coordinator._minimax("hello"))

    assert result == "ok"
    assert request["endpoint"] == "https://api.minimaxi.com/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer secret"
    assert request["body"]["model"] == "MiniMax-M2.7"
    assert request["body"]["temperature"] == 0.4
    assert request["provider_label"] == "MiniMax"


@pytest.mark.parametrize("disable_think", [True, False, None])
def test_ollama_disable_think_uses_native_parameter(monkeypatch, disable_think):
    options = {
        "provider": "Ollama",
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "gemma4:12b",
    }
    if disable_think is not None:
        options["ollama_disable_think"] = disable_think
    coordinator, _, _ = make_coordinator(monkeypatch, states={}, options=options)
    request = {}

    async def post_json(endpoint, *, headers=None, body=None, provider_label=None):
        request.update(endpoint=endpoint, body=body)
        return {"message": {"content": "ok"}, "done_reason": "stop"}

    coordinator._post_json = post_json

    assert asyncio.run(coordinator._ollama("hello")) == "ok"
    assert request["endpoint"] == "http://localhost:11434/api/chat"
    assert request["body"]["model"] == "gemma4:12b"
    if disable_think:
        assert request["body"]["think"] is False
        assert request["body"]["messages"][0]["content"] == "/no_think"
    else:
        assert "think" not in request["body"]
        assert request["body"]["messages"] == [{"role": "user", "content": "hello"}]


@pytest.mark.parametrize("reasoning_field", ["reasoning_content", "reasoning"])
@pytest.mark.parametrize("content", [None, ""])
def test_chat_response_uses_reasoning_fallback(monkeypatch, reasoning_field, content):
    coordinator, _, _ = make_coordinator(monkeypatch, states={})
    answer = "```yaml\nalias: Reasoning answer\ntriggers: []\nactions: []\n```"
    response = {"choices": [{"message": {"content": content, reasoning_field: answer}, "finish_reason": "stop"}]}

    assert coordinator._extract_chat_content(response, "OpenRouter") == answer
    assert coordinator._last_response_metadata["finish_reason"] == "stop"


def test_chat_response_prefers_final_answer_over_reasoning(monkeypatch):
    coordinator, _, _ = make_coordinator(monkeypatch, states={})
    response = {"choices": [{"message": {"content": "Final answer", "reasoning_content": "Draft reasoning"}}]}

    assert coordinator._extract_chat_content(response, "OpenRouter") == "Final answer"


def test_empty_chat_response_is_an_explicit_error(monkeypatch):
    coordinator, _, _ = make_coordinator(monkeypatch, states={})

    with pytest.raises(ValueError, match="empty content"):
        coordinator._extract_chat_content({"choices": [{"message": {"content": ""}}]}, "OpenRouter")


@pytest.mark.parametrize("provider,key,model", [
    ("Google", "google_model", "gemini-2.5-flash"),
    ("Groq", "groq_model", "llama-3.3-70b-versatile"),
])
def test_configured_models_are_not_replaced_by_new_defaults(monkeypatch, provider, key, model):
    coordinator, _, _ = make_coordinator(monkeypatch, states={}, options={"provider": provider, key: model})

    assert coordinator._current_model() == model


def test_automation_and_script_yaml_context_preserves_unicode(monkeypatch, tmp_path):
    (tmp_path / "automations.yaml").write_text(
        "- id: '1780905604476'\n  alias: Pomocn\u00edk klima vyp\n  triggers: []\n  actions: []\n",
        encoding="utf-8",
    )
    (tmp_path / "scripts.yaml").write_text(
        "klima_vyp:\n  alias: Vypnout klimatizaci v kancel\u00e1\u0159i\n  sequence: []\n",
        encoding="utf-8",
    )
    coordinator, _, _ = make_coordinator(monkeypatch, states={})
    coordinator.hass.config = SimpleNamespace(language="cs", path=lambda: str(tmp_path))

    automations = asyncio.run(coordinator._read_automations_file_method(10))
    scripts = asyncio.run(coordinator._read_scripts_file_method(10))

    assert "alias: Pomocn\u00edk klima vyp" in automations[0]
    assert "alias: Vypnout klimatizaci v kancel\u00e1\u0159i" in scripts[0]
    assert "\\x" not in automations[0] + scripts[0]
    assert "\\u" not in automations[0] + scripts[0]


def make_google_coordinator(monkeypatch, response, **options):
    coordinator, _, _ = make_coordinator(
        monkeypatch,
        states={},
        options={"provider": "Google", "google_api_key": "secret", **options},
    )

    async def post_json(endpoint, *, headers=None, body=None, provider_label=None):
        return response

    coordinator._post_json = post_json
    return coordinator


def test_google_max_tokens_without_text_explains_output_limit(monkeypatch):
    coordinator = make_google_coordinator(
        monkeypatch,
        {
            "candidates": [{"content": {"role": "model"}, "finishReason": "MAX_TOKENS"}],
            "usageMetadata": {"promptTokenCount": 900, "thoughtsTokenCount": 497},
        },
    )

    with pytest.raises(ValueError, match=r"Max Output Tokens limit \(500\)") as error:
        asyncio.run(coordinator._google("hello"))

    assert "497 thinking tokens" in str(error.value)
    assert coordinator._last_response_metadata["finish_reason"] == "MAX_TOKENS"


def test_google_partial_text_at_limit_is_returned_for_parsing(monkeypatch):
    coordinator = make_google_coordinator(
        monkeypatch,
        {"candidates": [{"content": {"parts": [{"text": '{"suggestions": ['}]}, "finishReason": "MAX_TOKENS"}]},
    )

    assert asyncio.run(coordinator._google("hello")) == '{"suggestions": ['
    assert coordinator._last_response_metadata["finish_reason"] == "MAX_TOKENS"


def test_google_thought_parts_are_not_part_of_the_answer(monkeypatch):
    coordinator = make_google_coordinator(
        monkeypatch,
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Considering the hallway lights", "thought": True},
                            {"text": '{"suggestions": []}', "thoughtSignature": "abc"},
                        ]
                    },
                    "finishReason": "STOP",
                }
            ]
        },
    )

    assert asyncio.run(coordinator._google("hello")) == '{"suggestions": []}'


@pytest.mark.parametrize(
    "response,message",
    [
        ({"promptFeedback": {"blockReason": "PROHIBITED_CONTENT"}}, "blockReason: PROHIBITED_CONTENT"),
        ({"candidates": [{"finishReason": "SAFETY"}]}, "finishReason: SAFETY"),
    ],
)
def test_google_empty_responses_report_the_provider_reason(monkeypatch, response, message):
    coordinator = make_google_coordinator(monkeypatch, response)

    with pytest.raises(ValueError, match=message):
        asyncio.run(coordinator._google("hello"))


def test_chat_response_at_output_limit_without_answer_is_explicit(monkeypatch):
    coordinator, _, _ = make_coordinator(monkeypatch, states={}, options={"max_output_tokens": 800})
    response = {
        "choices": [
            {
                "message": {"content": "", "reasoning_content": "Let me think about the hallway"},
                "finish_reason": "length",
            }
        ]
    }

    with pytest.raises(ValueError, match=r"OpenRouter stopped at the Max Output Tokens limit \(800\)"):
        coordinator._extract_chat_content(response, "OpenRouter")


def test_anthropic_output_limit_without_text_is_explicit(monkeypatch):
    coordinator, _, _ = make_coordinator(
        monkeypatch,
        states={},
        options={"provider": "Anthropic", "anthropic_api_key": "secret"},
    )

    async def post_json(endpoint, *, headers=None, body=None, provider_label=None):
        return {"content": [], "stop_reason": "max_tokens"}

    coordinator._post_json = post_json

    with pytest.raises(ValueError, match="Anthropic stopped at the Max Output Tokens limit"):
        asyncio.run(coordinator._anthropic("hello"))


def test_ollama_output_limit_without_text_is_explicit(monkeypatch):
    coordinator, _, _ = make_coordinator(
        monkeypatch,
        states={},
        options={"provider": "Ollama", "ollama_base_url": "http://localhost:11434", "ollama_model": "qwen3"},
    )

    async def post_json(endpoint, *, headers=None, body=None, provider_label=None):
        return {"message": {"role": "assistant", "content": ""}, "done_reason": "length"}

    coordinator._post_json = post_json

    with pytest.raises(ValueError, match="Ollama stopped at the Max Output Tokens limit"):
        asyncio.run(coordinator._ollama("hello"))


def test_truncated_google_generation_logs_raw_response_and_explains_limit(monkeypatch, caplog):
    states = {"light.hall": make_state("light.hall", "off", {"friendly_name": "Hall"})}
    coordinator, _, _ = make_coordinator(
        monkeypatch,
        states=states,
        options={"provider": "Google", "google_api_key": "secret", "max_input_tokens": 4000},
    )
    raw = '{"suggestions": [{"title": "Hall light", "description": "Token: abc123\\nLine two", "yaml": "alias: Ha'

    async def post_json(endpoint, *, headers=None, body=None, provider_label=None):
        return {"candidates": [{"content": {"parts": [{"text": raw}]}, "finishReason": "MAX_TOKENS"}]}

    notifications = []
    coordinator._post_json = post_json
    coordinator.scan_all = True
    monkeypatch.setattr(
        coordinator_module.persistent_notification,
        "async_create",
        lambda hass, **kwargs: notifications.append(kwargs),
        raising=False,
    )
    caplog.set_level(logging.DEBUG, logger=coordinator_module.__name__)

    data = asyncio.run(coordinator._async_update_data())

    assert data["request_succeeded"] is True
    assert "The provider reported a length finish reason; the suggestion may be truncated." in data["warnings"]
    assert "may have been cut off" in notifications[0]["message"]
    assert "Raw Google response for model gemini-3.5-flash" in caplog.text
    assert "'finish_reason': 'MAX_TOKENS'" in caplog.text
    assert '"title": "Hall light"' in caplog.text
    assert "abc123" not in caplog.text


def test_raw_response_log_is_skipped_without_debug_logging(monkeypatch, caplog):
    coordinator, _, _ = make_coordinator(monkeypatch, states={})
    caplog.set_level(logging.INFO, logger=coordinator_module.__name__)

    coordinator._log_provider_response("OpenAI", "gpt-5.4-mini", "response text")

    assert "response text" not in caplog.text

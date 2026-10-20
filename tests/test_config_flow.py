"""Configuration schema regression tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
import voluptuous as vol

from custom_components.ai_automation_suggester.config_flow import (
    AIAutomationConfigFlow,
    AIAutomationOptionsFlowHandler,
)
from custom_components.ai_automation_suggester.const import CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT


@pytest.fixture(params=["setup", "options"])
def timeout_schema(request):
    if request.param == "setup":
        schema = AIAutomationConfigFlow()._add_token_fields({})
    else:
        entry = SimpleNamespace(data={"provider": "Ollama"}, options={})
        flow = AIAutomationOptionsFlowHandler(entry)
        form = asyncio.run(flow.async_step_init())
        schema = form["data_schema"].schema
    return vol.Schema({key: validator for key, validator in schema.items() if key.schema == CONF_REQUEST_TIMEOUT})


@pytest.mark.parametrize("seconds", [10, 1800, 1801, 7200, 86400])
def test_timeout_accepts_long_local_requests(timeout_schema, seconds):
    assert timeout_schema({CONF_REQUEST_TIMEOUT: seconds})[CONF_REQUEST_TIMEOUT] == seconds


def test_timeout_default_is_unchanged(timeout_schema):
    assert timeout_schema({})[CONF_REQUEST_TIMEOUT] == DEFAULT_REQUEST_TIMEOUT == 900


@pytest.mark.parametrize("seconds", [-1, 0, 9])
def test_timeout_still_rejects_values_below_minimum(timeout_schema, seconds):
    with pytest.raises(vol.Invalid):
        timeout_schema({CONF_REQUEST_TIMEOUT: seconds})


def test_minimax_setup_defaults_to_flash_and_accepts_custom_models():
    flow = AIAutomationConfigFlow()
    form = asyncio.run(flow.async_step_user({"provider": "MiniMax"}))
    schema = form["data_schema"]

    assert schema({"minimax_api_key": "test-key"})["minimax_model"] == "MiniMax-M3.1-Flash"
    for model in ("MiniMax-M3", "MiniMax-M2.7", "custom-deployment"):
        assert schema({"minimax_api_key": "test-key", "minimax_model": model})["minimax_model"] == model


@pytest.mark.parametrize("storage", ["data", "options"])
@pytest.mark.parametrize("model", [None, "MiniMax-M3.1-Flash", "MiniMax-M3", "MiniMax-M2.7", "custom-deployment"])
def test_minimax_options_preserve_saved_models(storage, model):
    entry = SimpleNamespace(data={"provider": "MiniMax", "minimax_api_key": "test-key"}, options={})
    if model is not None:
        if storage == "options":
            entry.data["minimax_model"] = "MiniMax-M3.1-Flash"
        getattr(entry, storage)["minimax_model"] = model
    flow = AIAutomationOptionsFlowHandler(entry)
    form = asyncio.run(flow.async_step_init())
    submitted = form["data_schema"]({})
    result = asyncio.run(flow.async_step_init(submitted))

    assert result["data"]["minimax_model"] == (model or "MiniMax-M3.1-Flash")

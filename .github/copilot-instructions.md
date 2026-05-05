# GitHub Copilot Instructions

This repository contains **AI Automation Suggester**, a [Home Assistant](https://www.home-assistant.io/) custom integration distributed via [HACS](https://hacs.xyz/). It connects Home Assistant to large language model (LLM) providers and returns actionable YAML automation suggestions tailored to the user's smart-home setup.

---

## Repository layout

```
custom_components/ai_automation_suggester/   # Integration source
    __init__.py          # Entry-point: setup, teardown, service registration
    api.py               # HTTP view registration for the REST API
    config_flow.py       # UI config-flow and options-flow (HA config entries)
    const.py             # All constants (CONF_*, DEFAULT_*, ENDPOINT_*, SERVICE_*, …)
    coordinator.py       # DataUpdateCoordinator – orchestrates HA data collection and LLM calls
    endpoint_utils.py    # URL builders and HTTP-header helpers (bearer auth, Ollama, OpenAI)
    language_utils.py    # Language-detection helpers for multilingual suggestion output
    manifest.json        # HACS / hassfest metadata (domain, version, requirements)
    model_catalog.py     # Per-model capability flags (JSON schema support, Responses API, …)
    sensor.py            # Sensor platform (suggestions, status, token counters, …)
    services.yaml        # HA service definitions exposed to the UI and automations
    store.py             # Persistent suggestion history (JSON store via HA storage)
    strings.json         # UI string keys (translated in translations/<lang>.json)
    suggestions.py       # Response parsing (JSON / fenced YAML), formatting, validation
    automations/         # Example automation YAML files bundled with the integration
    translations/        # Locale files (en.json, etc.)
    www/                 # Lovelace card assets
custom_components/dashboard/ # Dashboard card source
tests/                       # pytest suite (no HA instance needed – pure-Python helpers)
docs/                        # Release notes and planning docs
.github/
    workflows/
        tests.yaml       # CI: ruff lint + pytest
        hassfest.yaml    # CI: Home Assistant hassfest validation
        hacs.yaml        # CI: HACS validation
        validate.yaml    # CI: extended HACS checks
    ISSUE_TEMPLATE/      # Bug report / feature request templates
    pull_request_template.md
```

---

## Key conventions

### Python style
- **Minimum supported Python: 3.9** (ruff `target-version = "py39"` in `pyproject.toml`). CI runs under Python 3.12; avoid features exclusive to 3.10+.
- **Line length: 120** characters (`ruff` enforces this).
- Ruff rules enabled: `E`, `F`, `I` (isort), `UP`, `B`. Ignored: `E501`, `UP007`, `UP045`.
- Run `ruff check custom_components/ai_automation_suggester/model_catalog.py custom_components/ai_automation_suggester/suggestions.py tests` to lint (matches CI exactly).
- Use `from __future__ import annotations` at the top of every module.
- Prefer `logging.getLogger(__name__)` for module-level loggers.

### Constants
- **All constants live in `const.py`**. Provider config keys follow `CONF_<PROVIDER>_<SETTING>` (e.g. `CONF_OPENAI_API_KEY`). Default values follow `DEFAULT_<SETTING>`. Sensor keys follow `SENSOR_KEY_<NAME>`.
- When adding a new provider, add all its `CONF_*` constants, its default model to `DEFAULT_MODELS`, and its endpoint to `ENDPOINT_*`.

### Home Assistant patterns
- Config entries use `CONFIG_VERSION = 3`; increment and add migration logic in `async_migrate_entry` if the stored data shape changes.
- Async-first: all I/O and HA interactions must be `async def` and use `await`.
- Use `async_get_clientsession(hass)` for HTTP calls rather than creating raw `aiohttp.ClientSession` objects.
- Register services in `__init__.py`; define their schemas in `services.yaml`.
- Sensor entities are registered in `sensor.py` via the `DataUpdateCoordinator` in `coordinator.py`.

### Adding a new LLM provider
1. Add `CONF_<PROVIDER>_*` keys and a default model entry in `const.py`.
2. Add an endpoint constant `ENDPOINT_<PROVIDER>`.
3. Add a `validate_<provider>` method to `ProviderValidator` in `config_flow.py`.
4. Add provider-specific config steps to the config flow and options flow.
5. Add the API call logic in the relevant section of `coordinator.py` (`_call_<provider>`-style helper).
6. Add model capability entries to `model_catalog.py` if the provider's models have special behaviour (e.g., no temperature support, JSON schema support).

### Suggestion parsing
- AI responses are parsed in `suggestions.py`. The integration prefers structured JSON (`STRUCTURED_OUTPUT_INSTRUCTIONS`) and falls back to fenced YAML (triple-backtick `yaml` or `yml` blocks).
- `parse_suggestion_response` returns a list of suggestion dicts. Each dict must include `title`, `description`, and `yaml`.
- Validate YAML snippets with `pyyaml` before surfacing them.

### Persistent storage
- `store.py` wraps Home Assistant's JSON storage helper. Suggestion history is limited by `CONF_HISTORY_RETENTION` (default 25).

---

## Testing

```bash
# Install test dependencies
pip install pytest pyyaml ruff pytest-homeassistant-custom-component

# Lint (matches CI)
ruff check custom_components/ai_automation_suggester/model_catalog.py \
           custom_components/ai_automation_suggester/suggestions.py \
           tests

# Run tests
pytest
```

The `tests/` directory contains pure-Python unit tests that do **not** require a running Home Assistant instance. Tests for new logic belong here. Use `pytest` fixtures and standard `unittest.mock` / `pytest.monkeypatch` patterns consistent with the existing test files (`test_suggestions.py`, `test_model_catalog.py`, `test_endpoint_utils.py`, `test_language_utils.py`).

---

## CI checks

All of the following must pass before merging:

| Workflow | What it checks |
|---|---|
| `tests.yaml` | ruff lint + pytest |
| `hassfest.yaml` | HA integration manifest and platform validity |
| `hacs.yaml` | HACS repository structure |
| `validate.yaml` | Extended HACS validation |

---

## PR checklist (from `.github/pull_request_template.md`)

- [ ] Run `pytest` locally.
- [ ] Run HACS validation.
- [ ] Run hassfest validation.
- Note the minimum HA version affected, and which providers and model IDs were tested.

---

## What Copilot should know about the domain

- **Home Assistant automations** are YAML documents. The integration never creates or modifies automations automatically – it only *suggests* them for user review.
- Entity IDs follow the `domain.entity_id` pattern (e.g. `light.living_room`). Suggestions must only reference entity IDs that exist in the user's HA instance (they are injected into the prompt by `coordinator.py`).
- The integration surfaces suggestions via HA **persistent notifications**, **sensor attributes**, and a **stored history**. Users can mark suggestions accepted, declined, or dismissed via HA services.
- Supported providers (as of v1.5.6): OpenAI, Azure OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, Custom OpenAI, Mistral AI, Perplexity AI, OpenRouter, Generic OpenAI.

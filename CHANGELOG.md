# Changelog

## 1.5.9 - 2026-07-04

### Added

- Added **Requesty** as an OpenAI-compatible LLM provider, giving access to 300+ models through the Requesty router (`https://router.requesty.ai`). Configure with a Requesty API key and pick any supported model (defaults to `openai/gpt-4o-mini`). Thanks @Thibaultjaigu (PR #176).
- Added **script reading support** so `script.*` YAML from `scripts.yaml` is included in the suggestion prompt alongside automations, letting the AI reason about scripts you already have when proposing new automations. Available as the `script_read_yaml` service field and mirrored across all 11 locales. Thanks @RmG152 (PR #167).
- Added **Polish (`pl`) translations** covering the full config flow, options flow, and service descriptions. Thanks @blka (PR #164).

## 1.5.8 - 2026-07-04

### Fixed

- Fixed a Home Assistant freeze/crash after multiple options-flow saves. `async_reload_entry` bypassed the core reload path, so `entry.async_on_unload` callbacks never fired and every save stacked an additional update listener until the event loop locked up. It now delegates to `hass.config_entries.async_reload` (issue #175, thanks @mjg42).
- Stopped the recorder warning `State attributes for sensor.ai_automation_suggester_*_ai_automation_suggestions_* exceed maximum size of 16384 bytes` by marking the large suggestion payload attributes (`suggestions`, `yaml_block`, `description`, `entities_processed`, `suggestion`) as unrecorded. Attributes remain visible in the live state, the dashboard card, and the HTTP API — they are just no longer persisted to the history database (issue #172).
- Added a `reasoning_content` fallback to the OpenAI-compatible response parser so reasoning models (Qwen3, DeepSeek R1, and similar) that emit their answer in `reasoning_content` when `content` is empty are no longer silently discarded (issue #127, thanks @HexRebuilt for the diagnosis).

## 1.5.7 - 2026-06-04

### Fixed

- Fixed integration entering `setup_error` on Home Assistant 2025.x+ because `async_add_entities(..., True)` triggered a full LLM inference during sensor platform setup and exceeded the setup timeout, especially with local/slow providers (issue #166).
- Fixed Perplexity setup validation always failing with `max_tokens must be at least 16 for sonar` by raising the validation probe's `max_tokens` from 1 to 16 (issue #171).

## 1.5.6 - 2026-05-03

### Fixed

- Fixed Gemini 2.5 Flash requests failing with `additionalProperties` JSON schema validation errors by sending a Google-compatible response schema.

## 1.5.5 - 2026-05-03

### Added

- Added Czech translations from the community contribution, updated for the current setup/options schema.
- Added prompt localization so generated suggestion titles, descriptions, and warnings follow the configured Home Assistant language when it is not English.

### Fixed

- Completed missing Italian service and option translation keys, including newer exclusion, history, timeout, OpenAI reasoning, and Ollama/Open WebUI fields.
- Fixed the reported spacing and capitalization typos in the contributed Czech wording.

## 1.5.4 - 2026-05-03

### Added

- Added an optional Ollama/Open WebUI API key field for authenticated Open WebUI Ollama proxy endpoints.

### Fixed

- Sent bearer authorization headers during Ollama setup validation and suggestion generation when an Ollama/Open WebUI API key is configured.

## 1.5.3 - 2026-05-03

### Added

- Added an optional Ollama/Open WebUI base URL field so users can configure native Ollama, proxied Ollama, and Open WebUI-style deployments without relying only on host and port fields.
- Added endpoint normalization tests for OpenAI-compatible and Ollama-compatible provider URLs.
- Added a feature-request plan for the remaining larger GitHub issues.

### Changed

- Provider setup validation now uses the configured request timeout and model-listing endpoints where possible instead of tiny generation calls for Anthropic and Gemini.
- Custom OpenAI-compatible setup validation now accepts base URLs, `/v1` URLs, exact `/chat/completions` URLs, and common Open WebUI model-listing paths.

### Fixed

- Improved Ollama validation and requests for Open WebUI proxy paths such as `/ollama/api/tags` and `/ollama/api/chat`.
- Improved OpenRouter setup validation by applying the configured timeout to avoid hanging validation requests.

## 1.5.2 - 2026-05-03

### Changed

- Reworded parser-repair and truncated-response warnings in persistent notifications so they are user-facing instead of implementation-oriented.

### Fixed

- Normalized malformed-response parser regression test formatting.

## 1.5.1 - 2026-05-03

### Fixed

- Fixed persistent notifications showing raw malformed JSON-like provider output when models returned unescaped multiline YAML inside structured responses.
- Added best-effort parsing for malformed structured suggestions so title, description, YAML, entities, confidence, and warnings can still be recovered.
- Replaced raw JSON-like fallback notification bodies with a short parse-failure message.

## 1.5.0 - 2026-05-03

### Added

- Added model capability metadata for current OpenAI, Azure OpenAI, Anthropic, Gemini, Groq, Mistral, Perplexity, OpenRouter, and local/OpenAI-compatible models.
- Added OpenAI Responses API routing for GPT-5-style reasoning models and safer token parameter selection for newer OpenAI-compatible models.
- Added structured suggestion parsing with JSON-first parsing, fenced YAML fallback, YAML validation warnings, and truncation warnings.
- Added persistent suggestion history with review statuses and HTTP API endpoints for dashboard cards.
- Added services to clear suggestion history and update suggestion status.
- Added persistent custom prompt, exclusion filters, history retention, and request timeout options.
- Added pytest coverage for model catalog and suggestion parsing helpers.
- Added release notes, issue templates, PR template, and refreshed CI scaffolding.

### Changed

- Updated provider defaults away from stale model IDs, including Gemini 2.0 Flash, legacy Groq Llama 3 IDs, and legacy Mistral aliases.
- Bumped the integration version to `1.5.0`.
- Reworked the bundled Lovelace card to use the new stored suggestion API.

### Fixed

- Fixed config entry migration to update the config entry version through Home Assistant's update API.
- Fixed service-triggered generation so concurrent calls no longer mutate shared coordinator settings without isolation.

## 1.4.2 and earlier

- Earlier releases focused on the initial provider integrations, token budget options, diagnostics sensors, and manual suggestion generation service.
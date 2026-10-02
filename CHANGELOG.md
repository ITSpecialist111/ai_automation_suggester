# Changelog

## 1.6.2 - 2026-10-02

### Fixed

- GPT-6 and later OpenAI models, such as `gpt-6.1-sol` and `gpt-6-luna`, failed with `OpenAI error 400: Unsupported parameter: 'max_tokens' is not supported with this model`. Model detection only recognized `gpt-5`, `o3`, and `o4` names, so newer models fell back to Chat Completions with `max_tokens` and a temperature. GPT-5-or-later and every `o`-series model are now matched by version number. On the OpenAI provider they use the Responses API with `max_output_tokens`, as GPT-5 models do. On Azure OpenAI, Custom OpenAI, and Generic OpenAI they use `max_completion_tokens` without a temperature (issue #192).
- Unrecognized model names on the direct OpenAI provider now send `max_completion_tokens` instead of the deprecated `max_tokens`. Unrecognized models on other providers are unchanged.
- Removed `aiohttp` and `pyyaml` from the manifest requirements. Home Assistant already provides both, and hassfest now rejects custom integrations that list core dependencies.

### Added

- Added regression tests for GPT-6-and-later and `o`-series detection, OpenAI request bodies, and unknown-model token parameters.

## 1.6.1 - 2026-09-26

### Fixed

- Fixed non-ASCII names in `automations.yaml` and `scripts.yaml` prompt context being sent as YAML escapes, for example `"Pomocn\xEDk klima vyp"`. Models could copy those escapes into their JSON response, making it invalid JSON and triggering the best-effort parser and its "formatting repair" warning (issue #172).
- JSON suggestion responses containing escapes that JSON does not allow, such as `\xED` or `\'`, or literal newlines inside strings, are now decoded without the best-effort repair path. Escaped single quotes become quotes, so a trigger such as `to: 'off'` is no longer corrupted to `to: \'off\'`. Valid JSON is decoded exactly as before.
- Truncation is now detected from each provider's own stop reason, including Gemini `MAX_TOKENS`, Anthropic `max_tokens`, Ollama `length`, and OpenAI Responses `max_output_tokens`. Previously only the OpenAI-compatible `length` finish reason produced the truncation warning (issue #172).
- When truncated structured output cannot be parsed, the suggestion now explains that the provider stopped at the Max Output Tokens limit instead of reporting a generic parse failure.
- When a provider stops at the output limit without returning a final answer, generation now fails with an error naming the configured Max Output Tokens value. Unfinished OpenAI-compatible reasoning text at the limit is no longer presented as a successful suggestion. Completed `reasoning_content` answers still use the fallback from issue #127.
- Gemini responses exclude thought-summary parts from the answer, report `blockReason` for blocked prompts, and report `finishReason` when no text is returned. Thinking-token usage is included when the output limit is reached.

### Added

- `openrouter/free`, OpenRouter's Free Models Router, now receives the structured-output schema, so OpenRouter routes it only to free models that support structured outputs. Thanks @JamieC03 (PR #190).
- Added debug logging of the prompt size and the raw provider response, with its finish reason and token usage. Credentials are redacted. Enable `custom_components.ai_automation_suggester: debug` to capture it for bug reports (issue #172).
- Added regression tests for provider stop reasons, tolerant JSON decoding, Unicode prompt context, Gemini response handling, output-limit errors, and debug logging.

### Changed

- Clarified that suggestion generation is on demand. The weekly-review and new-entity examples ship with the repository but must be imported and enabled as automations. The integration does not install automations, run inference at startup, or poll. Added an optional after-startup automation and scheduling troubleshooting (issue #177).
- Documented output-limit messages, `openrouter/free` behavior, and debug logging. Default token budgets, configured models, and suggestion history are unchanged.

## 1.6.0 - 2026-09-05

### Added

- Added MiniMax as a first-class provider with global/China API regions, configurable credentials and temperature, MiniMax-M3 as the default, and MiniMax-M2.7 catalog support. Thanks @octo-patch (PR #178).
- Added regression coverage for provider status, reasoning-response fallback, configured-model preservation, nested YAML fences, and setup/options timeout validation.

### Fixed

- Fixed the LiteLLM model sensor reporting `Unknown Model Key` and repeatedly logging warnings. Thanks @mjacobs (PR #186, issue #185).
- Ollama's existing Disable Think option now sends native `think: false` as well as the legacy `/no_think` prompt hint. Disabled/unset options leave the provider's native thinking behavior unchanged (issue #188).
- Removed complete Markdown YAML fences inside structured suggestion fields before YAML validation, preserving newlines and indentation. This addresses a reproducible wrapper-related case from the investigation of issue #172.

### Changed

- New Google configurations default to `gemini-3.5-flash` because Gemini 2.5 Flash is unavailable to new users (issue #184).
- New Groq configurations default to `openai/gpt-oss-120b`. Deprecated Llama IDs now warn with current replacements, and `qwen/qwen3.6-27b` is listed as a preview alternative (issue #187).
- Removed the 1800-second request timeout maximum from both setup and options. The default remains 900 seconds and the minimum remains 10 seconds (issue #182).
- Documented model migration, reasoning-model token budgets, startup status, and explicit generation troubleshooting. Existing configured models, token budgets, and suggestion history are preserved.

## 1.5.10 - 2026-07-11

### Fixed

- Fixed excluded-area filtering and device/area prompt context by initializing Home Assistant registries when the coordinator is created. The previous entity lifecycle hook was never called for a coordinator, so area exclusions could be ignored.
- Fixed entity sampling metadata so `entities_processed` contains exactly the entity context sent to the provider. New entities omitted by the entity limit or input budget now remain eligible for a later run instead of being marked as processed.
- Fixed rapid service calls potentially being delayed by the coordinator debouncer until after their request-specific filters and prompt settings had been restored.
- Replaced arbitrary mid-text prompt slicing with whole-block budgeting. Complete entity, automation, and script blocks are retained, with explicit warnings when context is compacted or deferred.
- Failed or empty provider requests now surface as service failures instead of appearing successful, and provider diagnostics redact credentials while preserving useful household context.
- Prevented oversized provider errors from exceeding Home Assistant's 255-character sensor state limit while retaining the full sanitized message as an attribute.
- Fixed the provider status sensor reporting `connected` before the first successful request.
- Serialized suggestion-store writes so concurrent generation, review actions, and history clearing cannot overwrite each other.
- Restored Home Assistant's coordinator shutdown cleanup instead of overriding it with a no-op.

### Added

- Added server-side validation warnings for entity, automation, script, and service references found in generated YAML.
- Added server-owned suggestion IDs and review statuses, plus confidence-range validation, so model output cannot control workflow metadata.
- Added coordinator, prompt-budget, area-exclusion, credential-redaction, output-validation, and storage-concurrency regression tests.
- Expanded Ruff enforcement to the full repository and removed wildcard imports from production modules.
- Made the lightweight test suite cross-platform and reproducible from `requirements.txt`.

### Privacy

- Personal household context remains intentionally available to the selected model. This release does not remove names, areas, states, attributes, or other useful smart-home details; it only prevents authentication credentials from being copied into diagnostics.

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
# AI Automation Suggester Upgrade Plan

Date: 2026-05-03
Repository reviewed: https://github.com/ITSpecialist111/ai_automation_suggester

## Scope Reviewed

- Local integration source under `custom_components/ai_automation_suggester`.
- Repository metadata: `manifest.json`, `hacs.json`, `requirements.txt`, README, example automations, translations, workflows.
- GitHub backlog: 100 issues through #153 and 25 pull requests through #155.
- Active backlog at review time: 27 open issues and 2 open pull requests.

## Current State

The project is a Home Assistant custom integration that generates automation suggestions from entity, device, area, and automation context. It currently exposes one sensor platform, a `generate_suggestions` service, persistent notifications, configuration and options flows, example automations, translation files, and a Lovelace card file.

The integration supports many providers directly in `coordinator.py`: OpenAI, Azure OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, Custom OpenAI, Mistral, Perplexity, OpenRouter, and Generic OpenAI. This gives the project broad reach, but it also concentrates provider-specific request building, validation, response parsing, timeout behavior, token handling, and error handling in one large file.

There are no test files in the repository. CI currently validates HACS and hassfest only. This means most regressions reported in issues are likely found by users after release rather than by automated checks.

The custom Lovelace card currently calls `/api/ai_automation_suggester/suggestions` and `/api/ai_automation_suggester/{action}/{suggestionId}`, but no matching backend API views were found in the local integration. That card should either be backed by real storage/API endpoints or removed/replaced with dashboard snippets that use supported sensor attributes.

## Model Catalog And API Compatibility Research

Research date: 2026-05-03. Sources checked: official OpenAI model/API docs, Azure OpenAI model availability docs, Anthropic Claude model docs, Google Gemini API docs, Mistral model/API docs, Groq model docs, Perplexity model docs, and OpenRouter model/API metadata.

### Key Findings

- The user's examples are real current model families, but the exact provider IDs matter. OpenAI documents `gpt-5.5` as the current flagship model and Azure OpenAI also lists `gpt-5.5` with model version `2026-04-24`. Anthropic documents `claude-opus-4-7` and `claude-sonnet-4-6`; the phrase "Opus 47" should be treated as shorthand for the API ID `claude-opus-4-7`.
- The current static defaults are already drifting. The integration defaults Google to `gemini-2.0-flash`, while current Gemini docs mark Gemini 2.0 Flash and Flash-Lite as deprecated and list Gemini 2.5 stable models plus Gemini 3/3.1 preview models.
- A static `DEFAULT_MODELS` dictionary is not enough. Each provider should have a catalog refresh path, a stable fallback, and a user override. Provider modules should store model metadata such as context window, max output, endpoint family, structured-output support, reasoning/thinking support, preview/deprecated status, and unsupported parameters.
- Model compatibility is now as much about request shape as model name. Newer reasoning models may reject or ignore parameters that older chat models accepted, and several providers distinguish chat completions, responses, messages, or generate-content APIs.
- Structured output support is now broad enough to become the primary parsing strategy, but it is not uniform. OpenAI, Gemini, Mistral, Perplexity, and OpenRouter all expose JSON or JSON Schema modes with provider-specific names and caveats. A Markdown fenced YAML fallback is still needed for older/local models.

### Current Model Families To Support

| Provider | Current model families to plan for | Notes for this integration |
| --- | --- | --- |
| OpenAI | `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5.3-*`, `gpt-5.2-*`, `gpt-5.1-*`, `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-4.1-*`, `gpt-4o*`, `o3`, `o4-mini`, `gpt-oss-*` | Prefer Responses API for GPT-5.5/5.4 reasoning models. Chat Completions can remain as compatibility fallback. Use `max_output_tokens` for Responses and model-aware `max_completion_tokens`/`max_tokens` for chat-compatible routes. Do not blindly send `temperature` to reasoning models. |
| Azure OpenAI | Same broad OpenAI families where region/quota permits, including `gpt-5.5`, `gpt-5.4-*`, `gpt-5.3-*`, `gpt-5.2-*`, `gpt-5.1-*`, `gpt-5-*`, `gpt-4.1-*`, `gpt-4o*`, `o-series`, and `gpt-oss-*` | Azure users deploy named deployments, not just model IDs. The config flow should distinguish deployment name from underlying model family and record API version, region, quota limitations, preview status, and whether the deployment supports Chat Completions or Responses. |
| Anthropic | `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001` / `claude-haiku-4-5`, plus legacy Claude 4.x and 3.7 models | Use the Models API when possible to query `max_input_tokens`, `max_tokens`, and capabilities. Opus 4.7 and later no longer accept manual extended thinking with `budget_tokens`; use adaptive thinking with effort. Thinking mode is not compatible with custom `temperature` or `top_k` changes. |
| Google Gemini | `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, `gemini-3.1-flash-lite-preview`, `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, and `*-latest` aliases where documented | Replace the default away from deprecated `gemini-2.0-flash`. Gemini 3 docs recommend leaving `temperature` at default 1.0. Use `thinking_config` only where supported. Use `response_mime_type` and `response_json_schema` for structured output. |
| Mistral | Mistral Large 3, Mistral Medium 3.5/3.1, Mistral Small 4, Ministral 3 14B/8B/3B, Devstral 2, Codestral, Magistral Medium 1.2 | Current code default `mistral-medium` should be reviewed against current aliases such as `mistral-small-latest` and published model IDs. Mistral supports `/v1/models`, `response_format` JSON object/schema modes, `reasoning_effort`, and model-dependent default temperature. |
| Groq | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `groq/compound`, `groq/compound-mini`, plus preview models like Llama 4 Scout | Current default `llama3-8b-8192` is stale. Use Groq's `https://api.groq.com/openai/v1/models` endpoint when authenticated. Distinguish production models from preview models. |
| Perplexity | `sonar`, `sonar-pro`, `sonar-reasoning-pro`, `sonar-deep-research` | Current default `sonar` remains recognizable, but the integration should expose search/reasoning/research model classes. Perplexity structured outputs use `response_format` JSON Schema and may have first-schema latency of 10-30 seconds, so timeout handling matters. |
| OpenRouter | Dynamic provider-prefixed IDs such as `openai/gpt-5.5`, `anthropic/claude-opus-4.7`, `google/gemini-2.5-flash`, `mistralai/mistral-large-2512`, router aliases such as `openrouter/auto`, and latest-family aliases such as `~openai/gpt-latest` | Treat OpenRouter as a dynamic catalog provider. Use `/api/v1/models` to discover IDs, context length, max completion tokens, pricing, supported parameters, deprecations, and structured-output support. Its normalized response includes both `finish_reason` and `native_finish_reason`. |
| LocalAI, Ollama, Open WebUI, Generic OpenAI-compatible | User-supplied model names | Do not validate against a fixed catalog. Probe `/models` or provider-specific endpoints where available, allow no-key local deployments, and make token/temperature/JSON-mode capabilities configurable or auto-detected. |

### Compatibility Strategy

- Add a `ModelCatalog` concept per provider. It should support static fallback entries, authenticated model listing where available, manual refresh, cache expiry, and a visible "last refreshed" diagnostic.
- Store model capabilities separately from provider capabilities. A provider can support a feature while a specific model does not.
- Add a model-aware request builder that maps the integration's generic generation settings to provider-specific parameters: `max_output_tokens`, `max_completion_tokens`, `max_tokens`, `thinking`, `thinking_config`, `reasoning`, `reasoning_effort`, `response_format`, `response_mime_type`, and `response_json_schema`.
- Add a compatibility warning layer. If a selected model is preview, deprecated, missing structured output, missing JSON schema support, or likely to reject configured sampling parameters, show this in diagnostics and avoid sending unsafe parameters.
- Keep stable default recommendations by provider, but prefer aliases only when the provider guarantees the alias behavior. For production defaults, prefer stable non-preview IDs over preview IDs unless the user explicitly opts into preview/latest aliases.
- Add provider smoke tests around representative current models using mocked HTTP fixtures: OpenAI GPT-5.5 Responses, Azure OpenAI GPT-5.5 deployment, Claude Opus 4.7 adaptive thinking, Claude Sonnet 4.6, Gemini 2.5 stable structured output, Gemini 3 preview structured output, Mistral JSON schema, Groq production model, Perplexity Sonar structured output, and OpenRouter dynamic metadata.
- Add a release checklist item to refresh model catalogs and mark deprecated defaults before every release.

## Backlog Themes

### Provider Compatibility

Open issues show recurring provider breakage and endpoint rigidity:

- Ollama/Open WebUI/custom endpoint issues: #116, #122, #132, #142, #144, #149.
- OpenAI model parameter drift, especially GPT-5 style `max_completion_tokens`: #141.
- Google/Gemini parsing and model compatibility: #130, #150, #152.
- Anthropic validation/model compatibility: #153.
- OpenRouter setup timeout/cancel behavior: #145.
- New provider requests: Venice.ai #131, ZhipuAI via closed PR #129 and open PR #155.

The code should move to a provider abstraction so each provider owns its endpoint shape, validation behavior, request parameters, timeout needs, response parser, and capability flags.

### Home Assistant Platform Alignment

Several issues point at Home Assistant API evolution and better native AI integration:

- Migration/setup compatibility: #113, #128.
- Use existing HA-configured LLM/conversation agents: #112.
- Support AI Task and AI Buttons: #134.
- Consider integration sub-entries: #136.

This project should decide its minimum supported Home Assistant version. The README mentions 2023.5, while `hacs.json` requires 2024.1. A modernized roadmap should likely target a newer baseline if AI Task/sub-entry features become core requirements.

### Suggestion Quality And Output Reliability

Closed and open issues repeatedly mention truncated output, missing YAML, missing descriptions, no suggestions, or sensor attributes not updating: #8, #9, #37, #42, #61, #65, #78, #94, #96, #97, #123, #127, #152.

The integration should stop relying only on "find the first fenced YAML block" parsing. It needs a structured response contract, validation, truncation detection, and a durable suggestion store.

### User Control

Users want more control over what is analyzed and how suggestions are generated:

- Exclude domains, areas, and entities: #102.
- Persist and recall previous suggestions: #109.
- Persistent custom system prompt field: #139.
- Earlier requests for skipping/ignoring suggestions and manual prompt flows: #24, #88, #89.

These are core product features, not nice-to-haves. They make the integration safer, cheaper to run, and easier to trust.

### Localization

Localization is active and valuable, but incomplete:

- Italian translation/output behavior: #133.
- Czech translation request: #151.
- Open PR #154 adds multilingual system prompts and Polish localization.

The integration should separate UI translation from AI output language. UI strings belong in translation files; prompt/output language should be selected from the Home Assistant language or an explicit option.

### Stability, Logs, And Diagnostics

Issue #120 asks for log cleanup and stability help. More broadly, users need clear provider health, last request metadata, timeout information, and recoverable error messages. The current provider status sensor mostly infers status from coordinator data and suggestion presence, which is not enough for reliable diagnostics.

## Open Pull Request Handling

### PR #154: Multilingual system prompts and Polish localization

This is a small, focused PR touching `const.py`, `coordinator.py`, `manifest.json`, and adding `translations/pl.json`. It should be reviewed first and likely merged or reimplemented after tests are added. The main review question is whether multilingual prompts belong in constants, translation files, or a prompt registry.

Recommended action: accept the feature direction, add tests for language selection, and merge or port it into the prompt/output-language work.

### PR #155: New providers and unified configuration/translation flow

This is a large PR touching 21 files with major changes to config flow, coordinator, services, sensors, translations, and new docs. It overlaps many real backlog items: Venice.ai #131, Open WebUI/custom endpoint flexibility #122/#132, OpenRouter setup #145, and provider configuration cleanup.

Recommended action: do not merge as one broad change until the provider abstraction and tests exist. Mine it for useful provider schemas, docs, and endpoint handling, then split it into smaller PRs: provider abstraction, Open WebUI/custom endpoint support, Venice/ZhipuAI providers, service enhancements, translation cleanup, and docs.

## Target Architecture

### Provider Layer

Create a `providers/` package with a small shared contract:

- `ProviderConfig`: normalized provider settings from config/options.
- `ProviderCapabilities`: flags for OpenAI-compatible chat, Responses API support, streaming support, custom headers, endpoint validation, timeout defaults, model listing, model metadata, token parameter names, reasoning/thinking support, JSON/schema mode support, and content-type quirks.
- `ModelCapabilities`: per-model metadata for context window, max output tokens, endpoint family, stable/preview/deprecated status, supported generation parameters, structured-output support, and known caveats.
- `BaseProvider`: methods for `validate()`, `generate()`, `parse_response()`, and `redact_for_diagnostics()`.
- Provider modules for OpenAI-compatible, Anthropic, Google, Ollama, OpenRouter, Mistral, Perplexity, and local/custom endpoints.

This would remove the large dispatch dictionary and repeated response validation blocks from `coordinator.py`.

### Suggestion Pipeline

Split the current coordinator responsibilities:

- `context.py`: collect entities, areas, devices, existing automations, and optional YAML file content.
- `filters.py`: include/exclude domains, areas, devices, entities, disabled/unavailable entities, and hidden entities.
- `prompt.py`: build prompt sections, select language, enforce input budgets, summarize oversized context.
- `suggestions.py`: parse structured provider responses, validate YAML, record warnings, and store history.
- `coordinator.py`: orchestrate refreshes and update sensors only.

### Durable Suggestion Store

Use Home Assistant's storage helper to keep recent suggestions with IDs, created timestamps, provider/model metadata, input scope, prompt summary, generated description, YAML block, parse warnings, user action state, and optional rating.

This store would satisfy #109 and also provide the missing backend needed by the custom card.

### Home Assistant Native AI Support

Add a compatibility layer for Home Assistant-native AI paths:

- Explore using configured conversation agents or AI Task entities for users who already manage provider credentials in Home Assistant (#112, #134).
- Evaluate sub-entry support for provider/model variants once the minimum HA version supports it (#136).
- Keep direct provider support for users who want this integration to be standalone.

## Roadmap

### Phase 0: Triage And Baseline

Goal: make the project easier to maintain before changing behavior.

- Add labels and milestones to GitHub: provider, config-flow, HA-compatibility, output-parsing, localization, UX, docs, tests.
- Confirm the supported Home Assistant baseline and update README/HACS metadata to match.
- Create reproducible fixtures for the highest-volume failures: provider response shape drift, timeout, truncated output, missing YAML, and config migration.
- Add issue templates that ask for HA version, integration version, provider, model, endpoint type, logs, service call data, and whether the provider works outside this integration.

### Phase 1: Safety, Compatibility, And Tests

Goal: stop the most common regressions.

- Add pytest coverage with `pytest-homeassistant-custom-component` for config flow, options flow, service handling, coordinator state updates, migration, and sensors.
- Add mock provider tests for successful responses, API errors, invalid JSON, text/plain responses, empty choices, missing `message`, missing YAML, and truncated output.
- Add linting/formatting CI, preferably Ruff plus existing hassfest/HACS checks.
- Fix config entry migration to use supported Home Assistant update APIs rather than assigning `config_entry.version` directly.
- Keep `async_forward_entry_setups` and remove stale compatibility assumptions around the older singular method.
- Add coordinator locking so concurrent service calls cannot mutate shared prompt/filter settings mid-request.
- Validate service data with a schema and normalize `domains` to a real list selector rather than a generic object.
- Make the provider status sensor represent actual provider validation/request state, not simply whether suggestions exist.

Primary issues covered: #113, #120, #123, #128, #143.

### Phase 2: Provider Modernization

Goal: make providers reliable and easier to extend.

- Introduce the provider abstraction and move provider-specific code out of `coordinator.py`.
- Support exact custom OpenAI-compatible URLs, optional validation URL, custom headers, optional API key, and Open WebUI base paths (#122, #132).
- Add local provider timeout configuration, especially for Ollama and slow local hardware (#142).
- Support Ollama/Open WebUI endpoint variants and content-type fallback for cloud models returning `text/plain` (#116, #144, #149).
- Add model-aware OpenAI token parameter selection, including `max_completion_tokens` where needed (#141).
- Add OpenAI Responses API support for `gpt-5.5`/`gpt-5.4` reasoning models, including `max_output_tokens`, `reasoning.effort`, incomplete response detection, and no blind `temperature` forwarding.
- For Azure OpenAI, separate deployment name from model family and track API version, region availability, quota/preview status, and Chat Completions versus Responses support.
- Harden Google/Gemini parsing and defaults for current Gemini models (#130, #150, #152).
- Refresh Google defaults away from deprecated `gemini-2.0-flash`; prefer Gemini 2.5 stable defaults and document Gemini 3 preview opt-in behavior.
- Refresh Anthropic validation defaults and docs for `claude-opus-4-7`, `claude-sonnet-4-6`, and `claude-haiku-4-5`; support the Anthropic Models API and adaptive thinking where available (#153).
- Refresh Groq defaults away from stale Llama 3 8B IDs and distinguish production versus preview Groq models.
- Refresh Mistral defaults and aliases for Large 3, Medium 3.5, Small 4, Ministral 3, Devstral 2, and Codestral.
- Keep Perplexity `sonar` support but expose Sonar Pro, Sonar Reasoning Pro, and Sonar Deep Research as explicit choices with timeout guidance.
- Treat OpenRouter as a dynamic catalog provider and use `/api/v1/models` metadata to filter models by context length, supported parameters, structured outputs, and deprecation/expiration.
- Harden OpenRouter setup and request timeout behavior (#145).
- Add provider plugin tests before adding Venice.ai or ZhipuAI (#131, #155, #129).

Primary issues covered: #116, #122, #130, #131, #132, #141, #142, #144, #145, #149, #150, #153.

### Phase 3: Context, Prompting, And Structured Output

Goal: make suggestions useful, parsable, and repeatable.

- Add include/exclude filters for domains, areas, devices, entities, disabled entities, hidden entities, and unavailable entities (#102).
- Add a persistent custom system prompt option plus per-service extra prompt (#139).
- Replace plain-text response parsing with a structured schema such as JSON containing `title`, `description`, `yaml`, `entities_used`, `automation_ids_used`, `confidence`, and `warnings`.
- Ask providers to emit YAML as data, not only as a fenced Markdown block; use provider-native JSON/schema modes where available and keep Markdown parsing as fallback.
- Add provider-specific structured-output adapters for OpenAI Responses/Chat Completions, Anthropic tool/JSON prompting fallback, Gemini `response_json_schema`, Mistral `response_format`, Perplexity `response_format`, and OpenRouter `response_format`.
- Validate returned YAML enough to catch malformed automation snippets before surfacing them as ready-to-use.
- Detect truncation from provider finish reasons or incomplete structured output and show a clear warning instead of silently storing partial suggestions.
- Summarize or chunk context when input budgets are exceeded instead of cutting the prompt in the middle of entity text.
- Add suggestion history with configurable retention (#109).
- Add prompt/output language selection and review PR #154 in this phase (#133, #151, #154).

Primary issues covered: #102, #109, #133, #139, #151, #152, #154.

### Phase 4: User Experience And HA-Native Workflows

Goal: make review and action easier inside Home Assistant.

- Decide whether to keep the custom card. If kept, implement the missing backend API or websocket commands against the suggestion store.
- Add services for `dismiss_suggestion`, `rate_suggestion`, `regenerate_suggestion`, `export_suggestion_yaml`, and `clear_history`.
- Add dashboard examples that work without unsupported endpoints.
- Explore AI Task/AI Buttons integration for on-demand "suggest automation for this entity/area/device" workflows (#134).
- Explore using HA-configured conversation agents/LLMs to avoid duplicate API keys (#112).
- Explore sub-entries for provider/model variants once the minimum HA version is high enough (#136).
- Keep suggestions review-only; do not auto-create automations unless a future feature adds explicit, multi-step confirmation.

Primary issues covered: #112, #134, #136, plus UX fallout from #57, #78, #96, #97, #127.

### Phase 5: Documentation, Release, And Maintenance

Goal: make releases predictable.

- Rewrite README around the actual current workflow, provider matrix, privacy notes, and troubleshooting.
- Add a model compatibility page covering stable defaults, preview opt-in, deprecated model warnings, provider-specific token parameters, and troubleshooting for model/API errors.
- Document exactly what entity/automation data is sent to cloud providers and how local providers avoid that.
- Document API key storage accurately for Home Assistant custom integrations.
- Add provider setup guides for OpenAI-compatible endpoints, Open WebUI, Ollama, OpenRouter, Gemini, Anthropic, and Azure OpenAI.
- Add a changelog and release checklist.
- Update GitHub Actions versions and pin actions where appropriate.
- Add a small compatibility matrix by integration version, HA version, provider, and known model quirks.
- Refresh the provider/model matrix during every release and record the research date/source links.

## Suggested Releases

### 1.4.3 Patch Release

- Fix config migration/setup compatibility.
- Add custom system prompt option or correct README if it is intentionally service-only.
- Add configurable local-provider timeout.
- Fix OpenAI `max_completion_tokens` handling for newer models.
- Add a safe short-term model default refresh for Google, Groq, Mistral, Anthropic, and OpenAI without removing user-selected custom models.
- Fix obvious provider response parser bugs and better last-error surfacing.
- Add Czech translation if the submitted file is usable.
- Merge or port PR #154 if language selection tests pass.

### 1.5.0 Foundation Release

- Provider abstraction.
- Model catalog and capability metadata.
- Test suite and CI linting.
- Exclusion filters.
- Suggestion history storage.
- Structured output parsing.
- Backed custom card API or removal of the unsupported card.

### 1.6.0 Home Assistant Native AI Release

- AI Task/AI Button integration.
- Optional reuse of configured HA conversation agents/LLMs.
- Provider sub-entry evaluation or implementation.
- Expanded provider support from split pieces of PR #155.

### 2.0.0 Cleanup Release

- Remove legacy config fields and deprecated behavior after migration support is proven.
- Finalize stable internal provider APIs.
- Rework dashboard/card UX around stored suggestions and explicit user review.

## Issue Coverage Map

| Area | Issues / PRs | Plan |
| --- | --- | --- |
| Exclusions | #102 | Phase 3 filters |
| History | #109 | Phase 3 suggestion store |
| HA-native AI | #112, #134, #136 | Phase 4 |
| HA compatibility | #113, #128 | Phase 1 |
| Local/custom endpoints | #116, #122, #132, #142, #144, #149 | Phase 2 |
| Provider parsing/models | #130, #141, #145, #150, #153 | Phase 2 |
| Model catalog churn | #130, #141, #150, #153 plus current model research | Phase 2 and Phase 5 |
| New providers | #131, #129, #155 | Phase 2 after provider abstraction |
| Localization | #133, #151, #154 | Phase 3 |
| Prompt customization | #139 | Phase 3 or 1.4.3 patch |
| No/truncated suggestions | #123, #127, #152 | Phase 1 and Phase 3 |
| Already configured | #143 plus older #69/#74/#90 | Phase 1 config-flow cleanup |
| Stability/logs | #120 | Phase 1 diagnostics, Phase 5 docs |

## Risks And Decisions

- Minimum Home Assistant version is the largest architectural decision. Supporting very old versions conflicts with AI Task and sub-entry work.
- PR #155 is valuable but too broad to merge safely before test coverage and provider boundaries exist.
- Cloud-provider privacy expectations need clearer documentation because entity names, states, attributes, areas, devices, and automations may be sent to providers.
- Structured output will improve parsing, but providers vary in JSON-mode support. A fallback parser is still needed.
- Latest model support should not be implemented as one more hardcoded constants update. The safer path is catalog metadata, capability-aware request building, and explicit warnings for preview/deprecated models.
- Automatic automation creation should remain out of scope until validation, review, and explicit confirmation flows are mature.

## Immediate Next Actions

1. Add tests and CI linting before feature work.
2. Fix migration/config-flow compatibility and provider status accuracy.
3. Split provider logic out of `coordinator.py`.
4. Add model catalog/capability metadata and refresh stale defaults before broad provider feature work.
5. Implement exact/custom endpoint handling for OpenAI-compatible and Open WebUI users.
6. Add exclusion filters, persistent custom prompt, and suggestion history.
7. Review PR #154 for near-term merge and split PR #155 into smaller provider-focused changes.

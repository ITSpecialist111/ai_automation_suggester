# Changelog

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
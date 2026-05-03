# AI Automation Suggester 1.5.0

This foundation release modernizes provider/model handling and makes suggestions easier to review, retain, and display in Home Assistant.

## Highlights

- Current model defaults and model capability metadata for OpenAI GPT-5-style models, Azure OpenAI deployments, Claude Sonnet/Opus 4.x, Gemini 2.5/3 preview, Groq, Mistral, Perplexity, OpenRouter, and local/OpenAI-compatible providers.
- OpenAI Responses API support for GPT-5-style reasoning models with safer `max_output_tokens` and reasoning effort handling.
- Structured output support with JSON-first parsing, fenced YAML fallback, YAML validation warnings, and truncation warnings.
- Persistent suggestion history stored in Home Assistant storage.
- New backend endpoints for the included Lovelace card:
  - `GET /api/ai_automation_suggester/suggestions`
  - `POST /api/ai_automation_suggester/{accept|decline|dismiss}/{suggestion_id}`
- New services:
  - `ai_automation_suggester.clear_history`
  - `ai_automation_suggester.update_suggestion`
- Persistent custom prompt, exclusion filters, request timeout, and history retention options.
- Tests, changelog, issue templates, and CI scaffolding for safer future releases.

## HACS Updates

HACS detects updates from GitHub releases. After the `1.5.0` tag and GitHub release are published, HACS users should see the update in Home Assistant and can upgrade from HACS. A Home Assistant restart is still required after updating a custom integration.

## Notes For Upgraders

- Existing custom model names remain supported.
- Some stale defaults were refreshed for new configurations. Existing configured model values are preserved unless the user changes them in options.
- Suggestions are still review-only. The integration does not automatically create or modify automations.
- Cloud providers may receive entity names, states, attributes, areas, device context, and automation metadata. Use local providers for local-only processing.
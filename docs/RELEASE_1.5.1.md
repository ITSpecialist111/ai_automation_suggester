# AI Automation Suggester 1.5.1

This patch release fixes persistent notifications when an AI provider returns malformed structured output.

## Fixed

- Recovers suggestions from JSON-like responses where the provider emits multiline YAML outside a valid JSON string.
- Prevents raw malformed JSON payloads from being shown as the persistent notification body.
- Adds regression tests for malformed Mistral-style structured responses.

## Notes

If a provider reports a `length` or token-limit finish reason, the integration still shows a truncation warning. Lower the entity limit or output a smaller number of suggestions if the response is cut off.
# AI Automation Suggester 1.5.6

This patch fixes Gemini 2.5 Flash structured-output requests.

## Highlights

- Sends a Google Gemini-compatible response schema that omits JSON Schema keywords rejected by the Gemini API.
- Preserves the fuller JSON schema for OpenAI-compatible providers that accept it.

## Fixed

- Resolves Gemini API `400 INVALID_ARGUMENT` errors mentioning unsupported `additionalProperties` fields in `generation_config.response_schema`.
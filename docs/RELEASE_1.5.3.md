# AI Automation Suggester 1.5.3

This patch focuses on provider setup reliability and endpoint flexibility for local and OpenAI-compatible deployments.

## Highlights

- Added an optional Ollama/Open WebUI base URL field. You can still use the existing host, port, and HTTPS fields for native Ollama, or provide a full base URL such as `http://homeassistant.local:3000/ollama`.
- Added fallback Ollama API path handling for native Ollama and Open WebUI proxy paths.
- Made Custom OpenAI-compatible validation accept base URLs, `/v1` URLs, exact chat completion URLs, and common model-listing endpoints.
- Switched Anthropic and Gemini setup checks to model-listing endpoints where possible, avoiding fragile one-token generation pings during setup.
- Applied the configured request timeout to more setup validation calls, including OpenRouter.
- Added endpoint normalization regression tests.

## Notes

- Existing Ollama configurations continue to work with host, port, and HTTPS settings.
- The new base URL field takes precedence when it is provided.
- Larger feature requests are tracked in `docs/FEATURE_REQUEST_PLAN.md`.
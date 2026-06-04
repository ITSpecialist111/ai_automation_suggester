# AI Automation Suggester 1.5.7

This patch fixes a setup failure on recent Home Assistant releases and a Perplexity setup-validation error.

## Highlights

- The integration no longer runs an AI inference during sensor platform setup, which previously caused `setup_error` on Home Assistant 2025.x and newer.
- Perplexity setup validation now succeeds with `sonar` models.

## Fixed

- **Setup error on HA 2025.x+ (issue #166):** Sensor setup passed `update_before_add=True`, which in newer Home Assistant versions calls `CoordinatorEntity.async_update()` during platform setup. That triggered a full LLM request (10–60+ seconds) and exceeded the setup timeout, leaving the integration in `setup_error` on every restart — most visibly with local/slow providers (Ollama, LocalAI, llama.cpp). Entities now register without an immediate refresh and populate from coordinator data, refreshing when `generate_suggestions` runs.
- **Perplexity validation always failing (issue #171):** The setup validation probe sent `max_tokens: 1`, but Perplexity `sonar` models require `max_tokens >= 16` and reject smaller values with a `400`. The probe now uses `max_tokens: 16`, so validation passes regardless of the user's configured output token limit.

## Upgrade notes

No configuration changes are required. After updating, restart Home Assistant; the integration should load without `setup_error`, and Perplexity setup validation should succeed.

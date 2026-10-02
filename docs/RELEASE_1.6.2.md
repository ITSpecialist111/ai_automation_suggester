# AI Automation Suggester 1.6.2

Release date: 2026-10-02

## Highlights

- **GPT-6 support:** OpenAI GPT-6 models such as `gpt-6.1-sol` and `gpt-6-luna` no longer fail with `Unsupported parameter: 'max_tokens' is not supported with this model` (#192). Model detection only recognized `gpt-5`, `o3`, and `o4` names, so newer models fell back to Chat Completions with `max_tokens` and a temperature. GPT-5-or-later and every `o`-series model are now matched by version number, so future generations work without a catalog update.
  - **OpenAI:** these models use the Responses API with `max_output_tokens` and reasoning effort, as GPT-5 models already did.
  - **Azure OpenAI, Custom OpenAI, Generic OpenAI:** these models use Chat Completions with `max_completion_tokens` and no temperature.
- **Safer default for unknown OpenAI models:** Unrecognized model names on the direct OpenAI provider now send `max_completion_tokens` instead of the deprecated `max_tokens`. Unrecognized models on other providers are unchanged.

## Upgrade

Update through HACS and restart Home Assistant. No config-entry or stored-history migration is required. Configured models, token budgets, and suggestion history are unchanged.

## Behavior Change

- On the OpenAI provider, GPT-6-and-later and `o1`/`o5`-style model names now use the Responses API, the Reasoning Effort option, and structured output, and no longer send the configured temperature. `o3` and `o4-mini` keep their existing catalog behavior.

## Validation

- 155 automated tests pass in a clean Python 3.12 environment, matching CI. Ruff checks pass.
- The new regression tests fail against 1.6.1 (34 failures) and pass with this release.
- Home Assistant 2026.9.4 container smoke test: the real config flow and `ai_automation_suggester.generate_suggestions` service ran against a local TLS mock of `api.openai.com` that rejects `max_tokens` for GPT-5-and-later models, as the OpenAI API does.
  - 1.6.1: `gpt-6.1-sol` and `gpt-6-luna` fail with HTTP 500 and the exact sensor error from #192. `gpt-5.4-mini` passes.
  - 1.6.2: all three models return HTTP 200, show `New Suggestions Available`, and report `connected`.
- No live paid-provider inference was performed for this release.

## Contributors

Thanks @briankavanaugh for the clear #192 report, including the control test with `gpt-5.4-mini`.

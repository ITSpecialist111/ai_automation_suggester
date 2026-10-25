# AI Automation Suggester 1.7.0

## Temperature compatibility

- Direct Anthropic requests no longer send temperature, including for saved legacy models. The obsolete temperature form control has been removed; no reconfiguration is required.
- Claude 4.7-and-later and OpenAI GPT-5-and-later / `o`-series model names also omit temperature through OpenRouter, Requesty, Cheaper Inference, LiteLLM, and custom OpenAI-compatible APIs.
- Other routed models keep their configured temperature.
- The direct Anthropic API version remains pinned to `2023-06-01`. This release does not perform an API-version migration. Anthropic's `2026-10-21` version rejects sampling parameters on every model; newer Claude models already reject custom sampling on the older version.

## Providers and models

- Integrates PR #199 (Anthropic temperature removal).
- Integrates PR #198 and issue #197 (Cheaper Inference provider).
- Integrates PR #196 (MiniMax M3.1 Flash default with saved-model preservation).
- Adds Claude Sonnet/Opus/Haiku 5.5 and Fable 5.1 to the catalog, with Sonnet 5.5 as the default for new Anthropic configurations.
- Saved model selections are not replaced on upgrade.

## Validation and limitations

- Automated tests include real loopback HTTP generation against mock Anthropic, OpenRouter, Requesty, Cheaper Inference, and MiniMax endpoints; request payloads, parsed YAML, suggestion history, notifications, and explicit errors are checked.
- Home Assistant helpers and storage are stubbed in those tests. They are not a live Home Assistant installation test or a paid provider inference test.
- The network Home Assistant connection was unavailable, so no changes or test inference were performed on the user's instance.
- No inference is automatically started on startup. `initializing` means no provider request outcome exists yet, not that a background request is stuck. Explicitly call `ai_automation_suggester.generate_suggestions` with `all_entities: true` and a small entity limit to obtain a request result.

Thanks to the contributors of PRs #196, #198, and #199.

# AI Automation Suggester 1.6.1

Release date: 2026-09-26

## Highlights

- **Unicode-safe automation and script context:** Names from `automations.yaml` and `scripts.yaml` are sent as written, such as `Pomocník klima vyp`, instead of YAML escapes such as `"Pomocn\xEDk klima vyp"`. Models could copy those escapes into their JSON, which JSON does not allow. This matches the escaped text posted in #172.
- **Tolerant JSON decoding:** Responses with invalid escapes such as `\xED` or `\'`, or with literal newlines inside strings, are decoded without the best-effort repair warning. Escaped single quotes no longer corrupt YAML values, for example `to: \'off\'`. Valid JSON is unchanged.
- **Clear output-limit errors:** Stop reasons from Gemini (`MAX_TOKENS`), Anthropic (`max_tokens`), Ollama (`length`), and OpenAI Responses (`max_output_tokens`) now produce the truncation warning, not just OpenAI-compatible `length`. If a provider returns no final answer at the limit, generation fails with a message naming your Max Output Tokens setting. Gemini also reports thinking-token usage, blocked prompts, and other empty-response reasons (#172).
- **Raw response debug logging:** With debug logging enabled, each generation logs the prompt size and the raw provider response, with credentials redacted. This was promised in #172 so parse failures can be diagnosed from the provider's actual output.
- **OpenRouter free router:** `openrouter/free` now requests structured output, so OpenRouter routes it only to free models that support it. Thanks @JamieC03 for PR #190.
- **Automatic runs documentation:** The README now states that generation is on demand. The example automations must be imported and enabled. It also includes an optional after-startup automation (#177).

## Upgrade

1. Update through HACS and restart Home Assistant. No config-entry or stored-history migration is required. Configured models, token budgets, and suggestion history are unchanged.
2. If generation fails with "stopped at the Max Output Tokens limit", increase Max Output Tokens in the integration options. For reasoning or thinking models, start with 4096. Higher limits can increase usage and cost, so check your provider's usage dashboard.
3. For scheduled or after-restart runs, import an example automation as described in the README's **Automatic Suggestions** section.

## Behavior Change

- An OpenAI-compatible response with empty content that stopped at the output limit now fails with an explicit error. Previously, unfinished `reasoning_content` could appear as a successful suggestion and the provider status could show `connected`. Completed reasoning-model answers still use the `reasoning_content` fallback (#127).

## Diagnostics and Follow-Up

- To report a parsing problem, enable debug logging as described under **Error Handling & Troubleshooting > Debug Logging** in the README. Run one generation and share the `Raw ... response` log entry. Remove private details first, because the response can include entity names and areas.
- YAML that arrives from the provider without newlines still cannot be reconstructed safely by guessing indentation. #172 stays open for retesting with the new debug logs.
- Default token budgets remain 500 tokens each for compatibility. Existing entries keep their saved values.
- Claude Pro/Max subscription authentication remains unimplemented (#179). The Anthropic provider continues to use API key authentication.

## Validation

- 116 automated tests pass in clean Python 3.11 and 3.12 environments.
- Repository-wide Ruff checks pass.
- A Home Assistant 2026.9.3 container smoke test against a local fake OpenAI-compatible and Ollama provider passes 20 of 20 checks. It covers config flows, generation, notifications, sensors, provider status, prompt content, and debug logs. The same test against 1.6.0 passes 9 of 20 and reproduces the escaped prompt context, the repair warning, the corrupted `to: \'off\'` trigger, and truncation shown as success.
- Provider HTTP behavior is tested with mocks and the local fake provider. No live paid-provider inference was performed for this release.

## Contributors

Thanks @JamieC03 for PR #190. Thanks @afreemo-glitch, @JamesHannon, @pyrocumulus, @andynash, and @Pan-Lorenc for the #172 reports and data, and @wintrmte for confirming the #177 diagnosis.

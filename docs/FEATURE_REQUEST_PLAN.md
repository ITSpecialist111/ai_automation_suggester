# Feature Request Plan

This plan groups the remaining open feature requests into release-sized tracks. Provider bug fixes can ship as patch releases, while the items below should stay open until the related work is implemented and tested.

## Phase 1: Provider Setup And Reliability

Targets: #116, #122, #123, #127, #132, #144, #145, #150, #153

- Keep improving local-provider setup flows for native Ollama, Open WebUI, LocalAI, and OpenAI-compatible services.
- Make validation low-risk by preferring model-listing endpoints and clear timeout handling over generation pings.
- Improve diagnostics when a provider is reachable but returns no suggestions, including the final endpoint attempted and provider response category.
- Add focused tests around endpoint normalization and parser behavior as bug reports arrive.

## Phase 2: Translations And Localization

Targets: #133, #151

- Status: implemented in v1.5.5; awaiting reporter confirmation before closing any issue that needs a live Home Assistant retest.
- Keep translation files structurally aligned when new setup/options keys are added.

## Phase 3: Provider Expansion

Target: #131

- Add Venice.ai as an OpenAI-compatible provider if its API supports the existing chat-completions request shape.
- Add model defaults, validation, documentation, and provider tests before closing the request.

## Phase 4: Home Assistant Native AI Integration

Targets: #112, #134

- Investigate selecting an existing Home Assistant conversation/LLM agent instead of configuring a direct provider connection.
- Explore AI Task / AI Button workflows once the supported Home Assistant APIs and UX expectations are clear.
- Keep direct-provider support as the baseline while HA-native AI support matures.

## Phase 5: Multi-Entry Configuration

Target: #136

- Evaluate sub-entry support for multiple provider profiles under one integration entry.
- Preserve current config entries through migration and avoid breaking service calls or dashboard history.
- Add migration and options-flow tests before release.
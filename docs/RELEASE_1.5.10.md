# AI Automation Suggester 1.5.10

Release date: 2026-07-11

## Summary

This patch release makes suggestion generation more accurate and reliable while preserving the personal household context that makes the integration useful. Entity names, rooms, states, attributes, device details, and optional automation/script context remain available to the selected model. Only authentication credentials are removed from error diagnostics.

## Highlights

- Area exclusions now work from the first request, and device/area context is included correctly.
- `entities_processed` now lists exactly the entities sent to the provider.
- Entities omitted by limits or input budget remain eligible for later runs.
- Prompt budgeting retains complete context blocks rather than cutting entity or YAML text midway.
- Suggestions warn about unknown entity, automation, script, and service references.
- Model output can no longer choose stored suggestion IDs or review status.
- Provider failures are returned to service callers and credentials are redacted from diagnostics.
- Provider status remains `initializing` until the first successful request.
- Concurrent history writes and review actions are serialized safely.
- Home Assistant 2024.1 compatibility is retained while current coordinator APIs are used when available.

## Validation

- 38 automated tests pass on clean Python 3.11 and 3.12 environments and the development Python 3.14 environment.
- Repository-wide Ruff checks pass.
- Python compilation succeeds.
- Dashboard JavaScript syntax check succeeds.
- Integration JSON and YAML metadata parse successfully.

## Upgrade

Update through HACS and restart Home Assistant. Existing config entries and stored suggestion history remain compatible; no migration or reconfiguration is required.

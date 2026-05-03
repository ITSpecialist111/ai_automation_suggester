# AI Automation Suggester 1.5.5

This patch improves localization for setup text and generated AI suggestions.

## Highlights

- Added Czech translations from the community contribution, updated for the current setup/options schema.
- Fixed the reported spacing and capitalization typos in the contributed Czech wording.
- Completed missing Italian labels for services, exclusion filters, history, timeout, OpenAI reasoning, and Ollama/Open WebUI fields.
- Added a prompt instruction so generated suggestion titles, descriptions, and warnings follow the configured Home Assistant language when it is not English.

## Notes

- YAML, entity IDs, service names, and code identifiers are still kept unchanged in generated suggestions.
- Users can still override or strengthen language preferences with the persistent custom system prompt or per-call custom prompt.
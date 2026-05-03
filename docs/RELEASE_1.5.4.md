# AI Automation Suggester 1.5.4

This patch follows up on the Open WebUI/Ollama support added in `v1.5.3`.

## Highlights

- Added an optional Ollama/Open WebUI API key field.
- Sends the configured token as a bearer authorization header during Ollama setup validation.
- Sends the same bearer authorization header when generating suggestions through authenticated Open WebUI Ollama proxy endpoints.

## Notes

- Native Ollama installations that do not require authentication can leave the new API key field blank.
- For Open WebUI, use the existing base URL field for the `/ollama` endpoint and provide the Open WebUI API key when that endpoint returns `401 Not authenticated`.
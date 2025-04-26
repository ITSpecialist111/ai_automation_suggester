# AI Automation Suggester

[![Buy Me A Coffee](https://img.shields.io/badge/Buy&nbsp;me&nbsp;a&nbsp;coffee-donate-yellow?logo=buy-me-a-coffee&style=for-the-badge)](https://www.buymeacoffee.com/ITSpecialist)

[![Validate with hassfest](https://img.shields.io/github/actions/workflow/status/ITSpecialist111/ai_automation_suggester/hassfest.yaml?style=for-the-badge)]()
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/ITSpecialist111/ai_automation_suggester/validate.yaml?style=for-the-badge)]()
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/ITSpecialist111/ai_automation_suggester?style=for-the-badge)]()
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)]()

---

## Why does this exist?

Building a truly “smart” home means more than sprinkling sensors and smart‑plugs around the house.  Once your Home Assistant instance tops a few dozen entities it becomes **hard to see the hidden automation potential**:

* _Which sensors could combine to save energy?_
* _Where should lights be presence‑based instead of on timers?_
* _How can I surface weird edge‑cases the family keeps forgetting?_

Most of us either spend hours experimenting—or give up and leave gear idle.  
**AI Automation Suggester** flips that around by acting as a _free on‑call automation consultant_:

1. **Scans entities, devices, areas, and existing automations**  
2. **Feeds a summarised snapshot to an LLM** (OpenAI, Anthropic, Google Gemini, Groq, LocalAI, Ollama, Mistral or Perplexity)  
3. **Returns context‑aware YAML samples** you can copy‑paste straight into Home Assistant.  

Think of it as _“ChatGPT for Home Assistant”… but wired directly into your actual floor‑plan._

---

## What’s new in **v1.3.1**

* **`description` & `yaml_block` attributes** – cleaner parsing in Dashboards  
* Ollama, LocalAI & Custom‑OpenAI robustness tweaks  
* Deprecated options‑flow call removed (pre‑2025.12 compatibility)  
* README spring‑clean & new badge layout  

_Complete changelog lives in GitHub releases._

---

## Screenshots

> Replace the placeholder filenames with your own screenshots if you fork this project.

| Suggestions Overlay | Compact Dashboard Card |
|---|---|
| ![Suggestions example](docs/img/suggestions.png) | ![Dashboard](docs/img/dashboard.png) |

---

## Quick‑Start

1. **Install via HACS** – search _AI Automation Suggester_  
2. **Add Integration** → pick provider → paste API key (or local server details)  
3. **Fire the service once** from Developer Tools → `ai_automation_suggester.generate_suggestions`  
4. Check the new sensor `sensor.ai_automation_suggestions_<provider>` (and the Notification drawer).  

---

### Example Dashboard Snippet

```yaml
type: markdown
content: >
  **Status:** {{ states('sensor.ai_automation_suggestions_google') }}

  **Last update:** {{ state_attr('sensor.ai_automation_suggestions_google','last_update') }}

  ---

  {{ state_attr('sensor.ai_automation_suggestions_google','description') }}
```

---

## Contribute / Support

PRs & issues welcome.  
If this saves you time, [Buy me a coffee](https://www.buymeacoffee.com/ITSpecialist) ☕ keeps the project moving.

---

MIT License • © ITSpecialist111

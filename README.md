# AI Automation Suggester

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-%E2%98%95%EF%B8%8F-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/ITSpecialist)
[![Validate with hassfest](https://img.shields.io/github/actions/workflow/status/ITSpecialist111/ai_automation_suggester/hassfest.yaml?style=for-the-badge)](https://github.com/ITSpecialist111/ai_automation_suggester/actions)
[![HACS validation](https://img.shields.io/github/actions/workflow/status/ITSpecialist111/ai_automation_suggester/validate.yaml?style=for-the-badge)](https://github.com/ITSpecialist111/ai_automation_suggester/actions)
[![GitHub release](https://img.shields.io/github/v/release/ITSpecialist111/ai_automation_suggester?style=for-the-badge)](https://github.com/ITSpecialist111/ai_automation_suggester/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://hacs.xyz/)

> **Current version:** 1.3.1 • **Tested on Home Assistant ≥ 2024.1**

An integration for Home Assistant that leverages AI language models to understand your unique home environment and propose intelligent automations. By analysing your entities, devices, areas, and **existing automations**, the AI Automation Suggester surfaces new, context‑aware ideas that streamline home management and boost efficiency, comfort and security.

---

## 🚀 Quick highlights (v1.3.1)

* **`description` & `yaml_block` split** – dashboards can now show prose *and* raw YAML separately.  
* Supports **OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, Mistral AI, Perplexity AI**.  
* Service `ai_automation_suggester.generate_suggestions` accepts `all_entities`, `domains`, `entity_limit`, `custom_prompt`.  
* Two sensors exposed: suggestions + provider status.

---

## 1 • Purpose & problem statement

Smart‑homes grow complex fast. Which automations actually help?  
**AI Automation Suggester = personal automation consultant** spotting:

* Energy‑saving tweaks
* Security gaps
* Quality‑of‑life conveniences
* Maintenance reminders

with ready‑to‑paste YAML.

---

## 2 • How it works

1. **Snapshot** – entity/device/area/automation metadata collected.  
2. **AI call** – prompt sent to chosen provider.  
3. **Result parsing** – splits into `description` and `yaml_block`.  
4. **Notification & sensors** – easy review in HA UI or dashboards.

---

## 3 • Features

| Category | Details |
|----------|---------|
| **Multi‑provider** | OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, Mistral AI, Perplexity AI |
| **Custom scope**  | Random entity sampling, domain filter, entity limit |
| **Custom prompts**| Steer suggestions (“focus on off‑peak energy”) |
| **Persistent results** | Stored as sensor attributes |
| **Dashboard‑ready** | `description` & `yaml_block` attributes |

---

## 4 • Prerequisites

* **Home Assistant ≥ 2024.1**  
* Cloud LLMs: API keys  
* Local LLMs: LocalAI/Ollama server reachable by HA

---

## 5 • Installation

### a) HACS (recommended)

1. HACS → *Integrations* → search “AI Automation Suggester”.  
2. Install → restart HA.

### b) Manual

1. Download the release ZIP.  
2. Copy `custom_components/ai_automation_suggester` into `config/custom_components/`.  
3. Restart HA.

---

## 6 • Configuration

1. Settings → Devices & Services → **Add Integration** → AI Automation Suggester.  
2. Select provider + credentials.  
3. Optionally adjust `model` and `max_tokens`.  
4. Repeat for multiple providers.

---

## 7 • Using the service

| Field | Purpose |
|-------|---------|
| `provider_config` | Target a specific config entry |
| `all_entities` | Analyse every entity vs. only new ones |
| `domains` | Domain list or comma‑string |
| `entity_limit` | Cap for token control |
| `custom_prompt` | Extra instructions for the LLM |

---

## 8 • Dashboard snippets

### Description card

```yaml
content: >
  **Status:** {{ states('sensor.ai_automation_suggestions_google') }}

  **Last update:** {{ state_attr('sensor.ai_automation_suggestions_google','last_update') }}

  ---

  {{ state_attr('sensor.ai_automation_suggestions_google','description') }}
```

### YAML block card

```yaml
content: >
  {% set y = state_attr('sensor.ai_automation_suggestions_google','yaml_block') %}
  {% if y %}
  ```yaml
  {{ y }}
  ```
  {% else %}
  _No YAML block in last suggestion._
  {% endif %}
```

---

## 9 • Troubleshooting

* **No suggestions received** → check provider logs / API quota or lower `entity_limit`.  
* **Provider status = error** → double‑check endpoint / model name.  
* **Template errors** → reference `description` or `yaml_block`, not `suggestions`.

---

## 10 • Roadmap

* One‑click “Create automation”  
* Feedback loop for smarter prompts  
* More languages

---

## 11 • License & support

MIT license. Not affiliated with Home Assistant or any AI provider.

Found it helpful? **[Buy me a coffee ☕](https://www.buymeacoffee.com/ITSpecialist)** – keeps the tokens flowing!

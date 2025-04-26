
<!-- Buy‑me‑a‑coffee at the very top -->
<p align="center">
  <a href="https://www.buymeacoffee.com/ITSpecialist" target="_blank">
    <img src="https://img.shields.io/badge/Buy&nbsp;me&nbsp;a&nbsp;coffee-Support&nbsp;Dev-yellow?style=for-the-badge&logo=buy-me-a-coffee" alt="Buy Me A Coffee">
  </a>
</p>

# AI Automation Suggester

[![Validate with hassfest](https://img.shields.io/github/actions/workflow/status/ITSpecialist111/ai_automation_suggester/hassfest.yaml?style=for-the-badge)]()
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/ITSpecialist111/ai_automation_suggester/validate.yaml?style=for-the-badge)]()
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/ITSpecialist111/ai_automation_suggester?style=for-the-badge)]()
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)]()

An **AI‑powered assistant** for Home Assistant that *studies* your entities, areas, devices **and** existing
automations, then proposes fresh YAML you can drop straight into your system.

---

## ✨ Why does this exist?

*“I’ve added 200+ entities… now what?”*

Building a truly smart home often hits a familiar wall:

* **Too many possibilities** – every new sensor or light multiplies the ways things *could* interact.  
* **Writer’s block** – YAML automations look simple … until you try capturing real‑world nuance
  (presence, time, energy prices…).  
* **Maintenance overload** – even seasoned users forget to revisit old routines when hardware or
  habits change.

The result is an **under‑automated house** full of unrealised potential.

### The Fix – an Automation Copilot

AI Automation Suggester behaves like a consultant who:

1. **Inventories** your Home Assistant (entities, devices, areas **plus** existing automations).  
2. **Spots gaps & synergies** – e.g. *“You have a motion sensor in the hallway and a door sensor
   nearby; combine them for smarter lighting.”*  
3. **Drafts ready‑to‑paste YAML** including triggers / conditions / actions that reference your
   real `entity_id`s.  
4. Repeats on demand, so ideas evolve as your home evolves.

You still decide what runs – the integration simply boots you past the blank‑page stage.

---

## 📸 What to expect

<p align="center">
  <img src="Screenshot 2025-01-19 082247-1.png" alt="Notification example" width="700"/>
  <br><em>AI suggestions delivered right inside Home Assistant</em>
</p>

<p align="center">
  <img src="Screenshot 2025-01-19 083200.png" alt="Dashboard card example" width="700"/>
  <br><em>Dashboard showing human‑readable description and extracted YAML block</em>
</p>

---

## 🚀 How it works

| Step | What happens? |
|------|---------------|
| **1&nbsp;· Snapshot** | On manual trigger *or* a scheduled automation, the integration collects a **randomised sample** (size configurable) of your entities & attributes plus a list of existing automations. |
| **2&nbsp;· Prompt building** | That snapshot is embedded into a **system prompt** describing your house. You can append a *custom prompt* such as “focus on energy‑saving”. |
| **3&nbsp;· Provider call** | The prompt is sent to your chosen model – OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, Mistral or Perplexity. |
| **4&nbsp;· Parsing** | The raw LLM response is stored on a sensor attribute:<br> `description` (prose)  ·  `yaml_block` (detected <code>```yaml ... ```</code> code)  ·  full `suggestions`. |
| **5&nbsp;· Surface** | A persistent notification appears. Markdown cards can show the attributes for a no‑code dashboard. |

---

## 🏆 Benefits

* **Minutes, not hours** – go from idea to working automation fast.  
* **Context‑aware** – suggestions include area/device info so you’ll see *living‑room‑specific*
  rules, not boiler‑plate.  
* **Model‑agnostic** – cloud keys or fully‑local inference, your choice.  
* **Safe to try** – nothing runs automatically; you review & paste.  

---

## 📦 Features (v1.3.1)

* Multi‑provider back‑end (OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, Mistral, Perplexity).  
* Service **`ai_automation_suggester.generate_suggestions`** with flags  
  `all_entities`, `domains`, `entity_limit`, `custom_prompt`.  
* Two diagnostics sensors: **Suggestions** & **Provider Status**.  
* Built‑in example automations (new‑entity detection & weekly review).  
* Dashboard‑friendly attributes `description` & `yaml_block` *(since 1.3.0)*.  

---

## 🛠️ Installation

### HACS (recommended)

1. In HACS → **Integrations** → search *“AI Automation Suggester”*.  
2. Click install and restart Home Assistant.  
3. Settings → Devices & Services → **+ Add Integration** → choose AI Automation Suggester.

### Manual

```bash
custom_components/
└── ai_automation_suggester
    ├── __init__.py
    ├── ...
```

Restart HA and add via UI.

---

## ✍️ Usage

* **Manual** – Developer Tools → **Services** → call
  `ai_automation_suggester.generate_suggestions`.  
* **Automatic** – enable the shipped example automations or craft your own triggers.  
* **Dashboard snippets**  
  *Description*  
  ```jinja
  {{ state_attr('sensor.ai_automation_suggestions_<provider>', 'description') }}
  ```  
  *YAML block*  
  ```jinja
  {{ state_attr('sensor.ai_automation_suggestions_<provider>', 'yaml_block') }}
  ```

---

## 🧩 Troubleshooting

| Symptom | Check |
|---------|-------|
| “No suggestions available” | API key valid? provider status sensor showing `error`? try smaller `entity_limit`. |
| Provider Status `error` | Inspect Home Assistant log for `processing error:` lines. |
| Deprecation warning (options flow) | Fixed in **1.3.1** – update! |

---

## 🤝 Contributing & Support

Issues, PRs and translations are very welcome.  
If this project saves you time, **coffee keeps the ideas flowing** – hit the button up top ☕.

---

© 2025 • MIT License • Not affiliated with Home Assistant or any listed AI providers.

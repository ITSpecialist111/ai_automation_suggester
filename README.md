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

An **AI‑powered assistant** for Home Assistant that leverages large language models to understand your unique smart home environment – your entities, areas, devices, **and** existing automations. It proposes intelligent, actionable YAML suggestions tailored to your specific setup, helping you unlock your home's full potential.

---

## ✨ Why does this exist? (Purpose and Problem Statement)

As your Home Assistant setup grows, managing its complexity and identifying new opportunities for automation can become challenging. You might find yourself with:

* **Too many possibilities:** Every new device adds countless potential interactions.
* **Automation "Writer's Block":** Translating a complex idea into functional YAML can be daunting.
* **Underutilized Potential:** Many devices sit idle or require manual control because the right automation hasn't been thought of or created.
* **Maintenance Overload:** Keeping existing automations relevant as your home evolves is difficult.

The result is often an **under-automated house** despite having powerful hardware.

### The Fix – Your Personal Automation Copilot

The AI Automation Suggester integration solves these challenges by acting as a personal automation consultant. It intelligently analyzes your Home Assistant instance to:

1.  **Analyze your home's state:** Understand your devices, their capabilities, locations, and existing automations.
2.  **Identify opportunities:** Spot gaps, synergies, and potential improvements for energy saving, security, comfort, and convenience.
3.  **Draft ready-to-paste YAML:** Provide concrete, tailored automation ideas as YAML snippets you can review, tweak, and implement directly.

**In essence,** this integration turns the complexity of a large Home Assistant environment into actionable insights and tangible benefits, guiding you toward a more efficient, comfortable, and secure smart home.

---

## 🚀 How It Works (The Solution)

The integration follows a simple, effective process:

| Step | What happens? | Details |
|------|---------------|---------|
| **1&nbsp;· Snapshot** | Collects data about your home. | On manual trigger or schedule, the integration gathers information on your entities (including attributes), devices, areas, **and** existing automations. You can control the scope using filters and limits. |
| **2&nbsp;· Prompt Building** | Structures the data for the AI. | This snapshot is embedded into a detailed system prompt describing your specific Home Assistant setup. You can enhance this with a *custom prompt* to steer suggestions towards specific goals (e.g., "focus on presence lighting"). |
| **3&nbsp;· Provider Call** | Sends the prompt to the AI. | The crafted prompt is sent to your configured AI provider (OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, Mistral, Perplexity). |
| **4&nbsp;· Parsing** | Processes the AI's response. | The raw response from the AI is parsed to extract key information: a human-readable `description` of the suggestion, the actual `yaml_block` code, and potentially other details. This information is stored on sensor attributes. |
| **5&nbsp;· Surface** | Delivers the suggestions. | Suggestions appear as Home Assistant persistent notifications. You can also use sensor attributes to display suggestions on custom dashboards for easy review and implementation. |

Randomized entity selection (configurable) helps ensure each analysis run can surface fresh ideas rather than repeating the same suggestions.

---

## 📸 What to Expect (Screenshots)

Suggestions are delivered directly within Home Assistant notifications:

<p align="center">
  <img src="https://raw.githubusercontent.com/ITSpecialist111/ai_automation_suggester/1.3.2/Screenshot%202025-01-19%20082247-1.png" alt="Notification example" width="700"/>
  <br><em>AI suggestions delivered right inside Home&nbsp;Assistant</em>
</p>

You can also build custom dashboard cards to display suggestions using sensor attributes:

<p align="center">
  <img src="https://raw.githubusercontent.com/ITSpecialist111/ai_automation_suggester/1.3.2/Screenshot%202025-01-19%20083200.png" alt="Dashboard card example" width="700"/>
  <br><em>Dashboard showing human-readable description and extracted YAML block</em>
</p>

Here's an example of displaying suggestions on a dashboard:

<p align="center">
  <img src="https://raw.githubusercontent.com/ITSpecialist111/ai_automation_suggester/main/image.png" alt="Example Dashboard Implementation" width="700"/>
  <br><em>Example of a dashboard displaying AI-suggested automations</em>
</p>

---

## 🏆 Benefits

Leveraging the AI Automation Suggester provides several key benefits:

* **Time Saving:** Reduces the effort and guesswork involved in designing complex automations.
* **Context-Aware Suggestions:** Ideas consider your specific devices, areas, and current setup for realistic, tailored recommendations.
* **Model-Agnostic Flexibility:** Supports cloud and local AI models, letting you choose based on cost, privacy, and performance preferences.
* **Improved Usability:** Makes automation creation more accessible, even for users less familiar with YAML.
* **Dynamic Inspiration:** Provides fresh ideas as your home and devices change, keeping your automations evolving.
* **Enhanced Control:** Custom prompts, entity limits, and domain filters give you command over the suggestion generation process.
* **Safe to Try:** Suggestions are presented for review; nothing is automatically implemented without your explicit action.

---

## 📦 Features

* **Multi-Provider Support:** Connect to OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, Mistral, or Perplexity.
* **Customizable Prompts and Filters:** Tailor suggestions using system prompts, domain filters, and entity limits.
* **Randomized Entity Selection:** Prevent repetitive suggestions and discover new opportunities.
* **Context-Rich Insights:** Incorporates device and area information for smarter, more relevant ideas.
* **Persistent Notifications:** Receive suggestions directly in your Home Assistant interface.
* **Service Call Integration:** Manually trigger suggestions via the `ai_automation_suggester.generate_suggestions` service with full parameter control.
* **Diagnostics Sensors:** Monitor suggestion status and provider connection health.
* **Example Automations:** Includes built-in examples for new entity detection and weekly reviews.
* **Dashboard-Friendly Output:** Sensor attributes provide description and YAML blocks ready for Lovelace cards.

---

## 🛠️ Prerequisites

* **Home Assistant:** Version 2023.5 or later.
* **AI Provider Setup:** You will need access to an AI model.
    * For cloud providers (OpenAI, Anthropic, Google, Groq, Mistral, Perplexity), you’ll need API keys.
    * For local models (LocalAI, Ollama), ensure the local servers are running and accessible from Home Assistant.

---

## ⬇️ Installation

### HACS (Recommended)

1.  **Install HACS** if you haven't already.
2.  In HACS → **Integrations**, click the `+` button.
3.  Search for `AI Automation Suggester`.
4.  Select the integration and click **Download**.
5.  **Restart Home Assistant**.
6.  Go to Settings → Devices & Services → **+ Add Integration** and search for `AI Automation Suggester`.

### Manual Installation

1.  **Download** the contents of this repository.
2.  **Copy** the `custom_components/ai_automation_suggester` folder to your Home Assistant `custom_components` directory.
    ```bash
    <homeassistant_config_dir>/
    └── custom_components/
        └── ai_automation_suggester/
            ├── __init__.py
            └── ... (other files)
    ```
3.  **Restart Home Assistant**.
4.  Go to Settings → Devices & Services → **+ Add Integration** and search for `AI Automation Suggester`.

---

## ⚙️ Configuration

1.  Add the integration via the Home Assistant UI: Settings → Devices & Services → **+ Add Integration** → `AI Automation Suggester`.
2.  Follow the setup wizard:
    * **Select your AI Provider:** Choose from the dropdown list.
    * **Enter API Keys or Endpoint:** Provide the necessary credentials or local server URL based on your provider choice.
    * **Select Model:** Choose the specific model variant you wish to use.
    * **Set Max Tokens:** Define the maximum length for the AI's response (influences the length of suggestions).
    * **(Optional) Custom System Prompt:** Provide an initial prompt to guide the AI's overall perspective (e.g., "You are an expert in energy-saving automations for smart homes.").

You can adjust these settings later via the integration options in Settings → Devices & Services.

---

## ✍️ Usage

### Automatic Suggestions

The integration comes with example automations you can enable or adapt:

* **On New Entities:** Automatically generates suggestions when new entities are added to Home Assistant, helping you quickly integrate them.
* **Weekly Reviews:** Triggers a comprehensive analysis weekly (or at a custom interval you define in the automation), providing ongoing ideas.

Find and enable these examples in Settings → Automations.

### Manual Trigger

You can trigger the suggestion generation manually using the service call:

1.  Go to Developer Tools → **Services**.
2.  Select the service `ai_automation_suggester.generate_suggestions`.
3.  Call the service. You can pass parameters to customize the request:
    * `all_entities` (boolean, default: `false`): Set to `true` to consider all eligible entities, `false` to only consider entities added since the last successful run.
    * `domains` (list of strings, optional): Limit the analysis to entities within specific domains (e.g., `['light', 'sensor']`).
    * `entity_limit` (integer, optional): Set a maximum number of entities the AI should consider in this run. Useful for controlling prompt length and cost.
    * `custom_prompt` (string, optional): Add a specific instruction for this particular run (e.g., "Suggest security automations for doors and windows.").

### Dashboard Snippets

The main sensor (`sensor.ai_automation_suggestions_<provider_name>`) exposes useful attributes for display on dashboards. Replace `<provider_name>` with the name you gave the integration instance (e.g., `openai`, `ollama`).

* **Displaying the Description:**
    ```jinja
    {{ state_attr('sensor.ai_automation_suggestions_<provider_name>', 'description') }}
    ```
* **Displaying the YAML Block:**
    ```jinja
    {{ state_attr('sensor.ai_automation_suggestions_<provider_name>', 'yaml_block') }}
    ```
You can use Markdown cards or other card types to present this information cleanly in your Home Assistant dashboard.

---

## Customization and Advanced Usage

Beyond the basic configuration and service call parameters, you can further customize the integration's behavior:

### Random Entity Selection

By default, the integration uses randomized entity selection when `all_entities` is `true` (or the automatic weekly scan runs). This helps ensure variety in suggestions and prevents the AI from focusing only on the same initial set of entities.

### Domain Filtering

Use the `domains` parameter in the service call or your automation configuration to narrow the focus. This is very effective for getting suggestions for specific areas (e.g., only analyze `light` and `switch` entities in the `living_room` area - though area filtering is implicit based on the entities selected).

### Entity Limit

The `entity_limit` parameter is crucial for managing prompt size, particularly with models sensitive to input length or cost. Experiment to find a limit that provides good suggestions without hitting token limits or incurring excessive costs.

### Custom Prompts

The `custom_prompt` parameter allows you to be very specific about the type of suggestions you want for a particular run. Combine it with domain filtering for highly targeted results (e.g., `domains: ['climate'], custom_prompt: "Suggest automations to optimize heating/cooling based on occupancy and weather."`).

---

## Implementing Automations

1.  **Review Suggestions:** Check the persistent notifications or your dashboard card for new suggestions.
2.  **Copy YAML:** The suggestions are provided as ready-to-use Home Assistant YAML snippets. Copy the `yaml_block` content.
3.  **Add to Home Assistant:**
    * Paste the YAML into your `automations.yaml` file and restart Home Assistant.
    * Alternatively, use the Home Assistant Automation Editor UI: create a new automation, switch to YAML mode, and paste the snippet.
4.  **Adapt as Needed:** While the suggestions are tailored, you may need to make minor adjustments to triggers, conditions, delays, or actions to perfectly match your preferences and devices.
5.  **Test:** Always test new automations to ensure they function as expected before relying on them.

---

## Sensors

The integration provides two key sensors for monitoring:

* **AI Automation Suggestions Sensor:** `sensor.ai_automation_suggestions_<provider_name>`
    * State indicates the status (e.g., `idle`, `generating`, `suggestions_available`).
    * Attributes contain the latest suggestions, including `description`, `yaml_block`, and potentially other details depending on the AI provider's response format.
* **AI Provider Status Sensor:** `sensor.ai_provider_status_<provider_name>`
    * State indicates the connection health (e.g., `connected`, `error`, `unavailable`).
    * Attributes may provide additional details about the provider status or any errors encountered.

Monitor these sensors to ensure the integration is functioning correctly.

---

## ⚠️ Important Notes

* **Privacy Considerations:** If using cloud-based AI providers, be aware that entity data (names, states, attributes) is sent to their servers. Consider using local AI models (LocalAI, Ollama) for full data control if privacy is a major concern.
* **API Costs:** Some cloud providers charge for API usage based on tokens processed. Be mindful of this and use features like `entity_limit` and scheduled run frequency to manage potential costs. Monitor your provider's billing.
* **No Guarantees:** The AI's suggestions are based on patterns and logical inference from the data provided. They are not guaranteed to be perfect or the most efficient solution for every scenario. **Always review suggestions thoroughly before implementing them in your live system.**
* **AI Limitations:** Large language models can sometimes hallucinate or provide illogical suggestions. Use your judgment and knowledge of your home setup when reviewing.

---

## 🧩 Troubleshooting

| Symptom                                 | Check / Action                                                                                                                               |
|-----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| **No suggestions available** | - Verify API key is correct.<br>- Check the `AI Provider Status` sensor for errors.<br>- Check the Home Assistant logs for errors related to the integration.<br>- Try triggering the service manually with a small `entity_limit` and no domain filters.<br>- Ensure you have enough entities/devices for meaningful suggestions. |
| **AI Provider Status shows `error`** | - Inspect the Home Assistant log (`home-assistant.log`) for detailed error messages (look for `ai_automation_suggester` and `processing error`).<br>- Check your network connection to the provider's server (if cloud-based) or your local server.<br>- Confirm your API key is active and has permissions.<br>- Ensure your local AI server is running and accessible. |
| **Suggestion prompt is too long** | - Reduce the `entity_limit` parameter when triggering the service or configuring the automation.<br>- Use the `domains` filter to narrow the scope of entities analyzed.<br>- Shorten or simplify your `custom_prompt` if you are using one. |
| **Unintended startup suggestions** | - Review your Home Assistant automations and scripts to ensure none are configured to call `ai_automation_suggester.generate_suggestions` on startup or via events you didn't intend. |
| **Suggestions are repetitive** | - Ensure `all_entities` is used (e.g., in a weekly automation) and consider enabling randomized entity selection.<br>- Try different `custom_prompt` values to steer the AI in a new direction.<br>- Increase the `entity_limit` to give the AI more data points (if prompt length allows). |
| **Image links are broken in HACS/GitHub** | This has been addressed in this README version. Ensure the README file in your repository uses the corrected URLs provided. Clear your browser cache or wait for GitHub/HACS to refresh. |

If you encounter issues not covered here, please open an issue on the GitHub repository with details from your Home Assistant logs.

---

## Roadmap

Future planned features and improvements:

* **More Interactive Suggestions:** Explore feedback mechanisms to help the AI learn from user acceptance or rejection of suggestions.
* **One-Click Automation Creation:** Streamline the process from reviewing a suggestion to creating the automation in Home Assistant.
* **Expanded Localization:** Support for more languages through community contributions.
* **Improved Entity/Device Context:** Enhance the information provided to the AI about device types, capabilities, and relationships.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## Acknowledgments

* **Home Assistant Community:** For providing a robust and extensible smart home platform.
* **AI Providers:** OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, Mistral, and Perplexity for developing and providing access to powerful language models.
* **Contributors and Users:** For valuable feedback, testing, and contributions that help improve this project.

---

## Contributions

We welcome contributions! If you have ideas for new features, improvements, bug fixes, or translations, please feel free to open an issue or submit a pull request on the GitHub repository. Please follow standard development practices.

---

## Disclaimer

This is a custom component developed independently. It is not affiliated with, endorsed by, or officially supported by Home Assistant, Nabu Casa, or any of the mentioned AI providers. Use at your own discretion.

---

## 🤝 Support the Project

If you find this integration helpful and it saves you time and effort in automating your home, please consider supporting its development. Your support helps with maintenance, adding new features, and covering any potential costs associated with development and testing.

[<img src="https://img.shields.io/badge/Buy&nbsp;me&nbsp;a&nbsp;coffee-Support&nbsp;Dev-yellow?style=for-the-badge&logo=buy-me-a-coffee" alt="Buy Me A Coffee">](https://www.buymeacoffee.com/ITSpecialist)

---

## Additional Information

For further questions, discussions, or assistance, please visit the GitHub repository or the Home Assistant Community Forums thread (if one exists). Your feedback is highly valuable and helps shape the future direction of this project.

---

## ❓ FAQ

**1. How do I update the integration?**
If installed via HACS, update directly through the HACS interface in Home Assistant. If installed manually, download the latest version of the files from the repository and replace the existing ones in your `custom_components/ai_automation_suggester` folder, then restart Home Assistant.

**2. Can I use this integration without a cloud API key?**
Yes! You can use local AI models like those provided by LocalAI or Ollama running on your local network. This requires setting up and running the local AI server separately.

**3. Is my Home Assistant data safe?**
When using cloud-based AI providers, specific entity data (names, states, attributes) is sent to the provider's API for processing. Refer to the privacy policies of your chosen AI provider. Using local models keeps all data processing within your local network.

**4. I found a bug or have a feature request. What should I do?**
Please open an issue on the GitHub repository. Provide as much detail as possible, including steps to reproduce the bug, screenshots, and relevant logs. For feature requests, clearly describe the desired functionality and use case.

**5. Can I get suggestions in languages other than English?**
The quality of suggestions in other languages depends heavily on the AI model used. The integration structures the prompt in English, but you can experiment with custom prompts in other languages and see how the model responds. Community translations of the integration's UI and documentation are welcome!

---

With the AI Automation Suggester, you gain an AI-powered ally to help you unlock your home’s full potential. Instead of being overwhelmed by possibilities, receive thoughtful, context-aware suggestions that make your Home Assistant automations more impactful, efficient, and enjoyable.
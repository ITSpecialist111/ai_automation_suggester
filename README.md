# AI Automation Suggester

![Validate with hassfest](https://github.com/ITSpecialist111/AI_AUTOMATION_SUGGESTER/actions/workflows/hassfest.yaml/badge.svg)
![HACS Validation](https://github.com/ITSpecialist111/AI_AUTOMATION_SUGGESTER/actions/workflows/hacs.yaml/badge.svg)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/ITSpecialist111/AI_AUTOMATION_SUGGESTER)](https://github.com/ITSpecialist111/AI_AUTOMATION_SUGGESTER/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

An integration for Home Assistant that leverages AI models to analyze your entities and suggest potential automations. Now supporting multiple providers including OpenAI, Google, and local models for enhanced privacy.

---

## Support the Project

If you find this project helpful and would like to support its development, you can buy me a coffee!

<a href="https://buymeacoffee.com/itspecialist">
  <img src="https://camo.githubusercontent.com/7b8f7343bfc6e3c65c7901846637b603fd812f1a5f768d8b0572558bde859eb9/68747470733a2f2f63646e2e6275796d6561636f666665652e636f6d2f627574746f6e732f76322f64656661756c742d79656c6c6f772e706e67" alt="Buy Me A Coffee" width="200">
</a>

Your support is greatly appreciated and helps maintain and improve this project!

---

## Table of Contents

- [Background and Purpose](#background-and-purpose)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Installing via HACS (Recommended)](#installing-via-hacs-recommended)
  - [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Automatic Suggestions](#automatic-suggestions)
  - [Manual Trigger](#manual-trigger)
  - [Implementing Automations](#implementing-automations)
- [Sensors](#sensors)
- [Important Notes](#important-notes)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
  - [Future Enhancements](#future-enhancements)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Contributions](#contributions)
- [Disclaimer](#disclaimer)
- [Support the Project](#support-the-project)
- [Additional Information](#additional-information)
- [Frequently Asked Questions (FAQ)](#frequently-asked-questions-faq)

---

## Background and Purpose

Managing and automating devices in a smart home can be complex, especially as the number of devices grows. The **AI Automation Suggester** integration aims to simplify this process by leveraging AI models to analyze your entities in Home Assistant and provide intelligent automation suggestions.

---

## Features

- **Automatic Automation Suggestions**: Receive AI-generated automation ideas whenever new entities are added to your Home Assistant instance.
- **Manual Analysis Trigger**: Allows you to manually trigger the AI analysis at any time, providing flexibility and control.
- **Supports Multiple AI Providers**: Choose from a variety of AI models including OpenAI, Anthropic, Google, Groq, and local models like LocalAI and Ollama for privacy-focused users.
- **Customizable Prompts**: Override the default system prompt to tailor the suggestions to your specific needs.
- **Custom LLM Variants**: Users can select their preferred AI model variant, such as OpenAI's `gpt-3.5-turbo`.
- **Persistent Notifications**: Suggestions are delivered via Home Assistant's persistent notifications.
- **Sensor Entities**: Provides sensors to display the status of suggestions and provider connection status.
- **German Translation**: Added support for German language to reach a global audience.

---

## Prerequisites

- **Home Assistant**: Version 2023.5 or later.
- **API Keys**: Depending on the provider you choose, you may need API keys for OpenAI, Anthropic, Google, or Groq.
- **Local AI Setup**: For LocalAI and Ollama, you need to have the respective servers running on your local network.

---

## Installation

### Installing via HACS (Recommended)

The easiest way to install the **AI Automation Suggester** is through [HACS (Home Assistant Community Store)](https://hacs.xyz/).

#### **Step 1: Install HACS**

If you haven't installed HACS yet, follow the [official installation guide](https://hacs.xyz/docs/setup/download) to set it up.

#### **Step 2: Add Custom Repository**

1. Open your Home Assistant instance.
2. Navigate to **HACS** in the sidebar.
3. Click on the **Integrations** tab.
4. Click on the three-dot menu (⋮) in the top right corner.
5. Select **Custom repositories**.

   ![Custom Repositories](https://www.hacs.xyz/assets/images/screenshots/overview/menu/dark.png#only-dark)

6. In the **Add custom repository URL** field, enter:

   ```
   https://github.com/ITSpecialist111/ai_automation_suggester
   ```

7. In the **Category** dropdown, select **Integration**.
8. Click **Add**.

#### **Step 3: Install the Integration**

1. After adding the repository, search for **AI Automation Suggester** in HACS.
2. Click on the integration to view details.
3. Click **Download** to install the integration.

#### **Step 4: Restart Home Assistant**

After installation, you need to restart Home Assistant for the integration to be recognized.

1. Go to **Settings** > **System** > **Restart**.
2. Click **Restart** and wait for Home Assistant to restart.

### Manual Installation

If you prefer to install the integration manually, follow these steps:

1. **Download the Integration**

   - Clone or download the `ai_automation_suggester` repository from GitHub.

2. **Copy to Home Assistant**

   - Place the `ai_automation_suggester` directory inside the `custom_components` directory of your Home Assistant configuration folder.
   - Your directory structure should look like this:

     ```
     └── config/
         ├── configuration.yaml
         └── custom_components/
             └── ai_automation_suggester/
                 ├── __init__.py
                 ├── config_flow.py
                 ├── const.py
                 ├── coordinator.py
                 ├── manifest.json
                 ├── sensor.py
                 ├── services.yaml
                 ├── strings.json
                 └── translations/
                     ├── en.json
                     └── de.json
     ```

   - If the `custom_components` directory doesn't exist, create it.

3. **Restart Home Assistant**

   - After copying the files, restart Home Assistant to recognize the new integration.

---

## Configuration

### 1. **Add the Integration via Home Assistant UI**

- Navigate to **Settings** > **Devices & Services**.
- Click on **Add Integration**.
- Search for **AI Automation Suggester** and select it.

### 2. **Configure the Integration**

- **Provider**: Choose your preferred AI provider from the list (OpenAI, Anthropic, Google, Groq, LocalAI, Ollama, or Custom OpenAI).
- **API Key or Server Details**: Depending on the provider, you may need to enter an API key or provide server details for local models.
- **Model Selection**: Choose the AI model variant you wish to use (e.g., OpenAI's `gpt-3.5-turbo`).
- **Maximum Output Tokens**: Controls the length of the AI's response (default is 500). Increase if you need longer responses.
- **Custom System Prompt**: (Optional) Override the built-in system prompt with your own for more granular control.

### 3. **Obtain API Keys or Set Up Local AI Servers**

- **OpenAI**: Obtain an API key from the [OpenAI Dashboard](https://platform.openai.com/account/api-keys).
- **Anthropic**: Sign up for an API key at [Anthropic](https://www.anthropic.com/).
- **Google**: Get an API key from the [Google Cloud Console](https://console.cloud.google.com/).
- **Groq**: Register and obtain an API key from [Groq](https://groq.com/).
- **LocalAI/Ollama**: Set up the respective servers on your local network.

---

## Usage

### Automatic Suggestions

Once configured, the integration will automatically generate automation suggestions when new entities are added to your Home Assistant instance. Suggestions are sent as persistent notifications.

### Manual Trigger

You can manually trigger the AI analysis at any time:

- Go to **Developer Tools** > **Services**.
- Select `ai_automation_suggester.generate_suggestions` from the list.
- In the service data, you can specify:
  - **Provider Configuration**: If you have multiple providers configured, select which one to use.
  - **Custom Prompt**: Provide a custom prompt to tailor the suggestions.
- Click **Call Service**.

### Implementing Automations

- Review the suggestions provided in the persistent notifications.
- Implement the automations that suit your needs.

---

## Sensors

The integration provides two sensors:

- **AI Automation Suggestions**: Displays the status of suggestions and stores the latest suggestions in its attributes.
- **AI Provider Status**: Shows the connection status of the AI provider.

### Adding to Lovelace Dashboard

You can display the suggestions on your dashboard using an **Entities** card:

```yaml
type: entities
entities:
  - entity: sensor.ai_automation_suggestions
  - entity: sensor.ai_provider_status
```

---

## Important Notes

### **AI Provider API Key Security**

- **Do Not Share Your API Keys**: Keep your API keys confidential.
- **Revoking Compromised Keys**: If you suspect your API key has been compromised, revoke it immediately and generate a new one.

### **API Usage**

- **Costs**: Using AI provider APIs may incur costs. Monitor your usage in your provider's dashboard.
- **Usage Limits**: Set usage limits in your account to avoid unexpected charges.

### **Compatibility**

- **Home Assistant Version**: Ensure you are running Home Assistant version 2023.5 or later.
- **Local AI Models**: If using local models, ensure your local servers are correctly set up and accessible.

### **Data Privacy**

- **Data Sent to AI Providers**: The integration sends entity information to the selected AI provider's API for analysis.
- **User Consent**: By using this integration, you consent to this data being sent to the chosen AI provider.

---

## Troubleshooting

### **Common Issues**

1. **API Errors**

   - **Symptom**: Error messages related to AI provider APIs in notifications or logs.
   - **Solution**:
     - Verify your API key or server details are correct.
     - Ensure your API key has not expired or been revoked.
     - Check your account for any usage limits or account issues.
     - If using local models, ensure the server is running and accessible.

2. **Integration Not Showing Up**

   - **Symptom**: After installation, the integration doesn't appear in Home Assistant.
   - **Solution**:
     - Ensure the `ai_automation_suggester` directory is in the correct location.
     - Restart Home Assistant after adding the custom component.
     - Check the logs for any errors during startup.

3. **No Suggestions Generated**

   - **Symptom**: The integration doesn't generate any suggestions.
   - **Solution**:
     - Ensure new entities have been added to trigger automatic suggestions.
     - Manually trigger the service `ai_automation_suggester.generate_suggestions`.
     - Check if you have provided the necessary service data.
     - Review logs for any errors during the analysis.

4. **Dependency Issues**

   - **Symptom**: Errors related to missing dependencies or incorrect versions.
   - **Solution**:
     - Ensure all required libraries are installed.
     - Clear Home Assistant's cache by deleting the `deps` directory and restart.

### **Logging and Debugging**

- Enable debug logging for more detailed information:

  ```yaml
  logger:
    default: warning
    logs:
      custom_components.ai_automation_suggester: debug
  ```

- View logs under **Settings** > **System** > **Logs**.

---

## Roadmap

### **Future Enhancements**

1. **Interactive Suggestion Management**

   - **User Feedback Mechanism**: Allow users to provide feedback on suggestions to improve future results.
   - **Detailed Implementation Guides**: Provide step-by-step instructions for implementing suggested automations.

2. **Automated Automation Creation**

   - **One-Click Deployment**: Enable users to automatically implement suggested automations.
   - **Safety Measures**: Implement safeguards to ensure automations are created securely.

3. **Enhanced Localization**

   - **Additional Language Support**: Expand language support beyond English and German.
   - **Community Translations**: Collaborate with the community for translations and localization efforts.

4. **Community Integration Sharing**

   - **Platform for Sharing**: Allow users to share their automations and suggestions with the community.
   - **Moderation and Quality Control**: Implement mechanisms to ensure shared content is valuable and safe.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Home Assistant Community**: For providing an amazing platform and community support.
- **AI Providers**: OpenAI, Anthropic, Google, Groq, LocalAI, and Ollama for their AI models and APIs.

---

## Contributions

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/ITSpecialist111/ai_automation_suggester).

---

## Disclaimer

This integration is a third-party custom component and is not affiliated with or endorsed by Home Assistant or any of the AI providers.

---

## Support the Project

If you find this project helpful and would like to support its development, you can buy me a coffee!

<a href="https://buymeacoffee.com/itspecialist">
  <img src="https://camo.githubusercontent.com/7b8f7343bfc6e3c65c7901846637b603fd812f1a5f768d8b0572558bde859eb9/68747470733a2f2f63646e2e6275796d6561636f666665652e636f6d2f627574746f6e732f76322f64656661756c742d79656c6c6f772e706e67" alt="Buy Me A Coffee" width="200">
</a>

Your support is greatly appreciated and helps maintain and improve this project!

---

## Additional Information

For any questions or support, please open an issue on [GitHub](https://github.com/ITSpecialist111/ai_automation_suggester/issues).

---

## Frequently Asked Questions (FAQ)

### **1. How do I update the integration when a new version is released?**

- If installed via HACS, you can update the integration through the HACS interface:
  - Navigate to **HACS** > **Integrations**.
  - Find **AI Automation Suggester** in the list.
  - If an update is available, click **Update**.

### **2. Can I use this integration without an API key?**

- Yes, if you choose to use local AI models like LocalAI or Ollama, you do not need an external API key. However, you need to have the local servers set up and running.

### **3. Is my data safe when using this integration?**

- The integration sends entity information to the selected AI provider's API for analysis. If you use local models, your data remains within your local network. For cloud providers, you should review their privacy policies to understand how your data is handled.

### **4. I found a bug or have a feature request. How can I contribute?**

- Please open an issue on the [GitHub repository](https://github.com/ITSpecialist111/ai_automation_suggester/issues) with details about the bug or your feature request.

### **5. How can I add support for another language?**

- We welcome community contributions for translations. Please submit a pull request with the new language files in the `translations` directory.

### **6. How does the automatic suggestion generation work?**

- The integration monitors for new entities added to your Home Assistant instance. When new entities are detected, it automatically generates automation suggestions using the configured AI provider.

---

# End of README

Feel free to reach out if you need further assistance or have any other questions!
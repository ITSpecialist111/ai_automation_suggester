# AI Automation Suggester

![Validate with hassfest](https://github.com/ITSpecialist111/AI_AUTOMATION_SUGGESTER/actions/workflows/hassfest.yaml/badge.svg)
![HACS Validation](https://github.com/ITSpecialist111/AI_AUTOMATION_SUGGESTER/actions/workflows/hacs.yaml/badge.svg)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/ITSpecialist111/AI_AUTOMATION_SUGGESTER)](https://github.com/ITSpecialist111/AI_AUTOMATION_SUGGESTER/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

An integration for Home Assistant that uses OpenAI's GPT models to analyze your newly added entities and suggest potential automations.

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
- [Known Issues](#known-Issues)
- [Usage](#usage)
- [Important Notes](#important-notes)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
  - [Phase 1: Enhanced Entity Analysis](#phase-1-enhanced-entity-analysis)
  - [Phase 2: Interactive Suggestion Management](#phase-2-interactive-suggestion-management)
  - [Phase 3: Automated Automation Creation](#phase-3-automated-automation-creation)
  - [Future Enhancements](#future-enhancements)
  - [Contributing to the Roadmap](#contributing-to-the-roadmap)
  - [Timeline and Updates](#timeline-and-updates)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Contributions](#contributions)
- [Disclaimer](#disclaimer)
- [Support the Project](#support-the-project)

---

## Background and Purpose

Managing and automating devices in a smart home can be complex, especially as the number of devices grows. The **AI Automation Suggester** integration aims to simplify this process by leveraging OpenAI's GPT models to analyze newly added entities in your Home Assistant setup and provide intelligent automation suggestions.

---

## Features

- **Automatic Analysis**: Periodically scans for new entities and analyzes them using AI.
- **Automation Suggestions**: Provides clear and concise suggestions for potential automations.
- **Manual Trigger**: Allows you to manually trigger the AI analysis at any time.
- **Persistent Notifications**: Suggestions are delivered via Home Assistant's persistent notifications.
- **Sensor Entity**: Creates a sensor entity to display the status and suggestions.
- **Configurable Scan Frequency**: Set how often the integration scans for new entities.
- **Supports OpenAI GPT Models**: Uses OpenAI's GPT models for analysis.

---

## Prerequisites

- **Home Assistant**: Version 2023.5 or later.
- **OpenAI API Key**: You need an OpenAI API key to use the AI processing.

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

   - Place the `ai_suggester` directory inside the `custom_components` directory of your Home Assistant configuration folder.
   - Your directory structure should look like this:

     ```
     └── config/
         ├── configuration.yaml
         └── custom_components/
             └── ai_suggester/
                 ├── __init__.py
                 ├── config_flow.py
                 ├── const.py
                 ├── coordinator.py
                 ├── manifest.json
                 ├── sensor.py
                 ├── services.yaml
                 ├── strings.json
                 └── translations/
                     └── en.json
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

- **Scan Frequency (hours)**: Set how often (in hours) the integration scans for new entities. Default is `24` hours.
- **OpenAI API Key**: Enter your OpenAI API key.
- **Scan Frequency (hours)**: Scan Frequency (hours): Set how often (in hours) the integration scans for new entities. Default is 24 hours. Set to 0 to disable automatic scanning.
- **Initial Lag Time**: Initial Lag Time (minutes): Set a delay before initial suggestions are generated after setup. Default is 10 minutes.
- **OpenAI API Key**: Enter your OpenAI API key.

### 3. **Obtain an OpenAI API Key**

- Log in or sign up at the [OpenAI Platform](https://platform.openai.com/).
- Navigate to the [API Keys page](https://platform.openai.com/account/api-keys).
- Click on **Create new secret key** and copy the key.
- **Important**: Keep your API key secure and do not share it publicly.

---
## Known Issues

### 1. **Generic Suggestions on Initial Setup**

After the initial setup of the integration, the suggester will create a new persistent notification in Home Assistant. The initial suggestions are a generic list; however, you can manually trigger new suggestions that will look at your specific entities (or wait for the schedule to run).

You can manually trigger this by going to Developer Tools -> Actions -> AI Automation Suggester: Generate Suggestions -> Perform Action.

---

## Usage

### Video Tutorial via @BeardedTinker YouTube Channel **With Thanks!**

[![Watch the video](https://img.youtube.com/vi/-jnM33xQ3OQ/0.jpg)](https://www.youtube.com/watch?v=-jnM33xQ3OQ)


### 1. **Automatic Suggestions**

- The integration will automatically scan for new entities based on the configured scan frequency.
- When new entities are detected, it will analyze them and create automation suggestions.

### 2. **Manual Trigger**

- You can manually trigger the AI analysis at any time:
  - Go to **Developer Tools** > **Services**.
  - Select `ai_suggester.generate_suggestions` from the list.
  - Click **Call Service**.

### 3. **Viewing Suggestions**

- Suggestions are delivered via Home Assistant's persistent notifications.
- You can also view suggestions in the `sensor.ai_automation_suggestions` entity's attributes.

### 4. **Adding to Lovelace Dashboard**

- You can display the suggestions on your dashboard using an **Entities** card:

  ```yaml
  type: entities
  entities:
    - entity: sensor.ai_automation_suggestions
  ```

---

## Important Notes

### **OpenAI API Key Security**

- **Do Not Share Your API Key**: Keep your OpenAI API key confidential.
- **Revoking Compromised Keys**: If you suspect your API key has been compromised, revoke it immediately and generate a new one.

### **OpenAI API Usage**

- **Costs**: Using the OpenAI API may incur costs. Monitor your usage in the [OpenAI Dashboard](https://platform.openai.com/account/usage).
- **Usage Limits**: Set usage limits in your OpenAI account to avoid unexpected charges.

### **Compatibility**

- **OpenAI Python Library**: The integration requires `openai>=1.0.0`. This is specified in the `manifest.json`.
- **Home Assistant Version**: Ensure you are running Home Assistant version 2023.5 or later.

### **Data Privacy**

- **Data Sent to OpenAI**: The integration sends entity information to OpenAI's API for analysis.
- **User Consent**: By using this integration, you consent to this data being sent to OpenAI.

---

## Troubleshooting

### **Common Issues**

1. **OpenAI API Errors**

   - **Symptom**: Error messages related to OpenAI API in notifications or logs.
   - **Solution**:
     - Verify your OpenAI API key is correct.
     - Ensure your API key has not expired or been revoked.
     - Check your OpenAI account for any usage limits or account issues.

2. **Integration Not Showing Up**

   - **Symptom**: After installation, the integration doesn't appear in Home Assistant.
   - **Solution**:
     - Ensure the `ai_suggester` directory is in the correct location.
     - Restart Home Assistant after adding the custom component.
     - Check the logs for any errors during startup.

3. **No Suggestions Generated**

   - **Symptom**: The integration doesn't generate any suggestions.
   - **Solution**:
     - Manually trigger the service `ai_suggester.generate_suggestions`.
     - Check if there are any new entities to analyze.
     - Review logs for any errors during the analysis.

4. **Dependency Issues**

   - **Symptom**: Errors related to the OpenAI Python library version.
   - **Solution**:
     - Ensure that the OpenAI library version is `>=1.0.0`.
     - Clear Home Assistant's cache by deleting the `deps` directory and restart.

### **Logging and Debugging**

- Enable debug logging for more detailed information:

  ```yaml
  logger:
    default: warning
    logs:
      custom_components.ai_suggester: debug
      openai: debug
  ```

- View logs under **Settings** > **System** > **Logs**.

---

## Roadmap

We have an ambitious roadmap for the **AI Automation Suggester** integration to enhance its capabilities and provide even more value to Home Assistant users. Below is a list of planned features and improvements:

---

### **Phase 1: Enhanced Entity Analysis**

#### **1. Comprehensive Integration and Sensor Discovery**

- **Objective**: Extend the integration to analyze all available integrations, sensors, and automations in the user's Home Assistant setup.
- **Details**:
  - Collect detailed information about existing entities and their states.
  - Understand the relationships and dependencies between different entities.
  - Identify potential areas where automations could enhance the smart home experience.

#### **2. Advanced Automation Suggestions**

- **Objective**: Provide more powerful and personalized automation suggestions based on the comprehensive analysis.
- **Details**:
  - Use AI to detect patterns and usage habits.
  - Suggest automations that can improve efficiency, security, and convenience.
  - Include suggestions for energy savings, routine automation, and proactive alerts.

---

### **Phase 2: Interactive Suggestion Management**

#### **1. User Feedback Mechanism**

- **Objective**: Allow users to like or dislike the suggested automations to refine future suggestions.
- **Details**:
  - Implement a user interface where suggestions are listed with options to like or dislike.
  - Use feedback to improve the AI model's understanding of user preferences.
  - Store feedback securely and respect user privacy.

#### **2. Detailed Implementation Guides**

- **Objective**: For liked suggestions, provide concise and clear instructions on how to implement the automation.
- **Details**:
  - Break down the steps required to create the automation within Home Assistant.
  - Include code snippets, configuration examples, and screenshots where applicable.
  - Explain the desired outcome and how the automation enhances the user's smart home.

---

### **Phase 3: Automated Automation Creation**

#### **1. One-Click Automation Deployment**

- **Objective**: Enable users to automatically implement the suggested automations directly from the integration.
- **Details**:
  - Integrate with Home Assistant's automation editor to create automations programmatically.
  - Ensure automations are created following best practices and are easily editable by the user.
  - Provide options for users to review and confirm automations before deployment.

#### **2. Safety and Privacy Measures**

- **Objective**: Implement safeguards to ensure that automations are created securely and do not compromise the user's system.
- **Details**:
  - Include confirmation dialogs and summaries before making changes.
  - Ensure the integration adheres to Home Assistant's security guidelines.
  - Provide options to rollback changes if needed.

---

### **Future Enhancements**

#### **1. Local AI Processing**

- **Objective**: Develop local AI processing capabilities to reduce reliance on cloud services.
- **Details**:
  - Explore the use of local machine learning models compatible with Home Assistant's architecture.
  - Improve response times and reduce costs associated with cloud AI usage.
  - Enhance user privacy by keeping data processing local.

#### **2. Multi-Language Support**

- **Objective**: Support multiple languages to cater to a global user base.
- **Details**:
  - Translate the integration's interface and messages into other languages.
  - Ensure AI-generated suggestions are provided in the user's preferred language.
  - Collaborate with the community for translations and localization efforts.

#### **3. Community Integration Sharing**

- **Objective**: Allow users to share their automations and suggestions with the community.
- **Details**:
  - Create a platform or integrate with existing platforms to share and discover automations.
  - Enable users to benefit from community-driven ideas and solutions.
  - Implement moderation and quality control mechanisms.

---

## Contributing to the Roadmap

We welcome contributions and feedback from the community to help shape the future of the **AI Automation Suggester** integration. If you have ideas, feature requests, or would like to contribute to the development, please open an issue or submit a pull request on our [GitHub repository](https://github.com/ITSpecialist111/ai_automation_suggester).

---

## Timeline and Updates

We aim to implement these features progressively, with regular updates provided through the repository. Please check back frequently for the latest news and release notes.

---

**Note:** The features listed in this roadmap are subject to change based on feasibility, user feedback, and ongoing development efforts. Our goal is to provide the most valuable and user-friendly experience possible.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Home Assistant Community**: For providing an amazing platform and community support.
- **OpenAI**: For their powerful AI models and APIs.

---

## Contributions

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/ITSpecialist111/ai_automation_suggester).

---

## Disclaimer

This integration is a third-party custom component and is not affiliated with or endorsed by Home Assistant or OpenAI.

---

## Support the Project

If you find this project helpful and would like to support its development, you can buy me a coffee!

<a href="https://buymeacoffee.com/itspecialist">
  <img src="https://camo.githubusercontent.com/7b8f7343bfc6e3c65c7901846637b603fd812f1a5f768d8b0572558bde859eb9/68747470733a2f2f63646e2e6275796d6561636f666665652e636f6d2f627574746f6e732f76322f64656661756c742d79656c6c6f772e706e67" alt="Buy Me A Coffee" width="200">
</a>

Your support is greatly appreciated and helps maintain and improve this project!

---

# Additional Information

For any questions or support, please open an issue on [GitHub](https://github.com/ITSpecialist111/ai_automation_suggester/issues).

---

# Frequently Asked Questions (FAQ)

### **1. How do I update the integration when a new version is released?**

- If installed via HACS, you can update the integration through the HACS interface:
  - Navigate to **HACS** > **Integrations**.
  - Find **AI Automation Suggester** in the list.
  - If an update is available, click **Update**.

### **2. Can I use this integration without an OpenAI API key?**

- No, an OpenAI API key is required for the integration to function, as it uses OpenAI's GPT models to generate suggestions.

### **3. Is my data safe when using this integration?**

- The integration sends entity information to OpenAI's API for analysis. While OpenAI has robust privacy and security measures, you should review their [privacy policy](https://openai.com/policies/privacy-policy) to understand how your data is handled.

### **4. I found a bug or have a feature request. How can I contribute?**

- Please open an issue on the [GitHub repository](https://github.com/ITSpecialist111/ai_automation_suggester/issues) with details about the bug or your feature request.

### **5. Does the integration support local AI processing?**

- Currently, the integration only supports cloud-based AI processing using OpenAI's API. Local AI processing is planned for future updates.

---

# End of README

Feel free to reach out if you need further assistance or have any other questions!
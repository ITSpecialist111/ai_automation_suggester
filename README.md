# AI Automation Suggester

An integration for Home Assistant that uses OpenAI's GPT models to analyze your newly added entities and suggest potential automations.

---

## Table of Contents

- [Background and Purpose](#background-and-purpose)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Important Notes](#important-notes)
- [Troubleshooting](#troubleshooting)
- [License](#license)

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
- **Supports OpenAI GPT Models**: Uses OpenAI's `gpt-4o` model for analysis.
- **Local AI Option**: Placeholder for future local AI processing capabilities.

---

## Prerequisites

- **Home Assistant**: Version 2023.5 or later.
- **OpenAI API Key**: You need an OpenAI API key to use the cloud AI processing.

---

## Installation

### 1. **Download the Integration**

- Clone or download the `ai_automation_suggester` repository from GitHub.

### 2. **Copy to Home Assistant**

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

### 3. **Restart Home Assistant**

- After copying the files, restart Home Assistant to recognize the new integration.

---

## Configuration

### 1. **Add the Integration via Home Assistant UI**

- Navigate to **Settings** > **Devices & Services**.
- Click on **Add Integration**.
- Search for **AI Automation Suggester** and select it.

### 2. **Configure the Integration**

- **Scan Frequency (hours)**: Set how often (in hours) the integration scans for new entities. Default is `24` hours.
- **Use Local AI**: Option to use local AI processing (currently not implemented).
- **OpenAI API Key**: Enter your OpenAI API key. This is required if not using local AI.

### 3. **Obtain an OpenAI API Key**

- Log in or sign up at the [OpenAI Platform](https://platform.openai.com/).
- Navigate to the [API Keys page](https://platform.openai.com/account/api-keys).
- Click on **Create new secret key** and copy the key.
- **Important**: Keep your API key secure and do not share it publicly.

---

## Usage

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

### **Local AI Processing**

- **Not Yet Implemented**: The option to use local AI is currently a placeholder and not functional.
- **Future Updates**: Stay tuned for updates that may include local AI processing capabilities.

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

Example Outputs:


---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Home Assistant Community**: For providing an amazing platform and community support.
- **OpenAI**: For their powerful AI models and APIs.

---

## Contributions

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

---

## Disclaimer

This integration is a third-party custom component and is not affiliated with or endorsed by Home Assistant or OpenAI.


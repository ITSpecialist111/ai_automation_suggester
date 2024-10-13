# AI Automation Suggester

An AI-powered Home Assistant custom integration that suggests automations based on your entities. The Ultimate "Matt" mode.

## Features

- Scans entities periodically to detect new devices.
- Uses AI (e.g., OpenAI's GPT-4o) to generate automation suggestions.
- Provides a frontend interface for users to review and accept suggestions.
- Allows users to map placeholders to actual entities upon acceptance.
- Adds accepted automations to Home Assistant.

## Home Assistant Addon
[![Open your Home Assistant instance and add this add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=ai_suggester&repository_url=https%3A%2F%2Fgithub.com%2FITSpecialist111%2Fai_suggester)


## Manual Installation

1. Copy the `ai_suggester` folder to your `custom_components` directory.
2. Copy the `ai-suggester-card.js` file to `www/ai_suggester/` directory.
3. Restart Home Assistant.
4. In Home Assistant, navigate to **Configuration** > **Integrations**.
5. Click the **Add Integration** button and search for **AI Suggester**.
6. Follow the configuration wizard to set up the integration.

## Configuration

- **API Key**: Provide your OpenAI API key.
- **Scan Frequency**: Set how often (in hours) the integration scans for new entities.

## Usage

- After installation, the integration will scan for entities based on the configured frequency.
- When new suggestions are available, a persistent notification will appear.
- Add the **AI Suggester Card** to your Lovelace dashboard to view suggestions.

## Adding the Lovelace Card

1. In Home Assistant, go to **Overview** > **Edit Dashboard**.
2. Click **Add Card** and choose **Manual**.
3. Add the following configuration:
4. To Add another card:
   type: 'custom:ai-suggester-card'

```yaml
type: module
url: /local/ai_suggester/ai-suggester-card.js

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { applyHass } from 'custom-card-helpers'; // For hass object
@customElement('ai-automation-suggester-card')
export class AiAutomationSuggesterCard extends LitElement {
  static styles = css`
    :host {
      display: block;
    }
    ha-card {
      padding: 16px;
    }
    ul {
      list-style: none;
      padding: 0;
    }
    li {
      margin-bottom: 16px;
      border-bottom: 1px solid #eee;
      padding-bottom: 16px;
    }
    pre {
      background-color: #f0f0f0;
      padding: 10px;
      overflow-x: auto;
      border-radius: 4px;
      margin-top: 8px;
    }
    .details {
      display: none; /* Initially hidden */
    }
    .details[open] {
      display: block;
    }
    .error {
      color: red;
    }
  `;
  @property({ type: Object }) hass; // Home Assistant object
  @property({ type: Array }) suggestions = [];
  @state() loading = true;
  @state() error = null;
  connectedCallback() {
    super.connectedCallback();
    this.fetchData();
  }
  async fetchData() {
    this.loading = true;
    this.error = null;
    try {
      const response = await this.hass.callApi('GET', '/api/ai_automation_suggester/suggestions');
      this.suggestions = response;
    } catch (err) {
      this.error = err.message || 'Failed to fetch suggestions.';
    } finally {
      this.loading = false;
    }
  }
  toggleDetails(suggestion) {
    suggestion.showDetails = !suggestion.showDetails;
    this.requestUpdate(); // Ensure re-render
  }
  copyYaml(yaml) {
    navigator.clipboard.writeText(yaml);
    this.dispatchEvent(new CustomEvent('hass-notification', {
      detail: {
        type: 'info',
        message: 'YAML code copied to clipboard!',
      },
    }));
  }
  async handleSuggestionAction(suggestionId, action) {
    try {
      const response = await this.hass.callApi('POST', `/api/ai_automation_suggester/${action}/${suggestionId}`);
      if (response.success) {
        this.fetchData(); // Refresh suggestions after action
      } else {
        this.error = response.error || `Failed to ${action} suggestion.`;
      }
    } catch (err) {
      this.error = err.message || `Failed to ${action} suggestion.`;
    }
  }
  render() {
    return html`
      <ha-card>
        <div>
          <h2>AI Automation Suggestions</h2>
          ${this.loading
            ? html`<p>Loading suggestions...</p>`
            : this.error
              ? html`<p class="error">Error: ${this.error}</p>`
              : html`
                  <ul>
                    ${this.suggestions.map(suggestion => html`
                      <li>
                        <h3>${suggestion.title}</h3>
                        <p>${suggestion.shortDescription}</p>
                        <button @click="${() => this.toggleDetails(suggestion)}">Details</button>
                        <div class="details" ?open="${suggestion.showDetails}">
                          <p>${suggestion.detailedDescription}</p>
                          <pre><code class="language-yaml">${suggestion.yamlCode}</code></pre>
                          <button @click="${() => this.copyYaml(suggestion.yamlCode)}">Copy YAML</button>
                          <button @click="${() => this.handleSuggestionAction(suggestion.id, 'accept')}">Accept</button>
                          <button @click="${() => this.handleSuggestionAction(suggestion.id, 'decline')}">Decline</button>
                        </div>
                      </li>
                    `)}
                  </ul>
                `}
        </div>
      </ha-card>
    `;
  }
  setConfig(config) {
    // Optional: Handle any configuration options passed to the card
  }
  set hass(hass) {
    applyHass(this, hass);
  }
  get hass() {
    return this._hass;
  }
}
// Provide a fallback registration if the module is loaded directly
if (customElements.get('ai-automation-suggester-card') === undefined) {
  customElements.define('ai-automation-suggester-card', AiAutomationSuggesterCard);
}
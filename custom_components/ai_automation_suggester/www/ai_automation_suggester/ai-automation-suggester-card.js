import { LitElement, html, css } from "lit";

class AiAutomationSuggesterCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    suggestions: { state: true },
    loading: { state: true },
    error: { state: true },
  };

  static styles = css`
    :host {
      display: block;
    }
    ha-card {
      padding: 16px;
    }
    .toolbar {
      align-items: center;
      display: flex;
      justify-content: space-between;
      margin-bottom: 12px;
    }
    ul {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    li {
      border-top: 1px solid var(--divider-color, #ddd);
      padding: 12px 0;
    }
    li:first-child {
      border-top: 0;
    }
    pre {
      background: var(--code-editor-background-color, #f5f5f5);
      border-radius: 6px;
      overflow-x: auto;
      padding: 12px;
      white-space: pre-wrap;
    }
    .meta {
      color: var(--secondary-text-color);
      font-size: 0.9em;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }
    .error {
      color: var(--error-color, #b00020);
    }
  `;

  constructor() {
    super();
    this.suggestions = [];
    this.loading = true;
    this.error = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this.fetchData();
  }

  setConfig(config) {
    this.config = config;
  }

  async fetchData() {
    if (!this.hass) {
      return;
    }
    this.loading = true;
    this.error = null;
    try {
      this.suggestions = await this.hass.callApi("GET", "ai_automation_suggester/suggestions");
    } catch (err) {
      this.error = err.message || "Failed to fetch suggestions.";
    } finally {
      this.loading = false;
    }
  }

  async copyYaml(yaml) {
    await navigator.clipboard.writeText(yaml || "");
    this.dispatchEvent(
      new CustomEvent("hass-notification", {
        detail: { type: "info", message: "YAML copied to clipboard." },
        bubbles: true,
        composed: true,
      }),
    );
  }

  async handleSuggestionAction(suggestionId, action) {
    try {
      const response = await this.hass.callApi(
        "POST",
        `ai_automation_suggester/${action}/${suggestionId}`,
      );
      if (response.success) {
        await this.fetchData();
      } else {
        this.error = response.error || `Failed to ${action} suggestion.`;
      }
    } catch (err) {
      this.error = err.message || `Failed to ${action} suggestion.`;
    }
  }

  renderSuggestion(suggestion) {
    const yamlCode = suggestion.yamlCode || suggestion.yaml_block || "";
    return html`
      <li>
        <h3>${suggestion.title || "AI automation suggestion"}</h3>
        <p>${suggestion.shortDescription || suggestion.description || "No description returned."}</p>
        <p class="meta">
          ${suggestion.provider || "Unknown provider"} - ${suggestion.model || "Unknown model"} -
          ${suggestion.status || "new"}
        </p>
        ${yamlCode ? html`<pre><code>${yamlCode}</code></pre>` : html`<p class="meta">No YAML was returned.</p>`}
        ${(suggestion.warnings || []).length
          ? html`<p class="meta">${suggestion.warnings.join(" ")}</p>`
          : ""}
        <div class="actions">
          <ha-button @click=${() => this.copyYaml(yamlCode)} .disabled=${!yamlCode}>Copy YAML</ha-button>
          <ha-button @click=${() => this.handleSuggestionAction(suggestion.id, "accept")}>Accept</ha-button>
          <ha-button @click=${() => this.handleSuggestionAction(suggestion.id, "decline")}>Decline</ha-button>
          <ha-button @click=${() => this.handleSuggestionAction(suggestion.id, "dismiss")}>Dismiss</ha-button>
        </div>
      </li>
    `;
  }

  render() {
    return html`
      <ha-card>
        <div class="toolbar">
          <h2>AI Automation Suggestions</h2>
          <ha-button @click=${this.fetchData}>Refresh</ha-button>
        </div>
        ${this.loading
          ? html`<p>Loading suggestions...</p>`
          : this.error
            ? html`<p class="error">${this.error}</p>`
            : this.suggestions.length
              ? html`<ul>${this.suggestions.map((suggestion) => this.renderSuggestion(suggestion))}</ul>`
              : html`<p>No stored suggestions yet.</p>`}
      </ha-card>
    `;
  }
}

customElements.define("ai-automation-suggester-card", AiAutomationSuggesterCard);
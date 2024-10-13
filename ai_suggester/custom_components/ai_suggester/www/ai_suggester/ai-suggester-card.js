class AISuggesterCard extends HTMLElement {
  
  // Proper implementation of setConfig
  setConfig(config) {
    if (!config) {
      throw new Error("Invalid configuration");
    }
    this.config = config;
    this.renderCard();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.config) {
      this.renderCard();
    }
  }

  renderCard() {
    if (!this.content) {
      const card = document.createElement('ha-card');
      card.header = 'AI Automation Suggestions';
      this.content = document.createElement('div');
      this.content.style.padding = '16px';
      card.appendChild(this.content);
      this.appendChild(card);
    }
    if (this._hass) {
      this._hass.callApi('GET', 'ai_suggester/suggestions').then((suggestions) => {
        this.renderSuggestions(suggestions);
      });
    }
  }

  renderSuggestions(suggestions) {
    this.content.innerHTML = '';
    suggestions.suggestions.forEach((suggestion, index) => {
      const suggestionDiv = document.createElement('div');
      suggestionDiv.style.marginBottom = '16px';

      const description = document.createElement('p');
      description.textContent = suggestion.description;
      suggestionDiv.appendChild(description);

      const acceptButton = document.createElement('mwc-button');
      acceptButton.textContent = 'Accept';
      acceptButton.addEventListener('click', () => this.acceptSuggestion(index));
      suggestionDiv.appendChild(acceptButton);

      const rejectButton = document.createElement('mwc-button');
      rejectButton.textContent = 'Reject';
      rejectButton.addEventListener('click', () => this.rejectSuggestion(index));
      suggestionDiv.appendChild(rejectButton);

      this.content.appendChild(suggestionDiv);
    });
  }

  acceptSuggestion(index) {
    this._hass.callService('ai_suggester', 'accept_suggestion', { index });
  }

  rejectSuggestion(index) {
    this._hass.callService('ai_suggester', 'reject_suggestion', { index });
  }
}

customElements.define('ai-suggester-card', AISuggesterCard);

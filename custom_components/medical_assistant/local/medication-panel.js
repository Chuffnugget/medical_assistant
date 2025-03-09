/**
 * medication-panel.js
 *
 * This file defines a custom panel for the Medical Assistant integration.
 * Place this file in your config/www folder so that it is served at /local/medication-panel.js.
 */

import { LitElement, html, css } from 'lit-element';

class MedicationPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },
    };
  }

  constructor() {
    super();
    this.hass = {};
    this.narrow = false;
    this.route = {};
    // panel.config will contain any configuration from your manifest.
    this.panel = { config: {} };
  }

  static get styles() {
    return css`
      :host {
        display: block;
        padding: 16px;
        background-color: var(--secondary-background-color, #fafafa);
        color: var(--primary-text-color, #333);
      }
      h2 {
        margin: 0;
        padding: 0;
        color: var(--primary-text-color, #333);
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 16px;
      }
      th, td {
        border: 1px solid var(--primary-text-color, #333);
        padding: 8px;
        text-align: left;
      }
      th {
        background-color: var(--primary-background-color, #ddd);
      }
    `;
  }

  render() {
    // Simple rendering for testing.
    return html`
      <h2>Medication Panel</h2>
      <p>This panel has access to Home Assistant data.</p>
      <p>Number of entities: 
        ${this.hass && this.hass.states ? Object.keys(this.hass.states).length : 0}
      </p>
      <div>
        <h3>Panel Configuration</h3>
        <pre>${JSON.stringify(this.panel.config, null, 2)}</pre>
      </div>
      <div>
        <h3>Medications</h3>
        <!-- Placeholder: Insert your Excel-style grid or medication list here -->
        <p>(Your medication grid will appear here.)</p>
      </div>
    `;
  }
}

customElements.define('medication-panel', MedicationPanel);

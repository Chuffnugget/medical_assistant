/* medical_assistant_card.js - Custom Lovelace card for Medical Assistant Integration */
class MedicalAssistantCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity");
    }
    this.config = config;
  }

  set hass(hass) {
    if (!this.config) return;
    const entityId = this.config.entity;
    const stateObj = hass.states[entityId];
    if (!stateObj) {
      this.innerHTML = `<ha-card>Entity ${entityId} not found.</ha-card>`;
      return;
    }
    const medications = stateObj.attributes.medications || [];
    const now = new Date();
    const currentTime = now.toTimeString().substr(0, 8);
    // For simplicity, show medications whose scheduled time is up to the current time.
    const dueMedications = medications.filter(med => med.time <= currentTime);
    this.innerHTML = `
      <ha-card>
        <div class="card-header">Medications Due as of ${currentTime}</div>
        <div class="card-content">
          ${dueMedications.length > 0 
            ? dueMedications.map(med => `<div>${med.time} - ${med.name} (${med.strength})</div>`).join('')
            : '<div>No medications due.</div>'}
        </div>
      </ha-card>
    `;
  }

  getCardSize() {
    return 3;
  }
}

customElements.define("medical-assistant-card", MedicalAssistantCard);

import { LitElement, html, css } from 'lit';

class MedicationPanel extends LitElement {
  static get properties() {
    return {
      medications: { type: Array },
      showAddForm: { type: Boolean },
      editingMedication: { type: Object },
      newMedication: { type: Object },
    };
  }

  static get styles() {
    return css`
      h2, h3 {
        margin: 0.5rem 0;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
      }
      th, td {
        border: 1px solid var(--primary-text-color);
        padding: 8px;
        text-align: left;
      }
      th {
        background-color: var(--primary-background-color);
      }
      .button {
        margin: 4px;
        padding: 4px 8px;
        cursor: pointer;
        background-color: var(--primary-color);
        color: var(--text-primary-color);
        border: none;
        border-radius: 4px;
      }
      .form-row {
        margin: 0.5rem 0;
      }
      input {
        padding: 4px;
        margin-left: 0.5rem;
      }
      .form-container {
        background-color: var(--secondary-background-color);
        padding: 1rem;
        border-radius: 4px;
        margin-top: 1rem;
      }
    `;
  }

  constructor() {
    super();
    this.medications = [];
    this.showAddForm = false;
    this.editingMedication = null;
    this.newMedication = { day: '', time: '', name: '', strength: '' };
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchMedications();
  }

  async _fetchMedications() {
    try {
      // Assumes a WebSocket command "medical_assistant/get_schedule" is registered in the backend.
      const response = await this.hass.callWS({ type: "medical_assistant/get_schedule" });
      this.medications = response.schedule || [];
    } catch (err) {
      console.error("Error fetching medications", err);
      this.medications = [];
    }
  }

  _toggleAddForm() {
    this.showAddForm = !this.showAddForm;
  }

  async _addMedication() {
    // Call the Home Assistant service to add a medication.
    try {
      await this.hass.callService("medical_assistant", "add_medication", this.newMedication);
      this.newMedication = { day: '', time: '', name: '', strength: '' };
      this.showAddForm = false;
      this._fetchMedications();
    } catch (err) {
      console.error("Error adding medication", err);
    }
  }

  async _removeMedication(index) {
    try {
      await this.hass.callService("medical_assistant", "remove_medication", { index });
      this._fetchMedications();
    } catch (err) {
      console.error("Error removing medication", err);
    }
  }

  _editMedication(index) {
    // Create a copy of the medication so the form can be edited.
    this.editingMedication = { ...this.medications[index], index };
  }

  async _updateMedication() {
    try {
      await this.hass.callService("medical_assistant", "update_medication", this.editingMedication);
      this.editingMedication = null;
      this._fetchMedications();
    } catch (err) {
      console.error("Error updating medication", err);
    }
  }

  _cancelEdit() {
    this.editingMedication = null;
  }

  render() {
    return html`
      <h2>Medication Manager</h2>
      <button class="button" @click="${this._toggleAddForm}">
        ${this.showAddForm ? "Cancel Add" : "Add Medication"}
      </button>
      ${this.showAddForm ? this._renderAddForm() : ''}
      <table>
        <thead>
          <tr>
            <th>Day</th>
            <th>Time</th>
            <th>Name</th>
            <th>Strength</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${this.medications.map((med, index) => html`
            <tr>
              <td>${med.day}</td>
              <td>${med.time}</td>
              <td>${med.name}</td>
              <td>${med.strength}</td>
              <td>
                <button class="button" @click="${() => this._editMedication(index)}">Edit</button>
                <button class="button" @click="${() => this._removeMedication(index)}">Remove</button>
              </td>
            </tr>
          `)}
        </tbody>
      </table>
      ${this.editingMedication ? this._renderEditForm() : ''}
    `;
  }

  _renderAddForm() {
    return html`
      <div class="form-container">
        <h3>Add Medication</h3>
        <div class="form-row">
          <label>Day:
            <input type="text" .value="${this.newMedication.day}" placeholder="e.g. Monday"
              @input="${e => this.newMedication.day = e.target.value}">
          </label>
        </div>
        <div class="form-row">
          <label>Time:
            <input type="text" .value="${this.newMedication.time}" placeholder="HH:MM:SS"
              @input="${e => this.newMedication.time = e.target.value}">
          </label>
        </div>
        <div class="form-row">
          <label>Name:
            <input type="text" .value="${this.newMedication.name}" placeholder="Medication Name"
              @input="${e => this.newMedication.name = e.target.value}">
          </label>
        </div>
        <div class="form-row">
          <label>Strength:
            <input type="text" .value="${this.newMedication.strength}" placeholder="e.g. 100mg"
              @input="${e => this.newMedication.strength = e.target.value}">
          </label>
        </div>
        <button class="button" @click="${this._addMedication}">Add</button>
      </div>
    `;
  }

  _renderEditForm() {
    return html`
      <div class="form-container">
        <h3>Edit Medication</h3>
        <div class="form-row">
          <label>Day:
            <input type="text" .value="${this.editingMedication.day}" 
              @input="${e => this.editingMedication.day = e.target.value}">
          </label>
        </div>
        <div class="form-row">
          <label>Time:
            <input type="text" .value="${this.editingMedication.time}" 
              @input="${e => this.editingMedication.time = e.target.value}">
          </label>
        </div>
        <div class="form-row">
          <label>Name:
            <input type="text" .value="${this.editingMedication.name}" 
              @input="${e => this.editingMedication.name = e.target.value}">
          </label>
        </div>
        <div class="form-row">
          <label>Strength:
            <input type="text" .value="${this.editingMedication.strength}" 
              @input="${e => this.editingMedication.strength = e.target.value}">
          </label>
        </div>
        <button class="button" @click="${this._updateMedication}">Update</button>
        <button class="button" @click="${this._cancelEdit}">Cancel</button>
      </div>
    `;
  }
}

customElements.define("medication-panel", MedicationPanel);

class MedicalAssistantManagerCard extends HTMLElement {
  setConfig(config) {
    this.config = config;
    // Optionally allow a default day via configuration;
    // otherwise, default to today's weekday.
    this._days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    const today = new Date().toLocaleString("en-US", { weekday: "long" });
    this._selectedDay = config.default_day || today;
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  render() {
    if (!this._hass) return;

    const day = this._selectedDay;
    // Each day sensor is expected to have an entity_id like sensor.medical_assistant_monday_schedule.
    const sensorId = `sensor.medical_assistant_${day.toLowerCase()}_schedule`;
    const sensor = this._hass.states[sensorId];
    let medications = [];
    if (sensor && sensor.attributes && sensor.attributes.medications) {
      medications = sensor.attributes.medications;
    }

    // Build day selector options.
    const dayOptions = this._days
      .map(d => `<option value="${d}" ${d === day ? "selected" : ""}>${d}</option>`)
      .join("");

    // Build the list of medication entries.
    let medListHtml = "";
    medications.forEach((med, index) => {
      medListHtml += `
        <div class="med-entry" data-index="${index}">
          <span>${med.time} - ${med.name} (${med.strength})</span>
          <button class="edit-btn" data-index="${index}">Edit</button>
          <button class="delete-btn" data-index="${index}">Delete</button>
        </div>
      `;
    });

    // Hidden form for adding/editing a medication.
    const formHtml = `
      <div id="med-form" style="display:none; margin-top:10px;">
        <input id="med-time" type="text" placeholder="Time (HH:MM:SS)" /><br/>
        <input id="med-name" type="text" placeholder="Medication Name" /><br/>
        <input id="med-strength" type="text" placeholder="Strength" /><br/>
        <button id="save-med">Save</button>
        <button id="cancel-med">Cancel</button>
      </div>
    `;

    this.innerHTML = `
      <style>
        .med-entry { margin: 5px 0; }
        button { margin-left: 5px; }
      </style>
      <ha-card>
        <h2>Medical Assistant Manager</h2>
        <div>
          <label>Select Day: </label>
          <select id="day-select">
            ${dayOptions}
          </select>
        </div>
        <div id="med-list" style="margin-top:10px;">
          ${medListHtml}
        </div>
        <button id="add-med-btn" style="margin-top:10px;">Add Medication</button>
        ${formHtml}
      </ha-card>
    `;

    this._attachListeners();
  }

  _attachListeners() {
    // Day selector change.
    const daySelect = this.querySelector("#day-select");
    if (daySelect) {
      daySelect.addEventListener("change", (e) => {
        this._selectedDay = e.target.value;
        this.render();
      });
    }
    // Add medication button.
    const addBtn = this.querySelector("#add-med-btn");
    if (addBtn) {
      addBtn.addEventListener("click", () => {
        this._showForm("add");
      });
    }
    // Edit buttons.
    this.querySelectorAll(".edit-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const index = e.target.getAttribute("data-index");
        this._showForm("edit", index);
      });
    });
    // Delete buttons.
    this.querySelectorAll(".delete-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const index = e.target.getAttribute("data-index");
        this._deleteMedication(index);
      });
    });
    // Form buttons.
    const saveBtn = this.querySelector("#save-med");
    const cancelBtn = this.querySelector("#cancel-med");
    if (saveBtn) {
      saveBtn.addEventListener("click", () => {
        this._saveMedication();
      });
    }
    if (cancelBtn) {
      cancelBtn.addEventListener("click", () => {
        this._hideForm();
      });
    }
  }

  _showForm(mode, index = null) {
    // mode: "add" or "edit"
    this._formMode = mode;
    this._editIndex = index;
    const form = this.querySelector("#med-form");
    form.style.display = "block";
    // If editing, pre-fill form with the selected medication.
    const sensorId = `sensor.medical_assistant_${this._selectedDay.toLowerCase()}_schedule`;
    const sensor = this._hass.states[sensorId];
    let medications = [];
    if (sensor && sensor.attributes && sensor.attributes.medications) {
      medications = sensor.attributes.medications;
    }
    if (mode === "edit" && index !== null && medications[index]) {
      const med = medications[index];
      this.querySelector("#med-time").value = med.time;
      this.querySelector("#med-name").value = med.name;
      this.querySelector("#med-strength").value = med.strength;
    } else {
      this.querySelector("#med-time").value = "";
      this.querySelector("#med-name").value = "";
      this.querySelector("#med-strength").value = "";
    }
  }

  _hideForm() {
    const form = this.querySelector("#med-form");
    form.style.display = "none";
  }

  _saveMedication() {
    const time = this.querySelector("#med-time").value;
    const name = this.querySelector("#med-name").value;
    const strength = this.querySelector("#med-strength").value;
    if (this._formMode === "add") {
      // Call add_medication service.
      this._hass.callService("medical_assistant", "add_medication", {
        day: this._selectedDay,
        medication_name: name,
        strength: strength,
        time: time
      });
    } else if (this._formMode === "edit") {
      // Call update_medication service.
      this._hass.callService("medical_assistant", "update_medication", {
        day: this._selectedDay,
        index: parseInt(this._editIndex),
        medication_name: name,
        strength: strength,
        time: time
      });
    }
    this._hideForm();
  }

  _deleteMedication(index) {
    // Call remove_medication service.
    this._hass.callService("medical_assistant", "remove_medication", {
      day: this._selectedDay,
      index: parseInt(index)
    });
  }

  getCardSize() {
    return 5;
  }
}

customElements.define("medical-assistant-manager-card", MedicalAssistantManagerCard);

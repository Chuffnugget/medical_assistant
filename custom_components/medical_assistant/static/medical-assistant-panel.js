class MedicalAssistantPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) this._init();
  }

  set panel(panel) {
    this._panel = panel;
  }

  set route(route) {
    this._route = route;
  }

  set narrow(narrow) {
    this._narrow = narrow;
  }

  async _init() {
    this._initialized = true;
    this.attachShadow({ mode: "open" });

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; padding:16px; }
        .wrap { max-width: 1100px; margin: 0 auto; }
        .toolbar { display:flex; gap:12px; align-items:center; justify-content: space-between; margin-bottom: 12px; }
        .title { font-size: 20px; font-weight: 600; }
        button { cursor:pointer; padding:8px 12px; border-radius:10px; border:1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
        button.danger { border-color: var(--error-color); }
        table { width:100%; border-collapse: collapse; background: var(--card-background-color); border-radius: 14px; overflow:hidden; }
        th, td { padding: 10px 12px; border-bottom: 1px solid var(--divider-color); text-align:left; vertical-align: top; }
        th { font-weight: 600; }
        tr:last-child td { border-bottom: none; }
        input[type="text"], input[type="time"] { width: 100%; box-sizing: border-box; padding: 8px; border-radius: 10px; border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color); }
        .row-actions { display:flex; gap:8px; }
        .pill { display:inline-block; padding:2px 8px; border:1px solid var(--divider-color); border-radius:999px; margin:2px 4px 2px 0; font-size: 12px; opacity: 0.9; }
        dialog { border:none; border-radius:16px; padding:0; width:min(720px, 96vw); background: var(--card-background-color); color: var(--primary-text-color); }
        .dlg { padding: 16px; }
        .dlg h3 { margin: 0 0 12px; }
        .grid { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .grid .full { grid-column: 1 / -1; }
        .days { display:flex; flex-wrap: wrap; gap: 8px; }
        label.day { display:flex; gap:6px; align-items:center; padding:6px 10px; border:1px solid var(--divider-color); border-radius:999px; }
        .dlg-actions { display:flex; justify-content:flex-end; gap: 10px; padding: 0 16px 16px; }
        .hint { opacity: 0.8; font-size: 12px; margin-top: 6px; }
      </style>

      <div class="wrap">
        <div class="toolbar">
          <div class="title">Medication schedule</div>
          <div style="display:flex; gap:8px;">
            <button id="refresh">Refresh</button>
            <button id="add">Add medication</button>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th style="width: 18%;">Time</th>
              <th style="width: 22%;">Name</th>
              <th style="width: 18%;">Strength</th>
              <th style="width: 28%;">Days</th>
              <th style="width: 14%;">Actions</th>
            </tr>
          </thead>
          <tbody id="rows"></tbody>
        </table>

        <div class="hint">Admin-only panel. Entities update automatically from this schedule.</div>
      </div>

      <dialog id="dlg">
        <div class="dlg">
          <h3 id="dlgTitle">Medication</h3>
          <div class="grid">
            <div>
              <div>Time</div>
              <input id="f_time" type="time" />
            </div>
            <div>
              <div>Enabled</div>
              <label class="day"><input id="f_enabled" type="checkbox" /> Enabled</label>
            </div>
            <div>
              <div>Name</div>
              <input id="f_name" type="text" placeholder="e.g. Paracetamol" />
            </div>
            <div>
              <div>Strength</div>
              <input id="f_strength" type="text" placeholder="e.g. 500 mg" />
            </div>
            <div class="full">
              <div>Days of week</div>
              <div class="days" id="f_days"></div>
            </div>
            <div class="full">
              <div>Notes</div>
              <input id="f_notes" type="text" placeholder="optional" />
            </div>
          </div>
        </div>
        <div class="dlg-actions">
          <button id="cancel">Cancel</button>
          <button id="save">Save</button>
        </div>
      </dialog>
    `;

    this.shadowRoot.getElementById("refresh").addEventListener("click", () => this._load());
    this.shadowRoot.getElementById("add").addEventListener("click", () => this._openDialog({ mode: "create" }));
    this.shadowRoot.getElementById("cancel").addEventListener("click", () => this._closeDialog());
    this.shadowRoot.getElementById("save").addEventListener("click", () => this._saveDialog());

    this._buildDaysUI();
    await this._load();
  }

  _buildDaysUI() {
    const labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
    const daysWrap = this.shadowRoot.getElementById("f_days");
    daysWrap.innerHTML = "";
    labels.forEach((lab, i) => {
      const id = `day_${i}`;
      const el = document.createElement("label");
      el.className = "day";
      el.innerHTML = `<input type="checkbox" id="${id}" data-day="${i}" /> ${lab}`;
      daysWrap.appendChild(el);
    });
  }

  async _ws(msg) {
    return await this._hass.connection.sendMessagePromise(msg);
  }

  async _load() {
    const res = await this._ws({ type: "medical_assistant/list_meds" });
    this._meds = res.meds || [];
    this._renderRows();
  }

  _renderRows() {
    const rows = this.shadowRoot.getElementById("rows");
    rows.innerHTML = "";

    const dayName = (d) => ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d] || "?";

    this._meds.forEach((m) => {
      const tr = document.createElement("tr");

      const days = (m.days_of_week || []).map((d) => `<span class="pill">${dayName(d)}</span>`).join(" ");

      tr.innerHTML = `
        <td>${this._escape(m.time_local || "")}</td>
        <td>${this._escape(m.name || "")}</td>
        <td>${this._escape(m.strength || "")}</td>
        <td>${days}</td>
        <td>
          <div class="row-actions">
            <button data-act="edit">Edit</button>
            <button class="danger" data-act="del">Delete</button>
          </div>
        </td>
      `;

      tr.querySelector('[data-act="edit"]').addEventListener("click", () => this._openDialog({ mode: "edit", med: m }));
      tr.querySelector('[data-act="del"]').addEventListener("click", () => this._delete(m.id));

      rows.appendChild(tr);
    });

    if (this._meds.length === 0) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="5" style="opacity:0.8;">No medications yet. Click “Add medication”.</td>`;
      rows.appendChild(tr);
    }
  }

  _openDialog({ mode, med }) {
    this._dlgMode = mode;
    this._dlgMed = med || null;

    const dlg = this.shadowRoot.getElementById("dlg");
    this.shadowRoot.getElementById("dlgTitle").textContent =
      mode === "create" ? "Add medication" : "Edit medication";

    const setVal = (id, v) => (this.shadowRoot.getElementById(id).value = v ?? "");
    setVal("f_time", med?.time_local ?? "08:00");
    setVal("f_name", med?.name ?? "");
    setVal("f_strength", med?.strength ?? "");
    setVal("f_notes", med?.notes ?? "");

    this.shadowRoot.getElementById("f_enabled").checked = med ? !!med.enabled : true;

    // days
    const days = new Set(med?.days_of_week ?? [0,1,2,3,4,5,6]);
    this.shadowRoot.querySelectorAll("#f_days input[type=checkbox]").forEach((cb) => {
      cb.checked = days.has(Number(cb.dataset.day));
    });

    dlg.showModal();
  }

  _closeDialog() {
    const dlg = this.shadowRoot.getElementById("dlg");
    dlg.close();
  }

  async _saveDialog() {
    const time_local = this.shadowRoot.getElementById("f_time").value;
    const name = this.shadowRoot.getElementById("f_name").value.trim();
    const strength = this.shadowRoot.getElementById("f_strength").value.trim();
    const notes = this.shadowRoot.getElementById("f_notes").value.trim();
    const enabled = this.shadowRoot.getElementById("f_enabled").checked;

    const days_of_week = Array.from(this.shadowRoot.querySelectorAll("#f_days input[type=checkbox]"))
      .filter((cb) => cb.checked)
      .map((cb) => Number(cb.dataset.day));

    if (!time_local || !name || !strength || days_of_week.length === 0) {
      alert("Time, name, strength, and at least one day are required.");
      return;
    }

    if (this._dlgMode === "create") {
      await this._ws({
        type: "medical_assistant/create_med",
        time_local,
        name,
        strength,
        notes,
        enabled,
        days_of_week,
      });
    } else {
      await this._ws({
        type: "medical_assistant/update_med",
        id: this._dlgMed.id,
        time_local,
        name,
        strength,
        notes,
        enabled,
        days_of_week,
      });
    }

    this._closeDialog();
    await this._load();
  }

  async _delete(id) {
    if (!confirm("Delete this medication?")) return;
    await this._ws({ type: "medical_assistant/delete_med", id });
    await this._load();
  }

  _escape(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[c]));
  }
}

customElements.define("medical-assistant-panel", MedicalAssistantPanel);

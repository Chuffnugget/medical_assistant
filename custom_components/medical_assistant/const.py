from __future__ import annotations

DOMAIN = "medical_assistant"

PLATFORMS: list[str] = ["sensor"]

DEFAULT_TITLE = "Medical Assistant"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.data"

SIGNAL_DATA_UPDATED = f"{DOMAIN}_data_updated"

# Sidebar panel
PANEL_URL_PATH = "medications"
PANEL_TITLE = "Medications"
PANEL_ICON = "mdi:pill"

# MUST match your JS: customElements.define("medical-assistant-panel", ...)
PANEL_CUSTOM_ELEMENT = "medical-assistant-panel"

# Serve panel JS from the integration's static folder
STATIC_URL_BASE = f"/api/{DOMAIN}/static"
PANEL_JS_FILENAME = "medical-assistant-panel.js"
PANEL_MODULE_URL = f"{STATIC_URL_BASE}/{PANEL_JS_FILENAME}"

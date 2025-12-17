from __future__ import annotations

DOMAIN = "medical_assistant"

PLATFORMS: list[str] = ["sensor"]

DEFAULT_TITLE = "Medical Assistant"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.data"

SIGNAL_DATA_UPDATED = f"{DOMAIN}_data_updated"

PANEL_URL_PATH = "medical-assistant"
PANEL_TITLE = "Medical Assistant"
PANEL_ICON = "mdi:pill"

STATIC_URL_BASE = f"/api/{DOMAIN}/static"
PANEL_MODULE_URL = f"{STATIC_URL_BASE}/medical-assistant-panel.js"
PANEL_CUSTOM_ELEMENT = "medical-assistant-panel"

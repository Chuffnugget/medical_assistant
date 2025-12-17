from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.frontend import async_register_built_in_panel, async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    PLATFORMS,
    STORAGE_KEY,
    STORAGE_VERSION,
    SIGNAL_DATA_UPDATED,
    PANEL_URL_PATH,
    PANEL_TITLE,
    PANEL_ICON,
    PANEL_MODULE_URL,
    PANEL_CUSTOM_ELEMENT,
    STATIC_URL_BASE,
)
from .storage import MedicalAssistantStore
from .websocket_api import async_register_ws


@dataclass(slots=True)
class Runtime:
    store: MedicalAssistantStore
    unsub_interval: callable | None = None


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration (YAML not used, but required entrypoint)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def _ensure_static_and_panel(hass: HomeAssistant) -> None:
    """Register static path + sidebar panel once."""
    reg = hass.data[DOMAIN].setdefault("_runtime_global", {})
    if reg.get("panel_registered"):
        return

    # Serve /api/medical_assistant/static/* from ./static
    static_dir = Path(__file__).parent / "static"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL_BASE, str(static_dir), False)]
    )

    # Register a built-in panel that loads our custom element from module_url.
    # This follows the same pattern used by other integrations that embed panels.
    async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config={
            "_panel_custom": {
                "name": PANEL_CUSTOM_ELEMENT,
                "embed_iframe": False,
                "trust_external": False,
                "module_url": PANEL_MODULE_URL,
            }
        },
        require_admin=True,
    )

    reg["panel_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Medical Assistant from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    await _ensure_static_and_panel(hass)

    # Store + load data
    store = MedicalAssistantStore(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_load()

    # Register websocket commands once
    async_register_ws(hass)

    runtime = Runtime(store=store)
    hass.data[DOMAIN][entry.entry_id] = runtime

    # Periodic "tick" so countdown updates even if no edits happen
    async def _tick(_: object) -> None:
        async_dispatcher_send(hass, SIGNAL_DATA_UPDATED, entry.entry_id)

    runtime.unsub_interval = async_track_time_interval(hass, _tick, timedelta(seconds=30))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    runtime: Runtime = hass.data[DOMAIN].pop(entry.entry_id)

    if runtime.unsub_interval:
        runtime.unsub_interval()
        runtime.unsub_interval = None

    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # If this was the last entry, remove the panel
    if ok and not any(k for k in hass.data[DOMAIN].keys() if k != "_runtime_global"):
        async_remove_panel(hass, PANEL_URL_PATH)
        hass.data[DOMAIN].get("_runtime_global", {}).pop("panel_registered", None)

    return ok

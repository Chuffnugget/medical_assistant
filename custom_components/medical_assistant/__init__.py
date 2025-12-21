from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.frontend import async_register_built_in_panel, async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    PLATFORMS,
    STORAGE_VERSION,
    STORAGE_KEY,
    SIGNAL_DATA_UPDATED,
    PANEL_URL_PATH,
    PANEL_TITLE,
    PANEL_ICON,
    PANEL_CUSTOM_ELEMENT,
    PANEL_MODULE_URL,
    STATIC_URL_BASE,
)
from .storage import MedicalAssistantStore


@dataclass(slots=True)
class Runtime:
    store: MedicalAssistantStore
    unsub_interval: callable | None = None


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def _ensure_panel_and_static(hass: HomeAssistant) -> None:
    reg = hass.data[DOMAIN].setdefault("_reg", {})
    if reg.get("panel_registered"):
        return

    static_dir = Path(__file__).parent / "static"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL_BASE, str(static_dir), cache_headers=False)]
    )

    async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config={
            "_panel_custom": {
                "name": PANEL_CUSTOM_ELEMENT,
                "module_url": PANEL_MODULE_URL,
                "embed_iframe": False,
                "trust_external": False,
            }
        },
        require_admin=True,
    )

    reg["panel_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    await _ensure_panel_and_static(hass)

    store = MedicalAssistantStore(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_load()

    runtime = Runtime(store=store)
    hass.data[DOMAIN][entry.entry_id] = runtime

    # Import/register WS here to avoid config_flow import failures
    from .websocket_api import async_register_ws  # noqa: WPS433

    async_register_ws(hass)

    async def _tick(_: object) -> None:
        async_dispatcher_send(hass, SIGNAL_DATA_UPDATED, entry.entry_id)

    runtime.unsub_interval = async_track_time_interval(hass, _tick, timedelta(seconds=30))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime: Runtime = hass.data[DOMAIN].pop(entry.entry_id)

    if runtime.unsub_interval:
        runtime.unsub_interval()
        runtime.unsub_interval = None

    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if ok:
        # If last entry removed, remove the panel
        still_entries = any(k for k in hass.data[DOMAIN].keys() if k not in ("_reg",))
        if not still_entries:
            async_remove_panel(hass, PANEL_URL_PATH)
            hass.data[DOMAIN].get("_reg", {}).pop("panel_registered", None)

    return ok

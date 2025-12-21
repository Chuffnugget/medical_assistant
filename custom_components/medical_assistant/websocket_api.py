from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, callback
from homeassistant.components import websocket_api
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_DATA_UPDATED


def _runtime(hass: HomeAssistant) -> Any:
    domain_data = hass.data.get(DOMAIN, {})
    for k, v in domain_data.items():
        if k in ("_reg",):
            continue
        if hasattr(v, "store"):
            return v
    raise RuntimeError("Medical Assistant runtime not found")


def _entry_ids(hass: HomeAssistant) -> list[str]:
    domain_data = hass.data.get(DOMAIN, {})
    return [k for k in domain_data.keys() if k not in ("_reg",)]


def async_register_ws(hass: HomeAssistant) -> None:
    reg = hass.data.setdefault(DOMAIN, {}).setdefault("_reg", {})
    if reg.get("ws_registered"):
        return

    websocket_api.async_register_command(hass, ws_list_meds)
    websocket_api.async_register_command(hass, ws_create_med)
    websocket_api.async_register_command(hass, ws_update_med)
    websocket_api.async_register_command(hass, ws_delete_med)

    reg["ws_registered"] = True


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/list_meds",
    }
)
@callback
def ws_list_meds(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    rt = _runtime(hass)
    connection.send_result(msg["id"], {"meds": rt.store.list_meds()})


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/create_med",
        vol.Required("name"): str,
        vol.Required("strength"): str,
        vol.Required("time_local"): str,
        vol.Required("days_of_week"): [vol.All(int, vol.Range(min=0, max=6))],
        vol.Optional("enabled", default=True): bool,
        vol.Optional("notes", default=""): str,
    }
)
async def ws_create_med(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    rt = _runtime(hass)
    meds = rt.store.list_meds()

    med = {
        "id": uuid.uuid4().hex[:8],
        "name": msg["name"],
        "strength": msg["strength"],
        "time_local": msg["time_local"],
        "days_of_week": msg["days_of_week"],
        "enabled": msg.get("enabled", True),
        "notes": msg.get("notes", ""),
    }
    meds.append(med)

    await rt.store.set_meds(meds)

    for entry_id in _entry_ids(hass):
        async_dispatcher_send(hass, SIGNAL_DATA_UPDATED, entry_id)

    connection.send_result(msg["id"], {"ok": True, "med": med})


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/update_med",
        vol.Required("id"): str,
        vol.Optional("name"): str,
        vol.Optional("strength"): str,
        vol.Optional("time_local"): str,
        vol.Optional("days_of_week"): [vol.All(int, vol.Range(min=0, max=6))],
        vol.Optional("enabled"): bool,
        vol.Optional("notes"): str,
    }
)
async def ws_update_med(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    rt = _runtime(hass)
    meds = rt.store.list_meds()

    med_id = msg["id"]
    updated: dict[str, Any] | None = None

    for med in meds:
        if med.get("id") == med_id:
            for key in ("name", "strength", "time_local", "days_of_week", "enabled", "notes"):
                if key in msg:
                    med[key] = msg[key]
            updated = med
            break

    if updated is None:
        connection.send_error(msg["id"], "not_found", f"Medication id '{med_id}' not found")
        return

    await rt.store.set_meds(meds)

    for entry_id in _entry_ids(hass):
        async_dispatcher_send(hass, SIGNAL_DATA_UPDATED, entry_id)

    connection.send_result(msg["id"], {"ok": True, "med": updated})


@websocket_api.require_admin
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/delete_med",
        vol.Required("id"): str,
    }
)
async def ws_delete_med(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    rt = _runtime(hass)
    meds = rt.store.list_meds()

    med_id = msg["id"]
    new_meds = [m for m in meds if m.get("id") != med_id]

    if len(new_meds) == len(meds):
        connection.send_error(msg["id"], "not_found", f"Medication id '{med_id}' not found")
        return

    await rt.store.set_meds(new_meds)

    for entry_id in _entry_ids(hass):
        async_dispatcher_send(hass, SIGNAL_DATA_UPDATED, entry_id)

    connection.send_result(msg["id"], {"ok": True})

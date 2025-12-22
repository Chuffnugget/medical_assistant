from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, callback
from homeassistant.components import websocket_api
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import entity_registry as er

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


def _normalize_person_id(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    v = value.strip()
    return v or None


def _list_people(hass: HomeAssistant) -> list[dict[str, str]]:
    """Return person entities from the entity registry (more reliable than states)."""
    ent_reg = er.async_get(hass)

    people: list[dict[str, str]] = []
    for entry in ent_reg.entities.values():
        if entry.domain != "person":
            continue
        # Prefer the entity registry name; fall back to state friendly_name/name
        name = entry.name
        st = hass.states.get(entry.entity_id)
        if not name and st is not None:
            name = st.attributes.get("friendly_name") or st.name
        if not name:
            name = entry.entity_id

        people.append({"entity_id": entry.entity_id, "name": str(name)})

    people.sort(key=lambda p: p["name"].lower())
    return people


def async_register_ws(hass: HomeAssistant) -> None:
    reg = hass.data.setdefault(DOMAIN, {}).setdefault("_reg", {})
    if reg.get("ws_registered"):
        return

    websocket_api.async_register_command(hass, ws_list_people)
    websocket_api.async_register_command(hass, ws_list_meds)
    websocket_api.async_register_command(hass, ws_create_med)
    websocket_api.async_register_command(hass, ws_update_med)
    websocket_api.async_register_command(hass, ws_delete_med)

    reg["ws_registered"] = True


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_people"})
@callback
def ws_list_people(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    connection.send_result(msg["id"], {"people": _list_people(hass)})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_meds"})
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
        vol.Optional("person_entity_id"): vol.Any(None, str),
    }
)
async def ws_create_med(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    rt = _runtime(hass)
    meds = rt.store.list_meds()

    person_id = _normalize_person_id(msg.get("person_entity_id"))
    if person_id is not None and not person_id.startswith("person."):
        connection.send_error(msg["id"], "invalid_person", "person_entity_id must be a person.* entity_id")
        return

    med = {
        "id": uuid.uuid4().hex[:8],
        "name": msg["name"],
        "strength": msg["strength"],
        "time_local": msg["time_local"],
        "days_of_week": msg["days_of_week"],
        "enabled": msg.get("enabled", True),
        "notes": msg.get("notes", ""),
        "person_entity_id": person_id,
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
        vol.Optional("person_entity_id"): vol.Any(None, str),
    }
)
async def ws_update_med(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    rt = _runtime(hass)
    meds = rt.store.list_meds()

    med_id = msg["id"]
    updated: dict[str, Any] | None = None

    if "person_entity_id" in msg:
        person_id = _normalize_person_id(msg.get("person_entity_id"))
        if person_id is not None and not person_id.startswith("person."):
            connection.send_error(msg["id"], "invalid_person", "person_entity_id must be a person.* entity_id")
            return
    else:
        person_id = None

    for med in meds:
        if med.get("id") == med_id:
            for key in ("name", "strength", "time_local", "days_of_week", "enabled", "notes"):
                if key in msg:
                    med[key] = msg[key]
            if "person_entity_id" in msg:
                med["person_entity_id"] = _normalize_person_id(msg.get("person_entity_id"))
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

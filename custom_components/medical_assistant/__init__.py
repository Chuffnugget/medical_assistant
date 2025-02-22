"""__init__.py - Medical Assistant Integration for Home Assistant."""
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, DAYS_OF_WEEK

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up Medical Assistant via YAML (if any)."""
    hass.data.setdefault(DOMAIN, {})
    if "schedule" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["schedule"] = {day: [] for day in DAYS_OF_WEEK}
    return True

async def add_medication(call: ServiceCall):
    """Service to add a medication to the schedule."""
    day = call.data["day"]
    medication = {
        "name": call.data["medication_name"],
        "strength": call.data["strength"],
        "time": call.data["time"]  # expected format HH:MM:SS
    }
    _LOGGER.debug("Adding medication %s to %s", medication, day)
    hass = call.hass
    hass.data[DOMAIN]["schedule"][day].append(medication)
    hass.helpers.dispatcher.async_dispatcher_send(f"{DOMAIN}_update")

async def remove_medication(call: ServiceCall):
    """Service to remove a medication from the schedule by index."""
    day = call.data["day"]
    index = call.data["index"]
    hass = call.hass
    try:
        removed = hass.data[DOMAIN]["schedule"][day].pop(index)
        _LOGGER.debug("Removed medication %s from %s", removed, day)
        hass.helpers.dispatcher.async_dispatcher_send(f"{DOMAIN}_update")
    except IndexError:
        _LOGGER.error("Invalid index %d for day %s", index, day)

async def update_medication(call: ServiceCall):
    """Service to update an existing medication entry in the schedule."""
    day = call.data["day"]
    index = call.data["index"]
    hass = call.hass
    schedule_day = hass.data[DOMAIN]["schedule"].get(day, [])
    try:
        current = schedule_day[index]
        updated = {
            "name": call.data.get("medication_name", current["name"]),
            "strength": call.data.get("strength", current["strength"]),
            "time": call.data.get("time", current["time"]),
        }
        schedule_day[index] = updated
        _LOGGER.debug("Updated medication at index %d for %s: %s", index, day, updated)
        hass.helpers.dispatcher.async_dispatcher_send(f"{DOMAIN}_update")
    except IndexError:
        _LOGGER.error("Invalid index %d for day %s", index, day)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Medical Assistant from a config entry."""
    _LOGGER.debug("Setting up Medical Assistant with entry: %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    if "schedule" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["schedule"] = {day: [] for day in DAYS_OF_WEEK}

    # Register services
    hass.services.async_register(DOMAIN, "add_medication", add_medication)
    hass.services.async_register(DOMAIN, "remove_medication", remove_medication)
    hass.services.async_register(DOMAIN, "update_medication", update_medication)

    # Forward the sensor platform setup (awaiting the helper)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload Medical Assistant config entry."""
    hass.services.async_remove(DOMAIN, "add_medication")
    hass.services.async_remove(DOMAIN, "remove_medication")
    hass.services.async_remove(DOMAIN, "update_medication")
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True

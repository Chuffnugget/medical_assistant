"""__init__.py - Medical Assistant Integration for Home Assistant."""
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, DAYS_OF_WEEK

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Medical Assistant integration via YAML (if any)."""
    hass.data.setdefault(DOMAIN, {})
    # Initialize the medication schedule with empty lists for each day
    if "schedule" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["schedule"] = {day: [] for day in DAYS_OF_WEEK}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Medical Assistant from a config entry."""
    _LOGGER.debug("Setting up Medical Assistant with entry: %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    if "schedule" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["schedule"] = {day: [] for day in DAYS_OF_WEEK}

    # -------------------------------
    # Register services to modify the schedule
    # -------------------------------

    async def add_medication(call: ServiceCall):
        """Service to add a medication to the schedule."""
        day = call.data["day"]
        medication = {
            "name": call.data["medication_name"],
            "strength": call.data["strength"],
            "time": call.data["time"]  # expected format HH:MM:SS
        }
        _LOGGER.debug("Adding medication %s to %s", medication, day)
        hass.data[DOMAIN]["schedule"][day].append(medication)
        # Trigger an update so any sensors refresh their state
        hass.helpers.dispatcher.async_dispatcher_send(f"{DOMAIN}_update")

    async def remove_medication(call: ServiceCall):
        """Service to remove a medication from the schedule by index."""
        day = call.data["day"]
        index = call.data["index"]
        try:
            removed = hass.data[DOMAIN]["schedule"][day].pop(index)
            _LOGGER.debug("Removed medication %s from %s", removed, day)
            hass.helpers.dispatcher.async_dispatcher_send(f"{DOMAIN}_update")
        except IndexError:
            _LOGGER.error("Invalid index %d for day %s", index, day)

    async def update_medication(call: ServiceCall):
        """Service to update a medication entry in the schedule."""
        day = call.data["day"]
        index = call.data["index"]
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

    # Service schemas
    ADD_MEDICATION_SCHEMA = vol.Schema({
        vol.Required("day"): vol.In(DAYS_OF_WEEK),
        vol.Required("medication_name"): str,
        vol.Required("strength"): str,
        vol.Required("time"): str,  # Expected format HH:MM:SS
    })
    REMOVE_MEDICATION_SCHEMA = vol.Schema({
        vol.Required("day"): vol.In(DAYS_OF_WEEK),
        vol.Required("index"): int,
    })
    UPDATE_MEDICATION_SCHEMA = vol.Schema({
        vol.Required("day"): vol.In(DAYS_OF_WEEK),
        vol.Required("index"): int,
        vol.Optional("medication_name"): str,
        vol.Optional("strength"): str,
        vol.Optional("time"): str,
    })

    hass.services.async_register(DOMAIN, "add_medication", add_medication, schema=ADD_MEDICATION_SCHEMA)
    hass.services.async_register(DOMAIN, "remove_medication", remove_medication, schema=REMOVE_MEDICATION_SCHEMA)
    hass.services.async_register(DOMAIN, "update_medication", update_medication, schema=UPDATE_MEDICATION_SCHEMA)

    # Forward setup to sensor platform (which will create one sensor per day)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload Medical Assistant config entry."""
    hass.services.async_remove(DOMAIN, "add_medication")
    hass.services.async_remove(DOMAIN, "remove_medication")
    hass.services.async_remove(DOMAIN, "update_medication")
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True

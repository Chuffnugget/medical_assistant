"""__init__.py - Medical Assistant Integration for Home Assistant."""
import logging
import os
import shutil
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, DAYS_OF_WEEK

_LOGGER = logging.getLogger(__name__)

def deploy_panel_file(hass: HomeAssistant) -> None:
    """Deploy medication-panel.js to the Home Assistant www folder.
    
    This function checks if the source file (in the integration's local folder)
    exists and compares its size to the file in config/www. If the destination
    is missing or its size differs, the file is copied.
    """
    # Source file location: custom_components/medical_assistant/local/medication-panel.js
    integration_dir = os.path.dirname(__file__)
    src_path = os.path.join(integration_dir, "local", "medication-panel.js")
    # Destination file location: config/www/medication-panel.js
    dst_path = hass.config.path("www", "medication-panel.js")

    if not os.path.exists(src_path):
        _LOGGER.error("Source file not found at %s", src_path)
        return

    # If destination doesn't exist, copy the file.
    if not os.path.exists(dst_path):
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy(src_path, dst_path)
        _LOGGER.info("Copied panel file to %s", dst_path)
        return

    # Compare file sizes (as a proxy for file changes)
    try:
        src_size = os.path.getsize(src_path)
        dst_size = os.path.getsize(dst_path)
    except Exception as e:
        _LOGGER.error("Error getting file sizes: %s", e)
        return

    if src_size != dst_size:
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy(src_path, dst_path)
        _LOGGER.info("Updated panel file in %s due to size mismatch (src: %s bytes, dst: %s bytes)", dst_path, src_size, dst_size)
    else:
        _LOGGER.info("Panel file in %s is up-to-date", dst_path)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up Medical Assistant via YAML (if any)."""
    hass.data.setdefault(DOMAIN, {})
    if "schedule" not in hass.data[DOMAIN]:
        # Global schedule as a list of medication records.
        hass.data[DOMAIN]["schedule"] = []
    
    # Use Home Assistant's executor to run the file deployment (to avoid blocking)
    await hass.async_add_executor_job(deploy_panel_file, hass)
    
    return True

async def add_medication(call: ServiceCall):
    """Service to add a medication to the schedule."""
    # We still accept a day to know when the medication should occur.
    medication = {
        "day": call.data["day"],
        "name": call.data["medication_name"],
        "strength": call.data["strength"],
        "time": call.data["time"]  # expected format HH:MM:SS
    }
    _LOGGER.debug("Adding medication %s", medication)
    hass = call.hass
    hass.data[DOMAIN]["schedule"].append(medication)
    hass.helpers.dispatcher.async_dispatcher_send(f"{DOMAIN}_update")

async def remove_medication(call: ServiceCall):
    """Service to remove a medication from the schedule by its index."""
    index = call.data["index"]
    hass = call.hass
    try:
        removed = hass.data[DOMAIN]["schedule"].pop(index)
        _LOGGER.debug("Removed medication %s", removed)
        hass.helpers.dispatcher.async_dispatcher_send(f"{DOMAIN}_update")
    except IndexError:
        _LOGGER.error("Invalid index %d", index)

async def update_medication(call: ServiceCall):
    """Service to update an existing medication entry in the schedule."""
    index = call.data["index"]
    hass = call.hass
    schedule = hass.data[DOMAIN]["schedule"]
    try:
        current = schedule[index]
        updated = {
            "day": call.data.get("day", current.get("day")),
            "name": call.data.get("medication_name", current.get("name")),
            "strength": call.data.get("strength", current.get("strength")),
            "time": call.data.get("time", current.get("time")),
        }
        schedule[index] = updated
        _LOGGER.debug("Updated medication at index %d: %s", index, updated)
        hass.helpers.dispatcher.async_dispatcher_send(f"{DOMAIN}_update")
    except IndexError:
        _LOGGER.error("Invalid index %d", index)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Medical Assistant from a config entry."""
    _LOGGER.debug("Setting up Medical Assistant with entry: %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    if "schedule" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["schedule"] = []

    # Register services
    hass.services.async_register(DOMAIN, "add_medication", add_medication)
    hass.services.async_register(DOMAIN, "remove_medication", remove_medication)
    hass.services.async_register(DOMAIN, "update_medication", update_medication)

    # Forward the sensor platform setup
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload Medical Assistant config entry."""
    hass.services.async_remove(DOMAIN, "add_medication")
    hass.services.async_remove(DOMAIN, "remove_medication")
    hass.services.async_remove(DOMAIN, "update_medication")
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True

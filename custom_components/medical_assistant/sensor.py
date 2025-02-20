"""sensor.py - Sensor platform for Medical Assistant integration."""
import logging
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, DAYS_OF_WEEK

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensor entities for each day of the week."""
    sensors = [MedicationScheduleSensor(day, hass) for day in DAYS_OF_WEEK]
    async_add_entities(sensors, update_before_add=True)

class MedicationScheduleSensor(Entity):
    """Representation of a medication schedule sensor for a specific day."""

    def __init__(self, day, hass):
        """Initialize the sensor."""
        self._day = day
        self._hass = hass
        self._unsubscribe_dispatcher = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Medical Assistant {self._day} Schedule"

    @property
    def unique_id(self):
        """Return a unique id for the sensor."""
        return f"medical_assistant_{self._day.lower()}"

    @property
    def state(self):
        """Return the state of the sensor: number of medications scheduled."""
        schedule = self._hass.data[DOMAIN]["schedule"].get(self._day, [])
        return len(schedule)

    @property
    def extra_state_attributes(self):
        """Return the sensor attributes including full medication list."""
        schedule = self._hass.data[DOMAIN]["schedule"].get(self._day, [])
        return {"medications": schedule}

    async def async_update(self):
        """No polling needed; state is stored in hass.data."""
        pass

    async def async_added_to_hass(self):
        """Subscribe to schedule updates."""
        self._unsubscribe_dispatcher = async_dispatcher_connect(
            self._hass, f"{DOMAIN}_update", self._handle_update
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from updates."""
        if self._unsubscribe_dispatcher:
            self._unsubscribe_dispatcher()
            self._unsubscribe_dispatcher = None

    def _handle_update(self):
        """Handle updates by scheduling a state update."""
        self.schedule_update_ha_state(True)

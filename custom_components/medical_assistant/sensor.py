"""sensor.py - Sensor platform for Medical Assistant integration."""
import logging
from datetime import datetime
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, DAYS_OF_WEEK

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensor entities for each day of the week and the next medication sensor."""
    sensors = [MedicationScheduleSensor(day, hass) for day in DAYS_OF_WEEK]
    sensors.append(NextMedicationSensor(hass))
    async_add_entities(sensors, update_before_add=True)

class MedicationScheduleSensor(Entity):
    """Representation of a medication schedule sensor for a specific day."""
    def __init__(self, day, hass):
        self._day = day
        self._hass = hass
        self._unsubscribe_dispatcher = None

    @property
    def name(self):
        return f"Medical Assistant {self._day} Schedule"

    @property
    def unique_id(self):
        return f"medical_assistant_{self._day.lower()}_schedule"

    @property
    def state(self):
        """State is the number of medications scheduled for the day."""
        schedule = self._hass.data[DOMAIN]["schedule"].get(self._day, [])
        return len(schedule)

    @property
    def extra_state_attributes(self):
        schedule = self._hass.data[DOMAIN]["schedule"].get(self._day, [])
        return {"medications": schedule}

    async def async_update(self):
        pass

    async def async_added_to_hass(self):
        self._unsubscribe_dispatcher = async_dispatcher_connect(
            self._hass, f"{DOMAIN}_update", self._handle_update
        )

    async def async_will_remove_from_hass(self):
        if self._unsubscribe_dispatcher:
            self._unsubscribe_dispatcher()
            self._unsubscribe_dispatcher = None

    def _handle_update(self):
        self.schedule_update_ha_state(True)

class NextMedicationSensor(Entity):
    """Representation of the sensor that shows the next medication to take."""
    def __init__(self, hass):
        self._hass = hass
        self._unsubscribe_dispatcher = None

    @property
    def name(self):
        return "Medical Assistant Next Medication"

    @property
    def unique_id(self):
        return "medical_assistant_next_medication"

    @property
    def state(self):
        """Compute and return the next medication as a formatted string."""
        schedule = self._hass.data[DOMAIN]["schedule"]
        next_day, next_med = self._get_next_medication(schedule)
        if next_med:
            med_time = next_med.get("time")
            med_name = next_med.get("name")
            med_strength = next_med.get("strength")
            return f"{next_day} {med_time} {med_name} ({med_strength})"
        return "No medication scheduled"

    @property
    def extra_state_attributes(self):
        schedule = self._hass.data[DOMAIN]["schedule"]
        next_day, next_med = self._get_next_medication(schedule)
        if next_med:
            return {
                "day": next_day,
                "time": next_med.get("time"),
                "name": next_med.get("name"),
                "strength": next_med.get("strength")
            }
        return {}

    async def async_update(self):
        pass

    async def async_added_to_hass(self):
        self._unsubscribe_dispatcher = async_dispatcher_connect(
            self._hass, f"{DOMAIN}_update", self._handle_update
        )

    async def async_will_remove_from_hass(self):
        if self._unsubscribe_dispatcher:
            self._unsubscribe_dispatcher()
            self._unsubscribe_dispatcher = None

    def _handle_update(self):
        self.schedule_update_ha_state(True)

    def _get_next_medication(self, schedule):
        """Determine the next medication based on current day/time.
        
        1. Check the current day for any medications with a time later than now.
        2. If none found, check subsequent days in order.
        3. Return a tuple (day, medication dict) or (None, None) if none found.
        """
        now = datetime.now()
        current_day = now.strftime("%A")
        current_time = now.time()
        # First, check today's medications.
        meds_today = schedule.get(current_day, [])
        upcoming = []
        for med in meds_today:
            try:
                med_time = datetime.strptime(med.get("time"), "%H:%M:%S").time()
                if med_time > current_time:
                    upcoming.append((med_time, med))
            except Exception as e:
                _LOGGER.error("Error parsing time for medication %s: %s", med, e)
        if upcoming:
            upcoming.sort(key=lambda x: x[0])
            return current_day, upcoming[0][1]
        # Check subsequent days.
        current_index = DAYS_OF_WEEK.index(current_day)
        for i in range(1, len(DAYS_OF_WEEK)):
            day = DAYS_OF_WEEK[(current_index + i) % len(DAYS_OF_WEEK)]
            meds = schedule.get(day, [])
            if meds:
                try:
                    meds_sorted = sorted(
                        meds,
                        key=lambda m: datetime.strptime(m.get("time"), "%H:%M:%S").time()
                    )
                    return day, meds_sorted[0]
                except Exception as e:
                    _LOGGER.error("Error parsing time for day %s: %s", day, e)
        return None, None

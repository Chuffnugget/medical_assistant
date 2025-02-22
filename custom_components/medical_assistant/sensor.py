"""sensor.py - Sensor platform for Medical Assistant integration."""
import logging
from datetime import datetime, timedelta
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
        """Return a formatted string for the next medication.
        
        If the next medication is within 12 hours, show relative time (e.g. "30 minutes until Aspirin (100mg)").
        Otherwise, show the exact scheduled time with the medication name.
        """
        schedule = self._hass.data[DOMAIN]["schedule"]
        next_day, next_med, med_dt = self._get_next_medication(schedule)
        if next_med and med_dt:
            now = datetime.now()
            delta = med_dt - now
            seconds = delta.total_seconds()
            if seconds < 12 * 3600:
                # Show relative time
                minutes = int(seconds // 60)
                hours = int(seconds // 3600)
                if hours > 0:
                    rel_time = f"{hours} hour{'s' if hours != 1 else ''}"
                else:
                    rel_time = f"{minutes} minute{'s' if minutes != 1 else ''}"
                return f"{rel_time} until {next_med.get('name')} ({next_med.get('strength')})"
            else:
                # Show timestamp and medication info
                time_str = med_dt.strftime("%H:%M")
                return f"{next_day} {time_str} - {next_med.get('name')} ({next_med.get('strength')})"
        return "No medication scheduled"

    @property
    def extra_state_attributes(self):
        schedule = self._hass.data[DOMAIN]["schedule"]
        next_day, next_med, med_dt = self._get_next_medication(schedule)
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
        """Determine the next medication based on the current day/time.
        
        Returns a tuple (day, medication dict, medication_datetime) or (None, None, None).
        """
        now = datetime.now()
        current_day = now.strftime("%A")
        current_time = now.time()
        # Check today's medications
        meds_today = schedule.get(current_day, [])
        upcoming = []
        for med in meds_today:
            try:
                med_time = datetime.strptime(med.get("time"), "%H:%M:%S").time()
                if med_time > current_time:
                    # Compute datetime for today's medication
                    med_dt = datetime.combine(now.date(), med_time)
                    upcoming.append((med_dt, med))
            except Exception as e:
                _LOGGER.error("Error parsing time for medication %s: %s", med, e)
        if upcoming:
            upcoming.sort(key=lambda x: x[0])
            return current_day, upcoming[0][1], upcoming[0][0]
        # Check subsequent days
        current_index = DAYS_OF_WEEK.index(current_day)
        for i in range(1, len(DAYS_OF_WEEK)):
            day = DAYS_OF_WEEK[(current_index + i) % len(DAYS_OF_WEEK)]
            meds = schedule.get(day, [])
            if meds:
                try:
                    # Take the earliest medication in that day
                    med_sorted = sorted(
                        meds,
                        key=lambda m: datetime.strptime(m.get("time"), "%H:%M:%S").time()
                    )
                    med = med_sorted[0]
                    # Calculate the date for the upcoming day
                    days_ahead = (DAYS_OF_WEEK.index(day) - current_index) % 7
                    med_date = now.date() + timedelta(days=days_ahead)
                    med_time = datetime.strptime(med.get("time"), "%H:%M:%S").time()
                    med_dt = datetime.combine(med_date, med_time)
                    return day, med, med_dt
                except Exception as e:
                    _LOGGER.error("Error parsing time for day %s: %s", day, e)
        return None, None, None

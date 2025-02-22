"""sensor.py - Sensor platform for Medical Assistant integration."""
import logging
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, DAYS_OF_WEEK

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensor entities for each day of the week, current day, and overall next medication."""
    sensors = [MedicationScheduleSensor(day, hass) for day in DAYS_OF_WEEK]
    sensors.append(CurrentDayMedicationSensor(hass))
    sensors.append(NextMedicationSensor(hass))
    async_add_entities(sensors, update_before_add=True)

class MedicationScheduleSensor(Entity):
    """Representation of a medication schedule sensor for a specific day, showing next medication info."""
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
        """Return next medication info for the day.
        
        If a medication is scheduled:
          - If it's within 12 hours from now, show a relative time (e.g. '30 minutes until Aspirin (100mg)').
          - Otherwise, show the exact timestamp and medication info.
        If no medication is scheduled (or all have passed), display an appropriate message.
        """
        schedule = self._hass.data[DOMAIN]["schedule"].get(self._day, [])
        next_med_info = self._get_next_medication_for_day(schedule)
        if next_med_info is None:
            return "No medication scheduled"
        med, med_dt = next_med_info
        now = datetime.now()
        delta = med_dt - now
        seconds = delta.total_seconds()
        if seconds < 0:
            return "Medication time passed"
        if seconds < 12 * 3600:
            # Show relative time
            minutes = int(seconds // 60)
            hours = int(seconds // 3600)
            if hours > 0:
                rel_time = f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                rel_time = f"{minutes} minute{'s' if minutes != 1 else ''}"
            return f"{rel_time} until {med.get('name')} ({med.get('strength')})"
        else:
            # Show timestamp and medication info
            time_str = med_dt.strftime("%a %H:%M")
            return f"{time_str} - {med.get('name')} ({med.get('strength')})"

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

    def _get_next_medication_for_day(self, schedule):
        """Determine the next medication for this sensor's day.
        
        - Compute the next occurrence of self._day relative to now.
        - For each medication in the day's schedule, combine the computed date with the medication's time.
        - Return the earliest upcoming medication (as a tuple: (medication dict, datetime)).
        """
        if not schedule:
            return None

        now = datetime.now()
        try:
            target_index = DAYS_OF_WEEK.index(self._day)
            current_index = DAYS_OF_WEEK.index(now.strftime("%A"))
        except Exception as e:
            _LOGGER.error("Error determining day indices: %s", e)
            return None

        # Compute how many days ahead the sensor's day is.
        days_ahead = (target_index - current_index) % 7
        # If it's today, use today's date; otherwise, compute the next occurrence.
        base_date = now.date() if days_ahead == 0 else now.date() + timedelta(days=days_ahead)

        upcoming = []
        for med in schedule:
            try:
                med_time = datetime.strptime(med.get("time"), "%H:%M:%S").time()
                med_dt = datetime.combine(base_date, med_time)
                if med_dt >= now:
                    upcoming.append((med_dt, med))
            except Exception as e:
                _LOGGER.error("Error parsing time for medication %s: %s", med, e)
        if upcoming:
            upcoming.sort(key=lambda x: x[0])
            # Return (medication, datetime)
            return upcoming[0][1], upcoming[0][0]
        else:
            return None

class CurrentDayMedicationSensor(Entity):
    """Sensor that always displays the next medication for the current day."""
    def __init__(self, hass):
        self._hass = hass
        self._unsubscribe_dispatcher = None

    @property
    def name(self):
        return "Medical Assistant Current Day Schedule"

    @property
    def unique_id(self):
        return "medical_assistant_current_day_schedule"

    @property
    def state(self):
        current_day = datetime.now().strftime("%A")
        schedule = self._hass.data[DOMAIN]["schedule"].get(current_day, [])
        next_med_info = self._get_next_medication_for_day(schedule)
        if next_med_info is None:
            return "No medication scheduled"
        med, med_dt = next_med_info
        now = datetime.now()
        delta = med_dt - now
        seconds = delta.total_seconds()
        if seconds < 0:
            return "Medication time passed"
        if seconds < 12 * 3600:
            minutes = int(seconds // 60)
            hours = int(seconds // 3600)
            if hours > 0:
                rel_time = f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                rel_time = f"{minutes} minute{'s' if minutes != 1 else ''}"
            return f"{rel_time} until {med.get('name')} ({med.get('strength')})"
        else:
            time_str = med_dt.strftime("%a %H:%M")
            return f"{time_str} - {med.get('name')} ({med.get('strength')})"

    @property
    def extra_state_attributes(self):
        current_day = datetime.now().strftime("%A")
        schedule = self._hass.data[DOMAIN]["schedule"].get(current_day, [])
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

    def _get_next_medication_for_day(self, schedule):
        if not schedule:
            return None

        now = datetime.now()
        base_date = now.date()
        upcoming = []
        for med in schedule:
            try:
                med_time = datetime.strptime(med.get("time"), "%H:%M:%S").time()
                med_dt = datetime.combine(base_date, med_time)
                if med_dt >= now:
                    upcoming.append((med_dt, med))
            except Exception as e:
                _LOGGER.error("Error parsing time for medication %s: %s", med, e)
        if upcoming:
            upcoming.sort(key=lambda x: x[0])
            return upcoming[0][1], upcoming[0][0]
        else:
            return None

class NextMedicationSensor(Entity):
    """Representation of the sensor that shows the overall next medication to take (across all days)."""
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
        schedule = self._hass.data[DOMAIN]["schedule"]
        next_day, next_med, med_dt = self._get_next_medication(schedule)
        if next_med and med_dt:
            now = datetime.now()
            delta = med_dt - now
            seconds = delta.total_seconds()
            if seconds < 12 * 3600:
                minutes = int(seconds // 60)
                hours = int(seconds // 3600)
                if hours > 0:
                    rel_time = f"{hours} hour{'s' if hours != 1 else ''}"
                else:
                    rel_time = f"{minutes} minute{'s' if minutes != 1 else ''}"
                return f"{rel_time} until {next_med.get('name')} ({next_med.get('strength')})"
            else:
                time_str = med_dt.strftime("%a %H:%M")
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
        """Determine the overall next medication across all days."""
        now = datetime.now()
        current_day = now.strftime("%A")
        # Check today's medications.
        meds_today = schedule.get(current_day, [])
        upcoming = []
        for med in meds_today:
            try:
                med_time = datetime.strptime(med.get("time"), "%H:%M:%S").time()
                med_dt = datetime.combine(now.date(), med_time)
                if med_dt > now:
                    upcoming.append((med_dt, med, current_day))
            except Exception as e:
                _LOGGER.error("Error parsing time for medication %s: %s", med, e)
        if upcoming:
            upcoming.sort(key=lambda x: x[0])
            med_dt, med, day = upcoming[0]
            return day, med, med_dt
        # Check subsequent days.
        try:
            current_index = DAYS_OF_WEEK.index(current_day)
        except Exception as e:
            _LOGGER.error("Error finding current day in DAYS_OF_WEEK: %s", e)
            return None, None, None
        for i in range(1, len(DAYS_OF_WEEK)):
            day = DAYS_OF_WEEK[(current_index + i) % len(DAYS_OF_WEEK)]
            meds = schedule.get(day, [])
            if meds:
                try:
                    meds_sorted = sorted(
                        meds,
                        key=lambda m: datetime.strptime(m.get("time"), "%H:%M:%S").time()
                    )
                    med = meds_sorted[0]
                    days_ahead = (DAYS_OF_WEEK.index(day) - current_index) % 7
                    med_date = now.date() + timedelta(days=days_ahead)
                    med_time = datetime.strptime(med.get("time"), "%H:%M:%S").time()
                    med_dt = datetime.combine(med_date, med_time)
                    return day, med, med_dt
                except Exception as e:
                    _LOGGER.error("Error parsing time for day %s: %s", day, e)
        return None, None, None

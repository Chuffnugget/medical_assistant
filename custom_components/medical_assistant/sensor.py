"""sensor.py - Sensor platform for Medical Assistant integration."""
import logging
from datetime import datetime, timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.input_select import InputSelectEntity

from .const import DOMAIN, DAYS_OF_WEEK

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensor entities for Medical Assistant."""
    entities = [
        NextMedicationSensor(hass),
        MedicationInputSelect(hass)
    ]
    async_add_entities(entities, update_before_add=True)

def get_next_occurrence(day: str, time_str: str):
    """
    Compute the next occurrence datetime for a given day (e.g. "Monday")
    and a time string in HH:MM:SS format.
    """
    now = datetime.now()
    try:
        day_index = DAYS_OF_WEEK.index(day)
    except ValueError:
        _LOGGER.error("Invalid day provided: %s", day)
        return None
    today_index = DAYS_OF_WEEK.index(now.strftime("%A"))
    days_ahead = (day_index - today_index) % 7
    med_time = datetime.strptime(time_str, "%H:%M:%S").time()
    candidate = datetime.combine(now.date() + timedelta(days=days_ahead), med_time)
    # If the candidate time is earlier than now (for today), schedule for next week.
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate

class NextMedicationSensor(Entity):
    """Sensor that shows the overall next medication (across all days)."""
    def __init__(self, hass):
        self._hass = hass
        self._state = "No medication scheduled"
        self._unsubscribe_dispatcher = None

    @property
    def name(self):
        return "Medical Assistant Next Medication"

    @property
    def unique_id(self):
        return "medical_assistant_next_medication"

    @property
    def state(self):
        return self._state

    def _compute_next_medication(self):
        now = datetime.now()
        schedule = self._hass.data[DOMAIN]["schedule"]
        upcoming = []
        for med in schedule:
            med_dt = get_next_occurrence(med["day"], med["time"])
            if med_dt and med_dt > now:
                upcoming.append((med_dt, med))
        if upcoming:
            upcoming.sort(key=lambda x: x[0])
            next_dt, next_med = upcoming[0]
            delta = next_dt - now
            seconds = delta.total_seconds()
            if seconds < 12 * 3600:
                minutes = int(seconds // 60)
                hours = int(seconds // 3600)
                rel_time = (f"{hours} hour{'s' if hours != 1 else ''}"
                            if hours > 0 else f"{minutes} minute{'s' if minutes != 1 else ''}")
                return f"{rel_time} until {next_med.get('name')} ({next_med.get('strength')})"
            else:
                time_str = next_dt.strftime("%a %H:%M")
                return f"{next_med['day']} {time_str} - {next_med.get('name')} ({next_med.get('strength')})"
        return "No medication scheduled"

    async def async_update(self):
        self._state = self._compute_next_medication()

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

class MedicationInputSelect(InputSelectEntity):
    """
    Input select entity that displays all medication records in the global schedule.
    Each option is a text string formatted as:
      "<YYYY-MM-DD HH:MM:SS> - <Medication Name> (<strength>)"
    ordered by the medication’s next occurrence.
    """
    def __init__(self, hass):
        self._hass = hass
        self._options = []
        self._selected_option = None
        self._unsubscribe_dispatcher = None
        self._update_options()

    @property
    def name(self):
        return "Medication Schedule Input"

    @property
    def unique_id(self):
        return "medical_assistant_medication_input_select"

    @property
    def options(self):
        return self._options

    @property
    def state(self):
        return self._selected_option

    def _update_options(self):
        now = datetime.now()
        schedule = self._hass.data[DOMAIN]["schedule"]
        option_list = []
        for med in schedule:
            med_dt = get_next_occurrence(med["day"], med["time"])
            if med_dt:
                option_str = f"{med_dt.strftime('%Y-%m-%d %H:%M:%S')} - {med['name']} ({med.get('strength')})"
                option_list.append((med_dt, option_str))
        # Order options by upcoming time.
        option_list.sort(key=lambda x: x[0])
        self._options = [option for _, option in option_list]
        if self._options:
            self._selected_option = self._options[0]
        else:
            self._selected_option = "No medications scheduled"

    async def async_update(self):
        self._update_options()

    async def async_added_to_hass(self):
        self._unsubscribe_dispatcher = async_dispatcher_connect(
            self._hass, f"{DOMAIN}_update", self._handle_update
        )

    async def async_will_remove_from_hass(self):
        if self._unsubscribe_dispatcher:
            self._unsubscribe_dispatcher()
            self._unsubscribe_dispatcher = None

    def _handle_update(self):
        self._update_options()
        self.schedule_update_ha_state(True)

    def select_option(self, option: str) -> None:
        if option in self._options:
            self._selected_option = option
            self.schedule_update_ha_state()

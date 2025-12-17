from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SIGNAL_DATA_UPDATED
from . import Runtime


@dataclass(slots=True)
class NextDose:
    when: datetime | None
    med: dict[str, Any] | None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: Runtime = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            NextMedNameSensor(hass, entry, runtime),
            NextMedStrengthSensor(hass, entry, runtime),
            NextMedTimeSensor(hass, entry, runtime),
            NextMedCountdownSensor(hass, entry, runtime),
        ],
        update_before_add=True,
    )


class _BaseMedicalAssistantEntity(Entity):
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, runtime: Runtime) -> None:
        self.hass = hass
        self.entry = entry
        self.runtime = runtime
        self._unsub: callable | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.entry.title,
            manufacturer="Chuffnugget",
            model="Medical Assistant",
        )

    async def async_added_to_hass(self) -> None:
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_DATA_UPDATED, self._handle_update_signal
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_update_signal(self, entry_id: str) -> None:
        if entry_id != self.entry.entry_id:
            return
        self.async_schedule_update_ha_state(True)

    def _compute_next(self) -> NextDose:
        meds = [m for m in self.runtime.store.list_meds() if m.get("enabled", True)]
        if not meds:
            return NextDose(when=None, med=None)

        now = dt_util.now()
        tz = dt_util.DEFAULT_TIME_ZONE

        best_when: datetime | None = None
        best_med: dict[str, Any] | None = None

        for med in meds:
            time_local = str(med.get("time_local", "00:00"))
            try:
                hh, mm = time_local.split(":")
                hour = int(hh)
                minute = int(mm)
            except Exception:
                continue

            days = med.get("days_of_week", [])
            if not isinstance(days, list) or not days:
                continue

            # Search up to 7 days ahead for the next matching weekday/time
            for offset in range(0, 8):
                day = (now + timedelta(days=offset)).date()
                candidate = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)

                if candidate.weekday() not in days:
                    continue
                if candidate <= now:
                    continue

                if best_when is None or candidate < best_when:
                    best_when = candidate
                    best_med = med
                break

        return NextDose(when=best_when, med=best_med)


class NextMedNameSensor(_BaseMedicalAssistantEntity):
    _attr_name = "Next medicine"
    _attr_unique_id = "next_medicine_name"

    @property
    def state(self) -> str | None:
        nxt = self._compute_next()
        return (nxt.med or {}).get("name")


class NextMedStrengthSensor(_BaseMedicalAssistantEntity):
    _attr_name = "Next medicine strength"
    _attr_unique_id = "next_medicine_strength"

    @property
    def state(self) -> str | None:
        nxt = self._compute_next()
        return (nxt.med or {}).get("strength")


class NextMedTimeSensor(_BaseMedicalAssistantEntity):
    _attr_name = "Next medicine time"
    _attr_unique_id = "next_medicine_time"

    @property
    def state(self) -> str | None:
        nxt = self._compute_next()
        if not nxt.when:
            return None
        # ISO timestamp string
        return nxt.when.isoformat()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        nxt = self._compute_next()
        return {"id": (nxt.med or {}).get("id")}


class NextMedCountdownSensor(_BaseMedicalAssistantEntity):
    _attr_name = "Next medicine countdown"
    _attr_unique_id = "next_medicine_countdown"
    _attr_native_unit_of_measurement = "s"

    @property
    def state(self) -> int | None:
        nxt = self._compute_next()
        if not nxt.when:
            return None
        now = dt_util.now()
        seconds = int((nxt.when - now).total_seconds())
        return max(seconds, 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        nxt = self._compute_next()
        return {
            "id": (nxt.med or {}).get("id"),
            "name": (nxt.med or {}).get("name"),
            "strength": (nxt.med or {}).get("strength"),
            "time_local": (nxt.med or {}).get("time_local"),
            "days_of_week": (nxt.med or {}).get("days_of_week"),
        }

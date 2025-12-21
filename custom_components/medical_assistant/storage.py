from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store


def _default_data() -> dict[str, Any]:
    return {"schema": 1, "meds": []}


@dataclass(slots=True)
class MedicalAssistantStore:
    hass: HomeAssistant
    version: int
    key: str

    # Must be declared because slots=True prevents dynamic attributes
    _store: Store = field(init=False)
    data: dict[str, Any] = field(default_factory=_default_data)

    def __post_init__(self) -> None:
        self._store = Store(self.hass, self.version, self.key)

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        if isinstance(loaded, dict):
            self.data = loaded
        else:
            self.data = _default_data()

        self.data.setdefault("schema", 1)
        self.data.setdefault("meds", [])

    async def async_save(self) -> None:
        await self._store.async_save(self.data)

    def list_meds(self) -> list[dict[str, Any]]:
        meds = self.data.get("meds", [])
        return meds if isinstance(meds, list) else []

    async def set_meds(self, meds: list[dict[str, Any]]) -> None:
        self.data["meds"] = meds
        await self.async_save()

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, DEFAULT_TITLE


class MedicalAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Medical Assistant."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Single-instance integration
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Optional("name", default=DEFAULT_TITLE): str,
                    }
                ),
            )

        return self.async_create_entry(
            title=user_input.get("name", DEFAULT_TITLE),
            data={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return MedicalAssistantOptionsFlow(config_entry)


class MedicalAssistantOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Medical Assistant."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        opts = dict(self._entry.options)

        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "countdown_update_seconds",
                            default=opts.get("countdown_update_seconds", 30),
                        ): vol.All(int, vol.Range(min=5, max=600)),
                    }
                ),
            )

        return self.async_create_entry(title="", data=user_input)

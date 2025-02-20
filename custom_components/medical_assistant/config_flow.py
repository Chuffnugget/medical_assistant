"""config_flow.py - Medical Assistant Integration for Home Assistant."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class MedicalAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Medical Assistant."""
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="Medical Assistant", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

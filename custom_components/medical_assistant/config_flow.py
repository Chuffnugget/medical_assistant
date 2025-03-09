import os
import shutil
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def deploy_panel_file(hass: HomeAssistant) -> str:
    """Copy medication-panel.js from the integration folder to config/www.

    Returns a status message.
    """
    # Integration directory: custom_components/medical_assistant
    integration_dir = os.path.dirname(__file__)
    # Source file: custom_components/medical_assistant/local/medication-panel.js
    src_path = os.path.join(integration_dir, "local", "medication-panel.js")
    # Destination: config/www/medication-panel.js
    dst_path = hass.config.path("www", "medication-panel.js")

    if not os.path.exists(src_path):
        msg = f"Error: Source file not found at {src_path}"
        _LOGGER.error(msg)
        return msg

    try:
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy(src_path, dst_path)
        msg = f"Success: Deployed medication-panel.js to {dst_path}"
        _LOGGER.info(msg)
        return msg
    except Exception as e:
        msg = f"Error deploying medication-panel.js: {e}"
        _LOGGER.error(msg)
        return msg

class MedicalAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Medical Assistant."""
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            deploy_status = deploy_panel_file(self.hass)
            # If the deploy_status indicates an error, show the form again with the error.
            if deploy_status.startswith("Error"):
                errors["base"] = deploy_status
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({}),
                    errors=errors,
                    description_placeholders={"deploy_status": deploy_status},
                )
            # Otherwise, create the entry and pass the deploy status in the data.
            return self.async_create_entry(title="Medical Assistant", data={"deploy_status": deploy_status})
        # When first showing the form, display a placeholder message.
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={"deploy_status": "Waiting for file deployment..."}
        )

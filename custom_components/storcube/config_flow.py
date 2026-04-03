from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import *

class StorcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            raw_ids = user_input[CONF_DEVICE_ID]
            device_ids = [d.strip() for d in raw_ids.split(",") if d.strip()]

            if not device_ids:
                errors["base"] = "no_device"
            else:
                await self.async_set_unique_id(user_input[CONF_LOGIN_NAME])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"StorCube ({len(device_ids)} devices)",
                    data={
                        CONF_LOGIN_NAME: user_input[CONF_LOGIN_NAME],
                        CONF_AUTH_PASSWORD: user_input[CONF_AUTH_PASSWORD],
                        CONF_DEVICE_IDS: device_ids,
                        CONF_APP_CODE: DEFAULT_APP_CODE,
                        CONF_DEBUG: user_input.get(CONF_DEBUG, False),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOGIN_NAME): str,
                    vol.Required(CONF_AUTH_PASSWORD): str,
                    vol.Required(CONF_DEVICE_ID): str,
                    vol.Optional(CONF_DEBUG, default=False): bool,
                }
            ),
            errors=errors,
        )

    @callback
    def async_get_options_flow(self, entry):
        return StorcubeOptionsFlow(entry)


class StorcubeOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEBUG,
                        default=self.entry.data.get(CONF_DEBUG, False),
                    ): bool,
                }
            ),
        )

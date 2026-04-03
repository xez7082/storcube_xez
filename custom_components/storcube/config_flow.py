from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_DEVICE_IDS,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
    CONF_APP_CODE,
    CONF_DEBUG,
    DEFAULT_APP_CODE,
)

_LOGGER = logging.getLogger(__name__)


class StorcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Storcube."""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        """Initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                raw_ids = user_input.get(CONF_DEVICE_ID, "")
                device_ids = [d.strip() for d in raw_ids.split(",") if d.strip()]

                if not device_ids:
                    errors["base"] = "no_device"
                else:
                    # 🔥 FIX: unique_id plus stable et unique
                    await self.async_set_unique_id(
                        f"{user_input[CONF_LOGIN_NAME]}_{device_ids[0]}"
                    )
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"StorCube ({len(device_ids)} device{'s' if len(device_ids) > 1 else ''})",
                        data={
                            CONF_LOGIN_NAME: user_input[CONF_LOGIN_NAME],
                            CONF_AUTH_PASSWORD: user_input[CONF_AUTH_PASSWORD],
                            CONF_DEVICE_IDS: device_ids,
                            CONF_APP_CODE: DEFAULT_APP_CODE,
                            CONF_DEBUG: user_input.get(CONF_DEBUG, False),
                        },
                    )

            except Exception as err:
                _LOGGER.exception("Config flow error: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOGIN_NAME): str,
                    vol.Required(CONF_AUTH_PASSWORD): str,
                    vol.Required(CONF_DEVICE_ID): str,  # "id1,id2"
                    vol.Optional(CONF_DEBUG, default=False): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        """Options flow."""
        return StorcubeOptionsFlow(entry)


class StorcubeOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEBUG,
                        default=self.entry.options.get(
                            CONF_DEBUG,
                            self.entry.data.get(CONF_DEBUG, False),
                        ),
                    ): bool,

                    # 🔥 FIX: allow device update (important)
                    vol.Optional(
                        CONF_DEVICE_ID,
                        default=",".join(self.entry.data.get(CONF_DEVICE_IDS, [])),
                    ): str,
                }
            ),
        )

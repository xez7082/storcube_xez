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
                login = user_input.get(CONF_LOGIN_NAME)
                password = user_input.get(CONF_AUTH_PASSWORD)

                # 🔥 FIX 1: validation stricte
                if not login or not password:
                    errors["base"] = "invalid_auth"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._get_schema(),
                        errors=errors,
                    )

                # 🔥 FIX 2: nettoyage device IDs
                raw_ids = user_input.get(CONF_DEVICE_ID, "")
                device_ids = [
                    d.strip()
                    for d in raw_ids.split(",")
                    if d and d.strip()
                ]

                if not device_ids:
                    errors["base"] = "no_device"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._get_schema(),
                        errors=errors,
                    )

                # 🔥 FIX 3: unique_id stable + safe
                unique_id = f"{login}_{device_ids[0]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Storcube ({device_ids[0]})",
                    data={
                        CONF_LOGIN_NAME: login,
                        CONF_AUTH_PASSWORD: password,
                        CONF_DEVICE_IDS: device_ids,
                        CONF_APP_CODE: user_input.get(CONF_APP_CODE, DEFAULT_APP_CODE),
                        CONF_DEBUG: user_input.get(CONF_DEBUG, False),
                    },
                )

            except Exception as err:
                _LOGGER.exception("Config flow error: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
            errors=errors,
        )

    def _get_schema(self):
        return vol.Schema(
            {
                vol.Required(CONF_LOGIN_NAME): str,
                vol.Required(CONF_AUTH_PASSWORD): str,
                vol.Required(CONF_DEVICE_ID): str,
                vol.Optional(CONF_APP_CODE, default=DEFAULT_APP_CODE): str,
                vol.Optional(CONF_DEBUG, default=False): bool,
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return StorcubeOptionsFlow(entry)


class StorcubeOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, entry: config_entries.ConfigEntry):
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
                        default=self.entry.options.get(
                            CONF_DEBUG,
                            self.entry.data.get(CONF_DEBUG, False),
                        ),
                    ): bool,

                    vol.Optional(
                        CONF_DEVICE_ID,
                        default=",".join(self.entry.data.get(CONF_DEVICE_IDS, [])),
                    ): str,
                }
            ),
        )

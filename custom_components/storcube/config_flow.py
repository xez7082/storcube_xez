from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow

from .const import (
    DOMAIN,
    CONF_DEVICE_IDS,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
    CONF_APP_CODE,
    CONF_DEBUG,
    CONF_MQTT_HOST,
    CONF_MQTT_PORT,
    CONF_MQTT_USER,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_TOPIC,
    DEFAULT_APP_CODE,
    DEFAULT_MQTT_PORT,
    DEFAULT_MQTT_TOPIC,
)

_LOGGER = logging.getLogger(__name__)


class StorcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Storcube config flow."""

    VERSION = 3

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                login = user_input.get(CONF_LOGIN_NAME)
                password = user_input.get(CONF_AUTH_PASSWORD)

                if not login or not password:
                    errors["base"] = "invalid_auth"
                    raise ValueError("Missing credentials")

                # 🔥 DEVICE IDS CLEAN
                raw_ids = user_input.get(CONF_DEVICE_IDS, "")
                device_ids = [d.strip() for d in raw_ids.split(",") if d.strip()]

                if not device_ids:
                    errors["base"] = "no_device"
                    raise ValueError("No device IDs")

                # 🔥 UNIQUE ID
                unique_id = f"{login}_{device_ids[0]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"StorCube {device_ids[0]}",
                    data={
                        CONF_LOGIN_NAME: login,
                        CONF_AUTH_PASSWORD: password,
                        CONF_DEVICE_IDS: device_ids,
                        CONF_APP_CODE: user_input.get(CONF_APP_CODE, DEFAULT_APP_CODE),
                        CONF_DEBUG: user_input.get(CONF_DEBUG, False),

                        # MQTT
                        CONF_MQTT_HOST: user_input.get(CONF_MQTT_HOST),
                        CONF_MQTT_PORT: user_input.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT),
                        CONF_MQTT_USER: user_input.get(CONF_MQTT_USER),
                        CONF_MQTT_PASSWORD: user_input.get(CONF_MQTT_PASSWORD),
                        CONF_MQTT_TOPIC: user_input.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC),
                    },
                )

            except AbortFlow as err:
                # 🔥 IMPORTANT → ne pas transformer en unknown
                raise err

            except Exception as err:
                _LOGGER.exception("Config flow error: %s", err)
                if "base" not in errors:
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(),
            errors=errors,
        )

    def _schema(self):
        return vol.Schema(
            {
                vol.Required(CONF_LOGIN_NAME): str,
                vol.Required(CONF_AUTH_PASSWORD): str,

                vol.Required(CONF_DEVICE_IDS): str,

                vol.Optional(CONF_APP_CODE, default=DEFAULT_APP_CODE): str,
                vol.Optional(CONF_DEBUG, default=False): bool,

                # MQTT
                vol.Required(CONF_MQTT_HOST): str,
                vol.Optional(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): int,
                vol.Required(CONF_MQTT_USER): str,
                vol.Required(CONF_MQTT_PASSWORD): str,
                vol.Optional(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC): str,
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return StorcubeOptionsFlow(entry)


class StorcubeOptionsFlow(config_entries.OptionsFlow):
    """Options flow."""

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
                        default=self.entry.options.get(
                            CONF_DEBUG,
                            self.entry.data.get(CONF_DEBUG, False),
                        ),
                    ): bool,
                }
            ),
        )

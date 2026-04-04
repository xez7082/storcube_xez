from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult, AbortFlow

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
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
    """Gestion du flux de configuration Storcube."""

    VERSION = 3

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Étape initiale de configuration par l'utilisateur."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # 1. Nettoyage des IDs
                raw_ids = user_input.get(CONF_DEVICE_IDS, "")
                device_ids = [d.strip() for d in raw_ids.split(",") if d.strip()]

                if not device_ids:
                    errors["base"] = "no_device"
                else:
                    # 2. Création de l'ID unique
                    login = user_input[CONF_LOGIN_NAME]
                    primary_id = device_ids[0]
                    
                    await self.async_set_unique_id(f"{login}_{primary_id}")
                    self._abort_if_unique_id_configured()

                    # 3. Construction du dictionnaire de données
                    data = {
                        CONF_LOGIN_NAME: login,
                        CONF_AUTH_PASSWORD: user_input[CONF_AUTH_PASSWORD],
                        CONF_DEVICE_IDS: device_ids,
                        CONF_DEVICE_ID: primary_id,
                        CONF_APP_CODE: user_input.get(CONF_APP_CODE, DEFAULT_APP_CODE),
                        CONF_DEBUG: user_input.get(CONF_DEBUG, False),
                    }

                    # 4. Ajout MQTT si renseigné
                    if user_input.get(CONF_MQTT_HOST):
                        data.update({
                            CONF_MQTT_HOST: user_input[CONF_MQTT_HOST],
                            CONF_MQTT_PORT: user_input.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT),
                            CONF_MQTT_USER: user_input.get(CONF_MQTT_USER),
                            CONF_MQTT_PASSWORD: user_input.get(CONF_MQTT_PASSWORD),
                            CONF_MQTT_TOPIC: user_input.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC),
                        })

                    return self.async_create_entry(
                        title=f"StorCube ({primary_id})",
                        data=data,
                    )

            except AbortFlow:
                raise
            except Exception as err:
                _LOGGER.exception("Erreur flux de configuration : %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(user_input),
            errors=errors,
        )

    def _schema(self, user_input: dict[str, Any] | None = None) -> vol.Schema:
        """Schéma du formulaire dynamique."""
        if user_input is None:
            user_input = {}

        return vol.Schema(
            {
                vol.Required(CONF_LOGIN_NAME, default=user_input.get(CONF_LOGIN_NAME, "")): str,
                vol.Required(CONF_AUTH_PASSWORD, default=user_input.get(CONF_AUTH_PASSWORD, "")): str,
                vol.Required(CONF_DEVICE_IDS, default=user_input.get(CONF_DEVICE_IDS, "")): str,
                vol.Optional(CONF_APP_CODE, default=DEFAULT_APP_CODE): str,
                
                # MQTT Optionnel
                vol.Optional(CONF_MQTT_HOST): str,
                vol.Optional(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): int,
                vol.Optional(CONF_MQTT_USER): str,
                vol.Optional(CONF_MQTT_PASSWORD): str,
                
                vol.Optional(CONF_DEBUG, default=False): bool,
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry) -> StorcubeOptionsFlow:
        return StorcubeOptionsFlow(entry)


class StorcubeOptionsFlow(config_entries.OptionsFlow):
    """Gestion des options modifiables."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEBUG,
                        default=self.entry.options.get(
                            CONF_DEBUG, self.entry.data.get(CONF_DEBUG, False)
                        ),
                    ): bool,
                }
            ),
        )

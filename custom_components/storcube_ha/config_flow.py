"""Config flow for Storcube integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

# On importe les constantes pour être sûr que les clés correspondent au reste du code
from .const import (
    DOMAIN, 
    CONF_DEVICE_ID, 
    CONF_LOGIN_NAME, 
    CONF_AUTH_PASSWORD
)

class StorcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le flux de configuration pour Storcube."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Étape initiale lors de l'ajout manuel par l'utilisateur."""
        errors = {}

        if user_input is not None:
            # 1. Vérification : empêcher d'ajouter deux fois la même batterie
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            # 2. Création de l'entrée dans Home Assistant
            return self.async_create_entry(
                title=f"Storcube {user_input[CONF_DEVICE_ID]}",
                data=user_input
            )

        # Schéma du formulaire (ce qui apparaît à l'écran)
        # Note : Les noms des champs ici doivent être les mêmes que dans strings.json
        DATA_SCHEMA = vol.Schema({
            vol.Required(CONF_LOGIN_NAME): str,
            vol.Required(CONF_AUTH_PASSWORD): str,
            vol.Required(CONF_DEVICE_ID): str,
            vol.Optional("host"): str,
            vol.Optional("port", default=1883): cv.port,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )

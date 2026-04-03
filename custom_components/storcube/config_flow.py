"""Config flow for Storcube integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

# On importe les constantes
from .const import (
    DOMAIN, 
    CONF_DEVICE_ID, 
    CONF_LOGIN_NAME, 
    CONF_AUTH_PASSWORD,
    CONF_APP_CODE,       # Assurez-vous que c'est dans const.py
    DEFAULT_APP_CODE     # Assurez-vous que c'est dans const.py
)

class StorcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le flux de configuration pour Storcube."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Étape initiale lors de l'ajout manuel par l'utilisateur."""
        errors = {}

        if user_input is not None:
            # 1. Vérification : empêcher les doublons
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            # 2. Injection automatique de app_code pour éviter l'erreur KeyError
            # On copie les entrées utilisateur et on ajoute la valeur manquante
            data = user_input.copy()
            data[CONF_APP_CODE] = DEFAULT_APP_CODE 

            # 3. Création de l'entrée
            return self.async_create_entry(
                title=f"Storcube {user_input[CONF_DEVICE_ID]}",
                data=data
            )

        # Schéma du formulaire (sans app_code pour simplifier la vie de l'utilisateur)
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

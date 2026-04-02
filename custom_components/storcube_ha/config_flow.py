import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOGIN_NAME, CONF_AUTH_PASSWORD

class StorcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le flux de configuration pour Storcube."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Étape initiale lors de l'ajout par l'utilisateur."""
        errors = {}

        if user_input is not None:
            # Ici, on pourrait ajouter une validation de connexion réelle
            # Pour l'instant, on crée l'entrée directement
            return self.async_create_entry(
                title=f"Storcube ({user_input[CONF_DEVICE_ID]})",
                data=user_input
            )

        # Formulaire affiché à l'utilisateur (lié à strings.json)
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

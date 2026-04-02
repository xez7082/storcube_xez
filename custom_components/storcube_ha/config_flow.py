"""Config flow for Storcube Battery Monitor integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_APP_CODE,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_APP_CODE,
    TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)

# Schéma de données centralisé pour éviter les répétitions
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Optional(CONF_APP_CODE, default=DEFAULT_APP_CODE): str,
        vol.Required(CONF_LOGIN_NAME): str,
        vol.Required(CONF_AUTH_PASSWORD): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Valider les identifiants en appelant l'API Storcube."""
    session = async_get_clientsession(hass)
    
    auth_data = {
        "appCode": data[CONF_APP_CODE],
        "loginName": data[CONF_LOGIN_NAME],
        "password": data[CONF_AUTH_PASSWORD],
    }

    try:
        async with session.post(TOKEN_URL, json=auth_data, timeout=10) as response:
            if response.status != 200:
                _LOGGER.error("Erreur HTTP Storcube: %s", response.status)
                raise InvalidAuth
            
            json_response = await response.json()
            if json_response.get("code") != 200:
                _LOGGER.error("Erreur API Storcube: %s", json_response.get("message"))
                raise CannotConnect
                
    except aiohttp.ClientError as err:
        _LOGGER.error("Erreur de connexion: %s", err)
        raise CannotConnect from err


class StorcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Storcube Battery Monitor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Étape initiale de configuration."""
        errors = {}
        
        if user_input is not None:
            # Vérifier si l'appareil est déjà configuré (évite les doublons)
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            try:
                await validate_input(self.hass, user_input)
                return self.async_create_entry(
                    title=f"Storcube {user_input[CONF_DEVICE_ID]}",
                    data=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Erreur inattendue")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Obtenir le gestionnaire d'options."""
        return StorcubeOptionsFlowHandler(config_entry)


class StorcubeOptionsFlowHandler(config_entries.OptionsFlow):
    """Gérer les options (modification après installation)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Gérer les options."""
        errors = {}

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                return self.async_create_entry(title="", data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"

        # On pré-remplit avec les valeurs actuelles
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self.config_entry.data.get(CONF_HOST)): str,
                    vol.Required(CONF_LOGIN_NAME, default=self.config_entry.data.get(CONF_LOGIN_NAME)): str,
                    vol.Required(CONF_AUTH_PASSWORD, default=self.config_entry.data.get(CONF_AUTH_PASSWORD)): str,
                    # Ajoutez les autres champs ici si nécessaire...
                }
            ),
            errors=errors,
        )

class CannotConnect(HomeAssistantError):
    """Erreur de connexion."""

class InvalidAuth(HomeAssistantError):
    """Erreur d'authentification."""

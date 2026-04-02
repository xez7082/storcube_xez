"""Number platform for Storcube Battery Monitor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    UnitOfPower,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    SET_POWER_URL,
    SET_THRESHOLD_URL,
    TOKEN_URL,
    CONF_APP_CODE,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Storcube number platform."""
    config = config_entry.data
    device_id = config.get(CONF_DEVICE_ID)

    if not device_id:
        _LOGGER.error("Device ID manquant dans la configuration")
        return

    # On passe la session globale de HA aux entités
    entities = [
        StorcubePowerNumber(hass, config_entry),
        StorcubeThresholdNumber(hass, config_entry)
    ]

    async_add_entities(entities)

class StorcubeBaseNumber(NumberEntity):
    """Classe de base pour les contrôles StorCube."""
    
    _attr_has_entity_name = True
    _attr_should_poll = False  # Les changements sont poussés par l'UI

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize base number entity."""
        self.hass = hass
        self.config_entry = config_entry
        self._session = async_get_clientsession(hass)
        self._device_id = config_entry.data[CONF_DEVICE_ID]
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
        }

    async def _get_auth_token(self) -> str | None:
        """Récupérer le token d'authentification (méthode mutualisée)."""
        credentials = {
            "appCode": self.config_entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.config_entry.data[CONF_LOGIN_NAME],
            "password": self.config_entry.data[CONF_AUTH_PASSWORD]
        }
        try:
            async with self._session.post(TOKEN_URL, json=credentials, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 200:
                        return data["data"]["token"]
        except Exception as e:
            _LOGGER.error("Erreur auth number: %s", e)
        return None

class StorcubePowerNumber(StorcubeBaseNumber):
    """Contrôle de puissance de sortie."""

    def __init__(self, hass, config_entry) -> None:
        super().__init__(hass, config_entry)
        self._attr_name = "Puissance de Sortie"
        self._attr_unique_id = f"{self._device_id}_output_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 800.0
        self._attr_native_step = 1.0
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_value = 100.0

    async def async_set_native_value(self, value: float) -> None:
        """Update the power value."""
        token = await self._get_auth_token()
        if not token: return

        headers = {"Authorization": token, "appCode": "Storcube"}
        params = {"equipId": self._device_id, "power": int(value)}

        try:
            async with self._session.get(SET_POWER_URL, headers=headers, params=params) as resp:
                if resp.status == 200 and (await resp.json()).get("code") == 200:
                    self._attr_native_value = value
                    self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Erreur set_power: %s", e)

class StorcubeThresholdNumber(StorcubeBaseNumber):
    """Contrôle du seuil de batterie."""

    def __init__(self, hass, config_entry) -> None:
        super().__init__(hass, config_entry)
        self._attr_name = "Seuil de Batterie"
        self._attr_unique_id = f"{self._device_id}_battery_threshold"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 1.0
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_value = 80.0

    async def async_set_native_value(self, value: float) -> None:
        """Update the threshold value."""
        token = await self._get_auth_token()
        if not token: return

        headers = {"Authorization": token, "Content-Type": "application/json", "appCode": "Storcube"}
        # On utilise le payload qui semble le plus standard d'après tes tests
        payload = {"reserved": str(int(value)), "equipId": self._device_id}

        try:
            async with self._session.post(SET_THRESHOLD_URL, headers=headers, json=payload) as resp:
                if resp.status == 200 and (await resp.json()).get("code") == 200:
                    self._attr_native_value = value
                    self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Erreur set_threshold: %s", e)

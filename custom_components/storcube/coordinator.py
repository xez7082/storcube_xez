from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN, SCAN_INTERVAL_SECONDS,
    CONF_LOGIN_NAME, CONF_AUTH_PASSWORD, TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self._token: str | None = None
        # Initialisation du dictionnaire de données
        self.data: dict[str, Any] = {}

    async def _async_get_token(self) -> str | None:
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)
        payload = {"loginName": login, "password": password, "appCode": "Storcube"}
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.post(TOKEN_URL, json=payload)
                res_data = await response.json()
                return res_data.get("data", {}).get("token")
        except Exception as e:
            _LOGGER.debug("Token non disponible (Cloud peut être optionnel si MQTT fonctionne): %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Méthode Cloud (HTTP)."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            return self.data

        session = async_get_clientsession(self.hass)
        headers = {"token": self._token, "appCode": "Storcube", "Content-Type": "application/json"}
        
        try:
            # On tente la liste car c'est le standard
            async with async_timeout.timeout(5):
                async with session.get("http://baterway.com/api/equip/list", headers=headers) as resp:
                    res = await resp.json()
                    items = res.get("data", {}).get("list", []) if isinstance(res.get("data"), dict) else []
                    
                    for item in items:
                        sn = str(item.get("deviceSn"))
                        if sn not in self.data: self.data[sn] = {}
                        self.data[sn].update(item)
        except Exception:
            pass # On ignore les erreurs Cloud si MQTT prend le relais

        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        """Cette fonction est appelée par __init__.py ou mqtt.py quand un message arrive."""
        _LOGGER.debug("Mise à jour MQTT reçue pour %s: %s", device_id, payload)
        
        if device_id not in self.data:
            self.data[device_id] = {}
        
        # On fusionne les données MQTT dans le coordinateur
        self.data[device_id].update(payload)
        
        # On force le rafraîchissement des capteurs dans HA
        self.async_set_updated_data(self.data)

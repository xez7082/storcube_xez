from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, SCAN_INTERVAL_SECONDS,
    CONF_LOGIN_NAME, CONF_AUTH_PASSWORD,
    CONF_DEVICE_IDS,
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
        self.data: dict[str, Any] = {}

    async def _async_get_token(self) -> str | None:
        """Authentification mise à jour 2026."""
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)
        
        # URL de login mise à jour
        url = "https://api-eu.baterway.com/api/login/login"
        payload = {
            "loginName": login,
            "password": password,
            "appCode": "Storcube",
            "terminalType": "1" # Important pour simuler l'app mobile
        }
        
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.post(url, json=payload)
                res_data = await response.json()
                token = res_data.get("data", {}).get("token")
                if token:
                    _LOGGER.debug("Authentification réussie")
                return token
        except Exception as e:
            _LOGGER.error("Échec auth Storcube : %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération des données S1000 (Correctif Février 2026)."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            return self.data

        session = async_get_clientsession(self.hass)
        # Headers renforcés pour simuler l'application officielle
        headers = {
            "token": self._token, 
            "appCode": "Storcube",
            "lang": "fr",
            "Content-Type": "application/json"
        }
        
        device_ids = self.entry.data.get(CONF_DEVICE_IDS) or [self.entry.data.get("device_id")]

        for device_id in device_ids:
            if not device_id: continue

            # DEPUIS FÉVRIER 2026 : L'URL est passée en /device/ et utilise deviceSn
            url = f"https://api-eu.baterway.com/api/device/getDeviceDetail?deviceSn={device_id}"
            
            try:
                async with async_timeout.timeout(10):
                    async with session.get(url, headers=headers) as resp:
                        res = await resp.json()
                        
                        # LOG CRITIQUE : Pour voir si on a enfin autre chose que 0
                        _LOGGER.warning("DEBUG S1000 [%s]: %s", device_id, res)

                        if res.get("code") == 200:
                            data_content = res.get("data")
                            if isinstance(data_content, dict):
                                # Sur les S1000, les données sont souvent dans 'deviceStatus' ou 'item'
                                status = data_content.get("deviceStatus") or data_content
                                self.data[str(device_id)] = status
                                
            except Exception as err:
                _LOGGER.error("Erreur de lecture %s : %s", device_id, err)

        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        """Backup MQTT."""
        if device_id not in self.data: self.data[device_id] = {}
        self.data[device_id].update(payload)
        self.async_set_updated_data(self.data)

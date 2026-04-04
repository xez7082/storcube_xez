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
        """Auth sur le serveur global (plus fiable au niveau DNS)."""
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)
        
        # URL globale (Net est souvent plus stable que EU)
        url = "https://api.baterway.net/api/login/login"
        payload = {
            "loginName": login,
            "password": password,
            "appCode": "Storcube",
            "terminalType": "1"
        }
        
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.post(url, json=payload)
                res_data = await response.json()
                token = res_data.get("data", {}).get("token")
                return token
        except Exception as e:
            _LOGGER.error("Erreur Auth (DNS/Net) : %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération via Endpoint 2026 sur serveur Global."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            return self.data

        session = async_get_clientsession(self.hass)
        headers = {
            "token": self._token, 
            "appCode": "Storcube",
            "Content-Type": "application/json"
        }
        
        device_ids = self.entry.data.get(CONF_DEVICE_IDS) or [self.entry.data.get("device_id")]

        for device_id in device_ids:
            if not device_id: continue

            # On tente l'endpoint qui a remplacé celui de Jon7119 en février
            url = f"https://api.baterway.net/api/device/getDeviceDetail?deviceSn={device_id}"
            
            try:
                async with async_timeout.timeout(10):
                    async with session.get(url, headers=headers) as resp:
                        res = await resp.json()
                        _LOGGER.warning("REPONSE 2026 [%s]: %s", device_id, res)

                        if res.get("code") == 200:
                            data_content = res.get("data")
                            if isinstance(data_content, dict):
                                # Extraction du statut (si présent dans deviceStatus)
                                status = data_content.get("deviceStatus") or data_content
                                self.data[str(device_id)] = status
                                
            except Exception as err:
                _LOGGER.debug("Erreur lecture %s : %s", device_id, err)

        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        if device_id not in self.data: self.data[device_id] = {}
        self.data[device_id].update(payload)
        self.async_set_updated_data(self.data)

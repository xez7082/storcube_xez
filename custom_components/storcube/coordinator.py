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

# On définit l'URL de token pour l'Europe si nécessaire
TOKEN_URL_EU = "https://api-eu.baterway.com/api/login/login"

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
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)
        payload = {"loginName": login, "password": password, "appCode": "Storcube"}
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                # Tentative sur le serveur EU
                response = await session.post(TOKEN_URL_EU, json=payload)
                res_data = await response.json()
                return res_data.get("data", {}).get("token")
        except Exception as e:
            _LOGGER.error("Erreur Token EU : %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
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

            # URLs sur le serveur EU
            urls = [
                f"https://api-eu.baterway.com/api/equip/getLatestData?device_id={device_id}",
                f"https://api-eu.baterway.com/api/equip/detail?device_id={device_id}",
            ]

            for url in urls:
                try:
                    async with async_timeout.timeout(5):
                        async with session.get(url, headers=headers) as resp:
                            res = await resp.json()
                            _LOGGER.warning("TEST EU [%s]: %s", device_id, res)

                            if res.get("code") == 200 and isinstance(res.get("data"), dict):
                                if len(res["data"]) > 1:
                                    self.data[str(device_id)] = res["data"]
                                    break
                except Exception:
                    continue

        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        if device_id not in self.data:
            self.data[device_id] = {}
        self.data[device_id].update(payload)
        self.async_set_updated_data(self.data)

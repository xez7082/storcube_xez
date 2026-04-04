from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN, SCAN_INTERVAL_SECONDS,
    CONF_LOGIN_NAME, CONF_AUTH_PASSWORD, TOKEN_URL,
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
            _LOGGER.error("Erreur Token : %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        if not self._token:
            self._token = await self._async_get_token()
        if not self._token:
            raise UpdateFailed("Authentification échouée")

        session = async_get_clientsession(self.hass)
        headers = {"token": self._token, "appCode": "Storcube", "Content-Type": "application/json"}
        
        new_global_data = {}
        
        try:
            # CHANGEMENT MAJEUR : On interroge la LISTE des appareils, pas le détail
            # C'est souvent là que les S1000 cachent leurs données réelles
            list_url = "http://baterway.com/api/equip/list"
            
            async with async_timeout.timeout(10):
                async with session.get(list_url, headers=headers) as resp:
                    res = await resp.json()
                    _LOGGER.debug("Réponse Liste Storcube: %s", res)

                    if res.get("code") == 200:
                        # On parcourt la liste des appareils renvoyés par le serveur
                        items = res.get("data", {}).get("list", [])
                        for item in items:
                            device_sn = str(item.get("deviceSn"))
                            # On stocke tout l'objet de l'appareil
                            new_global_data[device_sn] = item
                    
                    elif res.get("code") == 401:
                        self._token = None
                        
        except Exception as err:
            _LOGGER.error("Erreur lors de la récupération de la liste : %s", err)

        # Si la liste est vide ou ne contient pas nos IDs, on tente quand même le détail (fallback)
        if not new_global_data:
            return self.data

        return new_global_data

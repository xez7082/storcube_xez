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
    DOMAIN, ATTR_EXTRA_STATE, SCAN_INTERVAL_SECONDS, TIMEOUT_SECONDS,
    CONF_DEVICE_ID, CONF_LOGIN_NAME, CONF_AUTH_PASSWORD, TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.hass = hass
        self.entry = entry
        self._token: str | None = None
        self.data = {"soc": 0.0, "power": 0.0, "pv": 0.0, "online": False, ATTR_EXTRA_STATE: {}}

    async def _async_get_token(self) -> str | None:
        payload = {
            "loginName": self.entry.data.get(CONF_LOGIN_NAME),
            "password": self.entry.data.get(CONF_AUTH_PASSWORD),
            "appCode": "Storcube"
        }
        session = async_get_clientsession(self.hass)
        async with async_timeout.timeout(10):
            response = await session.post(TOKEN_URL, json=payload)
            res_data = await response.json()
            return res_data.get("data", {}).get("token")

    async def _async_update_data(self) -> dict[str, Any]:
        """Cette fonction va forcer l'affichage de l'ID dans une erreur système."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            raise Exception("Impossible de récupérer le Token - Vérifie tes identifiants")

        # ON FORCE LA DÉCOUVERTE
        session = async_get_clientsession(self.hass)
        url = "http://baterway.com/api/equip/user/list"
        
        async with session.get(url, headers={"token": self._token}) as resp:
            res = await resp.json()
            devices = res.get("data", [])
            
            if devices and isinstance(devices, list):
                # On construit le message avec TOUS les appareils trouvés
                output = []
                for d in devices:
                    output.append(f"[Nom: {d.get('aliasName')} | ID: {d.get('id')} | SN: {d.get('deviceSn')}]")
                
                final_msg = " / ".join(output)
                
                # ICI ON PROVOQUE L'ARRÊT CRITIQUE POUR LIRE LE MESSAGE
                _LOGGER.error("!!! RECHERCHE TERMINEE : VOIR L'ERREUR CI-DESSOUS !!!")
                raise Exception(f"TES IDENTIFIANTS REELS SONT ICI -> {final_msg}")
            else:
                raise Exception(f"AUCUN APPAREIL TROUVE. Réponse serveur: {res}")

        return self.data

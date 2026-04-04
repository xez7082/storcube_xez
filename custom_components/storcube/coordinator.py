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
    """Coordinateur pour StorCube : Récupère les données via l'API Cloud."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self._token: str | None = None
        self.data: dict[str, Any] = {}

    async def _async_get_token(self) -> str | None:
        """Récupère le token d'authentification."""
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)

        payload = {
            "loginName": login,
            "password": password,
            "appCode": "Storcube"
        }
        
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.post(TOKEN_URL, json=payload)
                res_data = await response.json()
                # Correction : le token est parfois dans data['token']
                token = res_data.get("data", {}).get("token")
                return token
        except Exception as e:
            _LOGGER.error("Erreur Token Storcube : %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Rafraîchissement périodique."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            raise UpdateFailed("Authentification Storcube échouée")

        session = async_get_clientsession(self.hass)
        headers = {
            "token": self._token, 
            "appCode": "Storcube",
            "Content-Type": "application/json"
        }
        
        # On récupère les IDs depuis les options ou les data
        device_ids = self.entry.data.get(CONF_DEVICE_IDS) or [self.entry.data.get("device_id")]
        new_global_data = {}

        for device_id in device_ids:
            if not device_id: continue
            
            try:
                # Tentative sur l'URL de détail
                url = f"http://baterway.com/api/equip/detail?device_id={device_id}"
                async with async_timeout.timeout(10):
                    async with session.get(url, headers=headers) as resp:
                        res = await resp.json()
                        
                        # LOG DE DEBUG IMPORTANT : 
                        # On va voir exactement ce que le serveur répond pour la S1000
                        _LOGGER.debug("Réponse brute Storcube pour %s: %s", device_id, res)

                        if res.get("code") == 200 and res.get("data") is not None:
                            # Si data est un entier (ex: 0), on essaie de voir si les infos 
                            # sont dans une autre clé du JSON
                            data_content = res["data"]
                            
                            if isinstance(data_content, dict):
                                new_global_data[str(device_id)] = data_content
                            else:
                                # Si le serveur renvoie 0, on crée un dictionnaire vide 
                                # pour éviter l'erreur dans sensor.py
                                new_global_data[str(device_id)] = {"status": "connected_but_no_data"}
                        
                        elif res.get("code") == 401: # Token expiré
                            self._token = None

            except Exception as err:
                _LOGGER.error("Erreur sur l'appareil %s : %s", device_id, err)

        if not new_global_data:
            return self.data
            
        return new_global_data

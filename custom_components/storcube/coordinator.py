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
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)
        payload = {"loginName": login, "password": password, "appCode": "Storcube"}
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.post(TOKEN_URL, json=payload)
                res_data = await response.json()
                token = res_data.get("data", {}).get("token")
                if token:
                    _LOGGER.debug("Token Cloud actualisé avec succès")
                return token
        except Exception as e:
            _LOGGER.debug("Le Cloud Storcube ne répond pas (Token): %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Méthode de récupération Cloud avec tests multi-points."""
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
        
        # Récupération des IDs configurés
        device_ids = self.entry.data.get(CONF_DEVICE_IDS)
        if not device_ids:
            device_ids = [self.entry.data.get("device_id")]

        for device_id in device_ids:
            if not device_id:
                continue

            # --- STRATÉGIE MULTI-URL POUR S1000 ---
            urls = [
                f"http://baterway.com/api/equip/getLatestData?device_id={device_id}",
                f"http://baterway.com/api/equip/detail?device_id={device_id}",
                f"http://baterway.com/api/equip/list" # Pour celle-ci on filtrera après
            ]

            for url in urls:
                try:
                    async with async_timeout.timeout(5):
                        async with session.get(url, headers=headers) as resp:
                            res = await resp.json()
                            
                            # Log visible en Orange dans HA pour voir quel URL répond quoi
                            endpoint = url.split('/')[-1].split('?')[0]
                            _LOGGER.warning("RETOUR S1000 [%s] pour %s: %s", endpoint, device_id, res)

                            if res.get("code") == 200:
                                data_content = res.get("data")
                                
                                # Cas 1: C'est un dictionnaire direct (getLatestData ou detail)
                                if isinstance(data_content, dict) and len(data_content) > 1:
                                    if str(device_id) not in self.data: self.data[str(device_id)] = {}
                                    self.data[str(device_id)].update(data_content)
                                    break # On a trouvé des données, on passe au device suivant

                                # Cas 2: C'est une liste (equip/list)
                                elif endpoint == "list" and isinstance(data_content, dict):
                                    items = data_content.get("list", [])
                                    for item in items:
                                        sn = str(item.get("deviceSn"))
                                        if sn == str(device_id):
                                            if sn not in self.data: self.data[sn] = {}
                                            self.data[sn].update(item)
                                            break
                except Exception as err:
                    _LOGGER.debug("Erreur sur l'URL %s : %s", url, err)
                    continue

        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        """Fusion des données reçues en temps réel via MQTT."""
        _LOGGER.debug("Mise à jour MQTT pour %s: %s", device_id, payload)
        
        if device_id not in self.data:
            self.data[device_id] = {}
        
        self.data[device_id].update(payload)
        
        # On signale à HA que les données ont changé pour rafraîchir les sensors
        self.async_set_updated_data(self.data)

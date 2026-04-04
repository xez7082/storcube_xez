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
    """Coordinateur pour StorCube : Récupère les données via l'API Cloud."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # On interroge le cloud toutes les X secondes (défini dans const.py)
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self._token: str | None = None
        
        # Stockage des données par device_id
        self.data: dict[str, Any] = {}

    async def _async_get_token(self) -> str | None:
        """Récupère le token d'authentification sur le Cloud."""
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)

        if not login or not password:
            _LOGGER.error("Identifiants manquants dans la configuration")
            return None

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
                token = res_data.get("data", {}).get("token")
                if token:
                    _LOGGER.debug("Token Storcube actualisé")
                    return token
        except Exception as e:
            _LOGGER.error("Erreur de connexion au Cloud Storcube pour le token : %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Rafraîchissement périodique via l'API Cloud."""
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
        
        # Récupération de la liste des IDs (Maître et Esclave)
        device_ids = self.entry.data.get(CONF_DEVICE_IDS, [])
        if not device_ids:
            # Fallback sur l'ID unique si la liste est vide
            device_ids = [self.entry.data.get("device_id")]

        new_global_data = {}

        for device_id in device_ids:
            if not device_id:
                continue
                
            try:
                # On interroge l'API de détail pour chaque batterie
                url = f"http://baterway.com/api/equip/detail?device_id={device_id}"
                async with async_timeout.timeout(10):
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            res = await resp.json()
                            if "data" in res:
                                # On stocke les données sous la clé de l'ID de l'appareil
                                new_global_data[device_id] = res["data"]
                                _LOGGER.debug("Données reçues pour %s: %s", device_id, res["data"])
            except Exception as err:
                _LOGGER.warning("Impossible de mettre à jour l'appareil %s : %s", device_id, err)
                # En cas d'erreur (ex: token expiré), on invalide le token pour le prochain cycle
                self._token = None

        # Si on a reçu des données, on met à jour le dictionnaire global
        if new_global_data:
            return new_global_data
        
        return self.data

    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """Conservé pour compatibilité, mais le Cloud est désormais prioritaire."""
        pass

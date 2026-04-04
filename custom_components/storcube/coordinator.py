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
    """Coordinateur pour StorCube : Gère le Cloud et le MQTT."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self._token: str | None = None
        
        # Initialisation avec des clés sécurisées pour éviter les erreurs d'affichage
        self.data: dict[str, Any] = {
            "soc": 0,
            "invPower": 0,
            "pv1power": 0,
            "pv2power": 0,
            "temp": 0,
            "online": False
        }

    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """Réception et traitement des messages MQTT (Temps Réel)."""
        _LOGGER.debug("MQTT REÇU : %s", payload)
        
        # Extraction si le payload est enveloppé dans une liste
        new_data = {}
        if isinstance(payload, dict):
            if "list" in payload and isinstance(payload["list"], list) and len(payload["list"]) > 0:
                new_data = payload["list"][0]
            else:
                new_data = payload

        if not new_data:
            return

        # --- MAPPING DE SÉCURITÉ ---
        # Si la batterie utilise des noms différents, on les convertit ici
        # Exemple : 'p_out' -> 'invPower', 'p_pv1' -> 'pv1power'
        mapping = {
            "p_out": "invPower",
            "p_pv1": "pv1power",
            "p_pv2": "pv2power",
            "battery_soc": "soc",
            "outputPower": "invPower",
            "pvPower": "pv1power"
        }

        for cloud_key, local_key in mapping.items():
            if cloud_key in new_data:
                new_data[local_key] = new_data[cloud_key]

        # Mise à jour des données globales
        self.data.update(new_data)
        
        # On force HA à mettre à jour les sensors immédiatement
        self.async_set_updated_data(self.data)
        _LOGGER.info("Capteurs Storcube mis à jour via MQTT")

    async def _async_get_token(self) -> str | None:
        """Récupère le token d'authentification sur le Cloud."""
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)

        if not login or not password:
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
                return token
        except Exception as e:
            _LOGGER.debug("Erreur Token (Optionnel si MQTT fonctionne) : %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Rafraîchissement périodique (Cloud)."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            return self.data

        session = async_get_clientsession(self.hass)
        headers = {"token": self._token, "appCode": "Storcube"}
        
        try:
            async with async_timeout.timeout(10):
                # On tente de récupérer la liste des équipements pour voir si des infos s'y trouvent
                async with session.get("http://baterway.com/api/equip/list", headers=headers) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        # Si le cloud contient des données, on les injecte
                        if "data" in res and isinstance(res["data"], list) and len(res["data"]) > 0:
                            self.data.update(res["data"][0])
        except Exception as err:
            _LOGGER.debug("Échec rafraîchissement Cloud : %s", err)

        return self.data

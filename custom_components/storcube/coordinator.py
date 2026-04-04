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
    DOMAIN, ATTR_EXTRA_STATE, SCAN_INTERVAL_SECONDS,
    CONF_LOGIN_NAME, CONF_AUTH_PASSWORD, TOKEN_URL,
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
        # On initialise avec les IDs trouvés par MQTT pour éviter les erreurs
        self.data = {"soc": 0.0, "power": 0.0, "pv": 0.0, "online": False, ATTR_EXTRA_STATE: {}}

    async def _async_get_token(self) -> str | None:
        """Récupère le token sur l'URL d'origine qui répondait."""
        payload = {
            "loginName": self.entry.data.get(CONF_LOGIN_NAME),
            "password": self.entry.data.get(CONF_AUTH_PASSWORD),
            "appCode": "Storcube"
        }
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                # On utilise TOKEN_URL des const (http://baterway.com/api/login ou similaire)
                response = await session.post(TOKEN_URL, json=payload)
                res_data = await response.json()
                token = res_data.get("data", {}).get("token")
                if token:
                    return token
                _LOGGER.warning("Le serveur n'a pas renvoyé de token, mais MQTT est actif.")
                return None
        except Exception as e:
            _LOGGER.debug("Echec optionnel du token: %s", e)
            return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération des données (Priorité MQTT si Cloud échoue)."""
        if not self._token:
            self._token = await self._async_get_token()

        # Si on n'a pas de token, on ne bloque pas tout, on laisse le MQTT travailler
        if not self._token:
            _LOGGER.debug("Mode MQTT pur (Pas de Cloud)")
            return self.data

        session = async_get_clientsession(self.hass)
        headers = {"token": self._token, "appCode": "Storcube"}
        
        # Test de l'endpoint qui a renvoyé 200 (même vide) au début
        try:
            async with session.get("http://baterway.com/api/equip/list", headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    _LOGGER.debug("Données Cloud reçues: %s", res)
                    # Ici tu peux ajouter la logique de parsing si res['data'] n'est plus vide
        except Exception:
            pass

        return self.data

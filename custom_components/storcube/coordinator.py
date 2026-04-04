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
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinateur pour StorCube : Gère le Cloud et le MQTT."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # On peut augmenter l'intervalle car le MQTT fera le travail en temps réel
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self._token: str | None = None
        
        # Initialisation avec des valeurs par défaut
        self.data: dict[str, Any] = {
            "soc": 0,
            "invPower": 0,
            "pv1power": 0,
            "pv2power": 0,
            "temp": 0,
            "online": False
        }

    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """
        Méthode appelée par __init__.py lors de la réception d'un message MQTT.
        C'est ici que tes 180W arrivent !
        """
        _LOGGER.debug("Mise à jour temps réel (MQTT) : %s", payload)
        
        # On fusionne les nouvelles données MQTT avec les données existantes
        # Si le payload est une liste (cas fréquent Storcube), on prend le premier élément
        if "list" in payload and isinstance(payload["list"], list) and len(payload["list"]) > 0:
            new_data = payload["list"][0]
        else:
            new_data = payload

        # Mise à jour du dictionnaire de données interne
        self.data.update(new_data)
        
        # CRUCIAL : Informe Home Assistant que les données ont changé pour rafraîchir les capteurs
        self.async_set_updated_data(self.data)

    async def _async_get_token(self) -> str | None:
        """Récupère le token d'authentification."""
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
                if token:
                    _LOGGER.info("Nouveau Token Cloud StorCube récupéré")
                    return token
        except Exception as e:
            _LOGGER.debug("Erreur lors de la récupération du token Cloud : %s", e)
        
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """
        Rafraîchissement périodique (Cloud).
        Si le Cloud échoue, on retourne les dernières données MQTT stockées.
        """
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            # Si pas de token, on ne lève pas d'erreur, on garde les données MQTT
            return self.data

        session = async_get_clientsession(self.hass)
        headers = {"token": self._token, "appCode": "Storcube"}
        
        try:
            async with async_timeout.timeout(10):
                # On essaie de récupérer le statut détaillé si l'ID est connu
                # (Adaptation selon ton besoin Cloud)
                async with session.get("http://baterway.com/api/equip/list", headers=headers) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        # Si des données utiles sont dans 'res', tu peux les merger ici :
                        # cloud_data = res.get("data", [{}])[0]
                        # self.data.update(cloud_data)
                        pass
        except Exception as err:
            _LOGGER.debug("Échec du rafraîchissement périodique Cloud : %s", err)

        return self.data

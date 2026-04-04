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
    CONF_LOGIN_NAME, CONF_AUTH_PASSWORD,
)

_LOGGER = logging.getLogger(__name__)

# Mise à jour des URLs vers le Cloud Global sécurisé
CLOUD_BASE = "https://api.storcube.com"
LOGIN_URL = f"{CLOUD_BASE}/api/v1/app/login" # Nouvelle URL de Login

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
        """Authentification sur le Cloud Global."""
        payload = {
            "loginName": self.entry.data.get(CONF_LOGIN_NAME),
            "password": self.entry.data.get(CONF_AUTH_PASSWORD),
            "appCode": "Storcube"
        }
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                # On force le Login sur le nouveau serveur
                response = await session.post(LOGIN_URL, json=payload)
                res_data = await response.json()
                token = res_data.get("data", {}).get("token")
                if token:
                    _LOGGER.debug("Nouveau Token Cloud récupéré")
                    return token
                _LOGGER.error("Réponse Login sans Token: %s", res_data)
                return None
        except Exception as e:
            _LOGGER.error("Erreur critique lors de l'auth: %s", e)
            return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération des données avec le nouveau Token."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            raise Exception("AUTHENTIFICATION ECHOUEE : Vérifiez Email/Mot de passe sur api.storcube.com")

        # Liste des endpoints Cloud 2.0
        endpoints = [
            f"{CLOUD_BASE}/api/v1/app/equip/list",
            f"{CLOUD_BASE}/api/v1/device/list",
            f"{CLOUD_BASE}/api/equip/list"
        ]
        
        session = async_get_clientsession(self.hass)
        
        for url in endpoints:
            try:
                headers = {
                    "token": self._token,
                    "appCode": "Storcube",
                    "User-Agent": "Dart/3.0 (dart:io)"
                }
                async with session.get(url, headers=headers, timeout=10) as resp:
                    res = await resp.json()
                    data_raw = res.get("data", [])
                    
                    # On extrait la liste
                    items = data_raw if isinstance(data_raw, list) else data_raw.get("list", []) if isinstance(data_raw, dict) else []
                    
                    if items and len(items) > 0:
                        output = []
                        for i in items:
                            oid = i.get('id') or i.get('deviceSn') or i.get('sn')
                            name = i.get('aliasName') or i.get('deviceName') or "Batterie"
                            output.append(f"[{name}: ID={oid}]")
                        
                        final_msg = " / ".join(output)
                        _LOGGER.error("!!! SUCCÈS CLOUD !!!")
                        raise Exception(f"TES IDENTIFIANTS SONT ENFIN ICI -> {final_msg}")
            except Exception as e:
                if "IDENTIFIANTS" in str(e): raise e
                continue

        raise Exception("COMPTE RECONNU MAIS LISTE VIDE. Est-ce que la batterie est bien visible dans l'App mobile ?")

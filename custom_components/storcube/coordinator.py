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
        """Récupère le token d'authentification."""
        payload = {
            "loginName": self.entry.data.get(CONF_LOGIN_NAME),
            "password": self.entry.data.get(CONF_AUTH_PASSWORD),
            "appCode": "Storcube"
        }
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.post(TOKEN_URL, json=payload)
                res_data = await response.json()
                return res_data.get("data", {}).get("token")
        except Exception as e:
            _LOGGER.error("Erreur de token : %s", e)
            return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Scan multi-endpoints pour trouver le chemin valide de ton compte."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            raise Exception("Échec d'authentification : vérifie tes identifiants.")

        # Liste des URLs à tester (certaines versions d'API utilisent /slb ou /app)
        paths_to_test = [
            "/api/slb/equip/user/list",
            "/api/app/equip/user/list",
            "/api/equip/list",
            "/api/equip/user/list" # Ton ancien qui faisait 404
        ]
        
        session = async_get_clientsession(self.hass)
        scan_results = []

        for path in paths_to_test:
            url = f"http://baterway.com{path}"
            try:
                async with session.get(url, headers={"token": self._token}, timeout=5) as resp:
                    res = await resp.json()
                    devices = res.get("data", [])
                    
                    if devices and isinstance(devices, list):
                        # VICTOIRE : On a trouvé des données !
                        output = []
                        for d in devices:
                            output.append(f"[Nom: {d.get('aliasName')} | ID: {d.get('id')} | SN: {d.get('deviceSn')}]")
                        
                        final_msg = " / ".join(output)
                        _LOGGER.error("!!! SCAN REUSSI SUR %s !!!", path)
                        raise Exception(f"TES IDENTIFIANTS REELS SONT ICI -> {final_msg}")
                    
                    scan_results.append(f"{path}: {resp.status} (Vide)")
            except Exception as e:
                if "TES IDENTIFIANTS" in str(e): raise e
                scan_results.append(f"{path}: Erreur {type(e).__name__}")

        # Si on arrive ici, c'est que rien n'a fonctionné
        raise Exception(f"ECHEC DU SCAN. Résultats : {', '.join(scan_results)}")

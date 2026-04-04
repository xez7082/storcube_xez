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
        """Scan des domaines Baterway et Storcube pour trouver tes appareils."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            raise Exception("Échec d'authentification.")

        # On teste les deux domaines possibles avec les endpoints les plus courants
        scanners = [
            {"base": "http://api.storcube.com", "path": "/api/device/list"},
            {"base": "http://api.storcube.com", "path": "/api/equip/list"},
            {"base": "http://api.storcube.com", "path": "/api/station/list"},
            {"base": "http://baterway.com", "path": "/api/device/list"},
            {"base": "http://baterway.com", "path": "/api/equip/list"},
        ]
        
        session = async_get_clientsession(self.hass)
        scan_results = []

        for scan in scanners:
            url = f"{scan['base']}{scan['path']}"
            try:
                # Ajout des headers complets pour simuler l'App
                headers = {"token": self._token, "appCode": "Storcube"}
                async with session.get(url, headers=headers, timeout=5) as resp:
                    res = await resp.json()
                    data_raw = res.get("data", [])
                    
                    # On cherche une liste d'appareils
                    items = data_raw if isinstance(data_raw, list) else data_raw.get("list", []) if isinstance(data_raw, dict) else []
                    
                    if items and len(items) > 0:
                        output = []
                        for i in items:
                            oid = i.get('id') or i.get('deviceSn') or i.get('sn')
                            name = i.get('aliasName') or i.get('deviceName') or "Batterie"
                            output.append(f"[{name}: ID={oid}]")
                        
                        final_msg = " / ".join(output)
                        _LOGGER.error("!!! VICTOIRE SUR %s !!!", url)
                        raise Exception(f"TES IDENTIFIANTS REELS SONT ICI -> {final_msg}")
                    
                    scan_results.append(f"{scan['path']}: {resp.status}")
            except Exception as e:
                if "TES IDENTIFIANTS" in str(e): raise e
                scan_results.append(f"{url}: Err")

        raise Exception(f"AUCUN APPAREIL TROUVE. Resultats : {', '.join(scan_results[:4])}")

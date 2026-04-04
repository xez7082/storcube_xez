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
        """Scan des endpoints 'Station' pour trouver tes batteries."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            raise Exception("Échec d'authentification.")

        # On teste les nouveaux endpoints utilisés par l'App récente
        paths_to_test = [
            "/api/station/list",
            "/api/station/user/list",
            "/api/slb/station/list",
            "/api/app/station/list"
        ]
        
        session = async_get_clientsession(self.hass)
        scan_results = []

        for path in paths_to_test:
            url = f"http://baterway.com{path}"
            try:
                async with session.get(url, headers={"token": self._token}, timeout=5) as resp:
                    res = await resp.json()
                    data_raw = res.get("data", [])
                    
                    # Support des deux formats : [item1, item2] OU {"list": [item1, item2]}
                    devices = data_raw if isinstance(data_raw, list) else data_raw.get("list", [])
                    
                    if devices and len(devices) > 0:
                        output = []
                        for d in devices:
                            # On récupère l'ID le plus probable
                            did = d.get('id') or d.get('stationId') or d.get('deviceSn')
                            name = d.get('aliasName') or d.get('stationName') or d.get('deviceName')
                            output.append(f"[{name}: ID={did}]")
                        
                        final_msg = " / ".join(output)
                        _LOGGER.error("!!! SCAN REUSSI SUR %s !!!", path)
                        raise Exception(f"TES IDENTIFIANTS REELS SONT ICI -> {final_msg}")
                    
                    scan_results.append(f"{path}: {resp.status} (Vide)")
            except Exception as e:
                if "TES IDENTIFIANTS" in str(e): raise e
                scan_results.append(f"{path}: Erreur {type(e).__name__}")

        raise Exception(f"ECHEC FINAL. Résultats : {', '.join(scan_results)}")

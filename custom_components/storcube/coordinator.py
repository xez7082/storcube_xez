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

# On revient sur le domaine qui répondait (baterway) mais avec le point d'entrée SLB (Europe)
BASE_URL = "http://baterway.com"
AUTH_URL = f"{BASE_URL}/api/v1/app/login"
LIST_URL = f"{BASE_URL}/api/slb/equip/user/list"

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
        """Authentification SLB."""
        payload = {
            "loginName": self.entry.data.get(CONF_LOGIN_NAME),
            "password": self.entry.data.get(CONF_AUTH_PASSWORD),
            "appCode": "Storcube"
        }
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                # On tente le login simple qui marchait au début
                response = await session.post(AUTH_URL, json=payload)
                res_data = await response.json()
                return res_data.get("data", {}).get("token")
        except Exception as e:
            _LOGGER.error("Erreur Auth: %s", e)
            return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération via le préfixe SLB (Smart Life Battery)."""
        if not self._token:
            self._token = await self._async_get_token()

        if not self._token:
            raise Exception("Échec de récupération du Token.")

        session = async_get_clientsession(self.hass)
        headers = {"token": self._token, "appCode": "Storcube"}
        
        # On teste le chemin SLB (Europe) et le chemin APP
        paths = ["/api/slb/equip/user/list", "/api/app/equip/user/list", "/api/equip/list"]
        
        for path in paths:
            url = f"{BASE_URL}{path}"
            try:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    res = await resp.json()
                    devices = res.get("data", [])
                    
                    if devices and isinstance(devices, list) and len(devices) > 0:
                        output = []
                        for d in devices:
                            did = d.get('id') or d.get('deviceSn')
                            name = d.get('aliasName') or d.get('deviceName')
                            output.append(f"[{name}: ID={did}]")
                        
                        final_msg = " / ".join(output)
                        raise Exception(f"VICTOIRE EUROPE -> {final_msg}")
            except Exception as e:
                if "VICTOIRE" in str(e): raise e
                continue

        raise Exception("AUTHENTIFIE MAIS APPAREIL INTROUVABLE. Vérifie ton ID dans l'App.")

"""Data Coordinator for Storcube Battery Monitor - Version Stable REST."""
from __future__ import annotations

import logging
import json
import asyncio
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_APP_CODE,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
    TOKEN_URL,
    OUTPUT_URL,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Gère la récupération des données via REST uniquement pour la stabilité."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self._auth_token: str | None = None
        self._device_id = str(entry.data[CONF_DEVICE_ID]).strip()
        
        self.data = {
            "soc": 0,
            "power": 0,
            "pv1": 0,
            "pv2": 0,
            "temp": 0,
            "is_online": False
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Mise à jour périodique."""
        try:
            if not self._auth_token:
                await self.async_renew_token()
            
            await self._update_rest_data()
            return self.data
        except Exception as err:
            raise UpdateFailed(f"Erreur Storcube : {err}")

    async def async_renew_token(self):
        """Récupère le token."""
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD]
        }
        async with self.session.post(TOKEN_URL, json=payload, timeout=10) as resp:
            if resp.status == 401:
                raise ConfigEntryAuthFailed("Identifiants invalides")
            res = await resp.json()
            if res.get("code") == 200:
                self._auth_token = res["data"]["token"]
                _LOGGER.info("Storcube: Token renouvelé")

    def _extract_values(self, source_data: dict[str, Any]):
        """Mapping des données."""
        # Logs pour identifier les nouvelles clés du solaire
        _LOGGER.debug("Data reçue pour %s: %s", self._device_id, source_data)

        # Batterie
        self.data["soc"] = float(source_data.get("reserved", self.data["soc"]))
        self.data["power"] = float(source_data.get("outputPower", self.data["power"]))
        
        # Tentatives pour le Solaire (chercher différentes clés possibles)
        pv_val = source_data.get("pvPower") or source_data.get("pvPower1") or source_data.get("ppv")
        if pv_val is not None:
            self.data["pv1"] = float(pv_val)

        # Statut
        online = source_data.get("fgOnline") or source_data.get("mainEquipOnline")
        if online is not None:
            self.data["is_online"] = (int(online) == 1)

    async def _update_rest_data(self):
        """Appel API."""
        if not self._auth_token: return
        headers = {"Authorization": self._auth_token, "appCode": "Storcube"}
        url = f"{OUTPUT_URL}{self._device_id}"
        
        async with self.session.get(url, headers=headers, timeout=10) as resp:
            res = await resp.json()
            if res.get("code") == 200 and "data" in res:
                raw = res["data"][0] if isinstance(res["data"], list) else res["data"]
                self._extract_values(raw)

    async def async_setup(self):
        """Pas de WebSocket, donc rien à faire ici."""
        pass

from __future__ import annotations

import logging
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
    DETAIL_URL,  # Assure-toi que DETAIL_URL finit par /status dans const.py
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Gère la récupération des données via l'API Status."""

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
            "soc": 0.0,
            "power": 0.0,
            "pv1": 0.0,
            "is_online": False,
            "extra": {} 
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    async def _async_update_data(self) -> dict[str, Any]:
        if not self._auth_token:
            await self.async_renew_token()
        
        await self._update_rest_data()
        return dict(self.data)

    async def async_renew_token(self):
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD]
        }
        try:
            async with self.session.post(TOKEN_URL, json=payload, timeout=10) as resp:
                res = await resp.json()
                if resp.status == 200 and res.get("code") == 200:
                    self._auth_token = res["data"]["token"]
                else:
                    raise UpdateFailed(f"Auth failed: {res.get('msg')}")
        except Exception as err:
            raise UpdateFailed(f"Erreur connexion auth: {err}")

    def _extract_values(self, raw_data: dict[str, Any]):
        """Extraction avec logs WARNING pour capture immédiate."""
        _LOGGER.warning("--- CONTENU DU BLOC DATA (ID: %s) ---", self._device_id)
        _LOGGER.warning(raw_data)
        
        self.data["extra"] = raw_data

        # Tentative sur plusieurs clés possibles
        self.data["soc"] = self._safe_float(
            raw_data.get("soc") or raw_data.get("batteryLevel") or raw_data.get("reserved"), 
            self.data["soc"]
        )
        self.data["power"] = self._safe_float(
            raw_data.get("outputPower") or raw_data.get("invPower") or raw_data.get("outPower"), 
            self.data["power"]
        )
        self.data["pv1"] = self._safe_float(
            raw_data.get("pvPower") or raw_data.get("pv1Power") or raw_data.get("ppv"), 
            self.data["pv1"]
        )
        
        online = raw_data.get("fgOnline") or raw_data.get("mainEquipOnline")
        self.data["is_online"] = (str(online) == "1")

    async def _update_rest_data(self):
        """Récupération via l'URL configurée."""
        if not self._auth_token:
            return

        headers = {
            "Authorization": self._auth_token,
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "Content-Type": "application/json"
        }
        
        url = f"{DETAIL_URL}{self._device_id}"
        
        try:
            async with self.session.get(url, headers=headers, timeout=15) as resp:
                res = await resp.json()
                
                # LOG DE SÉCURITÉ : On affiche TOUTE la réponse, quoi qu'il arrive
                _LOGGER.warning("REPONSE API COMPLETE (%s): %s", self._device_id, res)

                if resp.status == 200 and res.get("code") == 200:
                    data_block = res.get("data")
                    if data_block:
                        if isinstance(data_block, list) and len(data_block) > 0:
                            self._extract_values(data_block[0])
                        elif isinstance(data_block, dict):
                            self._extract_values(data_block)
                    else:
                        _LOGGER.error("Le serveur répond 200 mais le champ 'data' est vide.")
                elif resp.status == 401:
                    self._auth_token = None
        except Exception as e:
            _LOGGER.error("Erreur lors de la requête REST : %s", e)

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
    DETAIL_URL,  # On utilise DETAIL_URL au lieu de OUTPUT_URL
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Gère la récupération des données réelles via l'API Detail."""

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
        """Convertit en float de manière sécurisée."""
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    async def _async_update_data(self) -> dict[str, Any]:
        """Méthode principale de mise à jour."""
        try:
            if not self._auth_token:
                await self.async_renew_token()
            
            await self._update_rest_data()
            return dict(self.data)
            
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.error("Erreur Storcube (%s) : %s", self._device_id, err)
            raise UpdateFailed(f"Erreur de communication : {err}")

    async def async_renew_token(self):
        """Authentification."""
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD]
        }
        
        try:
            async with self.session.post(TOKEN_URL, json=payload, timeout=10) as resp:
                if resp.status == 401:
                    raise ConfigEntryAuthFailed("Identifiants incorrects")
                
                res = await resp.json()
                if res.get("code") == 200 and "data" in res:
                    self._auth_token = res["data"]["token"]
                else:
                    raise UpdateFailed(f"Auth fail: {res.get('msg')}")
        except asyncio.TimeoutError:
            raise UpdateFailed("Timeout auth")

    def _extract_values(self, raw_data: dict[str, Any]):
        """Mapping des données REELLES de l'API Detail."""
        
        _LOGGER.debug("Extraction des données réelles pour %s : %s", self._device_id, raw_data)
        self.data["extra"] = raw_data

        # Sur l'API Detail, les clés peuvent être différentes. 
        # On garde 'reserved' et 'soc' en secours, mais on ajoute les clés temps réel probables
        soc_val = raw_data.get("soc") or raw_data.get("reserved") or raw_data.get("batteryLevel")
        self.data["soc"] = self._safe_float(soc_val, self.data["soc"])

        # Puissance de sortie réelle
        out_val = raw_data.get("outputPower") or raw_data.get("invPower") or raw_data.get("outPower")
        self.data["power"] = self._safe_float(out_val, self.data["power"])

        # Solaire réel
        pv_val = raw_data.get("pvPower") or raw_data.get("pv1power") or raw_data.get("ppv")
        self.data["pv1"] = self._safe_float(pv_val, self.data["pv1"])

        # État
        online = raw_data.get("mainEquipOnline") or raw_data.get("fgOnline")
        self.data["is_online"] = (str(online) == "1")

    async def _update_rest_data(self):
        """Requête vers DETAIL_URL (Vraies données)."""
        if not self._auth_token:
            return

        headers = {
            "Authorization": self._auth_token,
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "Content-Type": "application/json"
        }
        
        # UTILISATION DE DETAIL_URL ICI
        url = f"{DETAIL_URL}{self._device_id}"
        
        try:
            async with self.session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    if res.get("code") == 200 and "data" in res:
                        payload = res["data"]
                        
                        # Detail renvoie généralement un objet direct, pas une liste
                        if isinstance(payload, dict):
                            self._extract_values(payload)
                        elif isinstance(payload, list) and len(payload) > 0:
                            self._extract_values(payload[0])
                    else:
                        _LOGGER.warning("API Detail : pas de données pour %s", self._device_id)
                
                elif resp.status == 401:
                    self._auth_token = None
                    
        except Exception as e:
            _LOGGER.error("Erreur API Detail : %s", e)

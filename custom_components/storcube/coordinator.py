"""Data Coordinator for Storcube Battery Monitor - Version Stable REST."""
from __future__ import annotations

import logging
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
    """Gère la récupération des données via REST uniquement."""

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
            "is_online": False,
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Conversion sécurisée en float."""
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    async def _async_update_data(self) -> dict[str, Any]:
        """Mise à jour périodique."""
        try:
            if not self._auth_token:
                await self.async_renew_token()
            
            await self._update_rest_data()
            return self.data
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Erreur Storcube ({self._device_id}) : {err}")

    async def async_renew_token(self):
        """Authentification et récupération du token."""
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD]
        }
        async with self.session.post(TOKEN_URL, json=payload, timeout=10) as resp:
            if resp.status == 401:
                self._auth_token = None
                raise ConfigEntryAuthFailed("Identifiants incorrects")
            
            res = await resp.json()
            if res.get("code") == 200:
                self._auth_token = res["data"]["token"]
                _LOGGER.info("Token Storcube mis à jour pour %s", self._device_id)
            else:
                _LOGGER.error("Erreur Auth Storcube : %s", res.get("msg"))

    def _extract_values(self, raw_data: dict[str, Any]):
        """Mapping basé sur les données réelles reçues (reserved=SOC, outputPower=Watts)."""
        
        _LOGGER.debug("Extraction pour %s : %s", self._device_id, raw_data)

        # 1. SOC (Batterie %)
        # On utilise 'reserved' en priorité car tes logs montrent que c'est là qu'est le 70%
        self.data["soc"] = self._safe_float(
            raw_data.get("reserved") or raw_data.get("soc"), 
            self.data["soc"]
        )

        # 2. Puissance de sortie (Décharge)
        # On utilise 'outputPower' qui affiche 150 dans tes logs
        self.data["power"] = self._safe_float(
            raw_data.get("outputPower") or raw_data.get("invPower"),
            self.data["power"]
        )

        # 3. Solaire (PV)
        # Actuellement absent du JSON, on garde des fallbacks au cas où l'API évolue
        pv_val = (
            raw_data.get("pvPower") or 
            raw_data.get("pv1power") or 
            raw_data.get("ppv")
        )
        self.data["pv1"] = self._safe_float(pv_val, self.data["pv1"])

        # 4. État
        online = raw_data.get("mainEquipOnline") or raw_data.get("fgOnline")
        if online is not None:
            self.data["is_online"] = (str(online) == "1")

    async def _update_rest_data(self):
        """Requête API."""
        if not self._auth_token:
            return

        headers = {
            "Authorization": self._auth_token,
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "Content-Type": "application/json"
        }
        
        # Note: Si le solaire reste à 0, il faudra peut-être modifier OUTPUT_URL 
        # dans const.py pour pointer vers une URL de détail.
        url = f"{OUTPUT_URL}{self._device_id}"
        
        try:
            async with self.session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    if res.get("code") == 200 and "data" in res:
                        payload = res["data"]
                        # On prend le premier élément si c'est une liste
                        raw = payload[0] if isinstance(payload, list) and len(payload) > 0 else payload
                        
                        if isinstance(raw, dict):
                            self._extract_values(raw)
                    else:
                        _LOGGER.warning("Réponse API anormale : %s", res.get("msg"))
                
                elif resp.status == 401:
                    self._auth_token = None
                    
        except Exception as e:
            _LOGGER.error("Erreur de connexion API Storcube : %s", e)

    async def async_setup(self):
        """Pas de WebSocket."""
        pass

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
    DETAIL_URL,
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
        """Authentification auprès de Baterway."""
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
                elif resp.status == 401:
                    raise ConfigEntryAuthFailed("Identifiants incorrects")
                else:
                    raise UpdateFailed(f"Auth fail: {res.get('msg')}")
        except asyncio.TimeoutError:
            raise UpdateFailed("Timeout lors de l'auth")

    def _extract_values(self, raw_data: dict[str, Any]):
        """Mapping intelligent des données réelles."""
        # Log en WARNING pour être sûr de voir passer les données dans la console HA
        _LOGGER.warning("--- DONNÉES BRUTES REÇUES (ID: %s) ---", self._device_id)
        _LOGGER.warning(raw_data)
        
        self.data["extra"] = raw_data

        # 1. SOC (Niveau batterie)
        # On teste les clés connues pour l'API Detail
        soc_val = raw_data.get("soc") or raw_data.get("batteryLevel") or raw_data.get("reserved")
        self.data["soc"] = self._safe_float(soc_val, self.data["soc"])

        # 2. Puissance de sortie (W)
        out_val = raw_data.get("outputPower") or raw_data.get("invPower") or raw_data.get("outPower")
        self.data["power"] = self._safe_float(out_val, self.data["power"])

        # 3. Solaire (W)
        pv_val = raw_data.get("pvPower") or raw_data.get("pv1Power") or raw_data.get("ppv")
        self.data["pv1"] = self._safe_float(pv_val, self.data["pv1"])

        # 4. État
        online = raw_data.get("fgOnline") or raw_data.get("mainEquipOnline")
        self.data["is_online"] = (str(online) == "1")

    async def _update_rest_data(self):
        """Appel de l'API Detail."""
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
                if resp.status == 200:
                    res = await resp.json()
                    data_block = res.get("data")
                    
                    if data_block:
                        # Si c'est une liste, on prend le premier
                        if isinstance(data_block, list) and len(data_block) > 0:
                            self._extract_values(data_block[0])
                        # Si c'est un dictionnaire direct
                        elif isinstance(data_block, dict):
                            self._extract_values(data_block)
                    else:
                        _LOGGER.error("Réponse vide de l'API Detail pour %s", self._device_id)
                
                elif resp.status == 401:
                    _LOGGER.warning("Token expiré pour %s, renouvellement au prochain cycle", self._device_id)
                    self._auth_token = None
                    
        except Exception as e:
            _LOGGER.error("Erreur critique lors de l'appel Detail : %s", e)

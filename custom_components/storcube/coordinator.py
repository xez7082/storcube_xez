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
        
        # Initialisation structurée pour sensor.py
        self.data = {
            "soc": 0,
            "power": 0,
            "pv1": 0,
            "pv2": 0,
            "temp": 0,
            "is_online": False,
            "extra": {} # Stockage des données brutes pour les capteurs spécifiques
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Convertit en float de manière sécurisée (gère None et chaînes vides)."""
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération périodique."""
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
        """Récupère un nouveau token d'authentification."""
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD]
        }
        async with self.session.post(TOKEN_URL, json=payload, timeout=10) as resp:
            if resp.status == 401:
                self._auth_token = None
                raise ConfigEntryAuthFailed("Identifiants Storcube incorrects")
            
            res = await resp.json()
            if res.get("code") == 200:
                self._auth_token = res["data"]["token"]
                _LOGGER.info("Storcube : Token renouvelé pour %s", self._device_id)
            else:
                _LOGGER.error("Erreur Auth Storcube : %s", res.get("msg"))

    def _extract_values(self, raw_data: dict[str, Any]):
        """Mapping intelligent basé sur les logs réels."""
        
        _LOGGER.debug("Extraction pour %s : %s", self._device_id, raw_data)
        
        # On sauvegarde les données brutes pour les sensors 'Test' ou 'Seuil'
        self.data["extra"] = raw_data

        # 1. Batterie (SOC) -> Utilise 'reserved' qui contient tes 70%
        soc_val = raw_data.get("reserved") or raw_data.get("soc")
        self.data["soc"] = self._safe_float(soc_val, self.data["soc"])

        # 2. Puissance Sortie (AC) -> Utilise 'outputPower' qui contient tes 150W
        out_val = raw_data.get("outputPower") or raw_data.get("invPower")
        self.data["power"] = self._safe_float(out_val, self.data["power"])

        # 3. Solaire (PV) -> Fallback au cas où l'ID 8075 envoie ces clés plus tard
        pv1_val = raw_data.get("pv1power") or raw_data.get("pvPower") or raw_data.get("ppv")
        self.data["pv1"] = self._safe_float(pv1_val, self.data.get("pv1", 0.0))

        # 4. État de connexion
        # 'fgOnline' ou 'mainEquipOnline' = 1 dans tes logs
        online = raw_data.get("mainEquipOnline") or raw_data.get("fgOnline")
        self.data["is_online"] = (str(online) == "1")

    async def _update_rest_data(self):
        """Requête HTTP vers l'API."""
        if not self._auth_token:
            return

        headers = {
            "Authorization": self._auth_token,
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "Content-Type": "application/json"
        }
        
        url = f"{OUTPUT_URL}{self._device_id}"
        
        try:
            async with self.session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    if res.get("code") == 200 and "data" in res:
                        data_payload = res["data"]
                        # L'API renvoie souvent une liste [ {} ]
                        raw = data_payload[0] if isinstance(data_payload, list) and len(data_payload) > 0 else data_payload
                        
                        if isinstance(raw, dict):
                            self._extract_values(raw)
                    else:
                        _LOGGER.warning("Réponse API vide ou erronée pour %s", self._device_id)
                
                elif resp.status == 401:
                    _LOGGER.warning("Session expirée pour %s", self._device_id)
                    self._auth_token = None
                    
        except Exception as e:
            _LOGGER.error("Erreur REST pour %s : %s", self._device_id, e)

    async def async_setup(self):
        """Initialisation."""
        pass

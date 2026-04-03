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
    """Gère la récupération des données via REST uniquement (Stabilité maximale)."""

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
        """Convertit en float de manière sécurisée."""
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération périodique des données."""
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
                _LOGGER.info("Storcube : Token renouvelé pour l'appareil %s", self._device_id)
            else:
                _LOGGER.error("Échec auth Storcube : %s", res.get("msg"))

    def _extract_values(self, raw_data: dict[str, Any]):
        """Mapping des données avec logs de diagnostic."""
        
        # LOG DE DIAGNOSTIC : À consulter si les valeurs restent à 0
        _LOGGER.debug("Données reçues pour %s : %s", self._device_id, raw_data)

        # 1. Batterie (SOC)
        self.data["soc"] = self._safe_float(
            raw_data.get("soc") or raw_data.get("reserved"), self.data["soc"]
        )

        # 2. Puissance Sortie (AC)
        self.data["power"] = self._safe_float(
            raw_data.get("invPower") or raw_data.get("totalInvPower") or raw_data.get("outputPower"),
            self.data["power"]
        )

        # 3. Solaire (PV1 & PV2)
        # On tente de mapper PV1 avec plusieurs clés possibles
        pv1_val = raw_data.get("pv1power") or raw_data.get("totalPv1power") or raw_data.get("pvPower")
        self.data["pv1"] = self._safe_float(pv1_val, self.data["pv1"])
        
        pv2_val = raw_data.get("pv2power") or raw_data.get("totalPv2power")
        self.data["pv2"] = self._safe_float(pv2_val, self.data["pv2"])

        # 4. Température
        self.data["temp"] = self._safe_float(
            raw_data.get("temp") or raw_data.get("temperature"), self.data["temp"]
        )

        # 5. État de connexion
        online = raw_data.get("mainEquipOnline") or raw_data.get("fgOnline") or raw_data.get("isWork")
        if online is not None:
            self.data["is_online"] = (str(online) == "1")

    async def _update_rest_data(self):
        """Appel API REST."""
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
                        # Gestion de la liste ou de l'objet direct
                        data_payload = res["data"]
                        raw = data_payload[0] if isinstance(data_payload, list) and len(data_payload) > 0 else data_payload
                        
                        if isinstance(raw, dict):
                            self._extract_values(raw)
                    else:
                        _LOGGER.warning("Réponse API anormale (%s) : %s", self._device_id, res.get("msg"))
                
                elif resp.status == 401:
                    _LOGGER.warning("Token expiré pour %s, renouvellement au prochain tour", self._device_id)
                    self._auth_token = None
                    
        except Exception as e:
            _LOGGER.error("Erreur de requête REST pour %s : %s", self._device_id, e)

    async def async_setup(self):
        """Initialisation sans WebSocket."""
        pass

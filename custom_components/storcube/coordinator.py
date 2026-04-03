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
        
        # Initialisation du dictionnaire de données
        self.data = {
            "soc": 0,
            "power": 0,
            "pv1": 0,
            "pv2": 0,
            "temp": 0,
            "is_online": False,
            "raw_debug": "" # Pour aider au diagnostic
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération des données."""
        try:
            if not self._auth_token:
                await self.async_renew_token()
            
            await self._update_rest_data()
            return self.data
        except Exception as err:
            # Si erreur 401 ou token expiré, on force le renouvellement au prochain tour
            if "401" in str(err):
                self._auth_token = None
            raise UpdateFailed(f"Erreur de communication Storcube : {err}")

    async def async_renew_token(self):
        """Récupère un nouveau token d'authentification."""
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD]
        }
        async with self.session.post(TOKEN_URL, json=payload, timeout=10) as resp:
            if resp.status == 401:
                raise ConfigEntryAuthFailed("Identifiants Storcube incorrects")
            
            res = await resp.json()
            if res.get("code") == 200:
                self._auth_token = res["data"]["token"]
                _LOGGER.info("Storcube : Token renouvelé avec succès")
            else:
                _LOGGER.error("Erreur lors du renouvellement du token : %s", res.get("msg"))

    def _extract_values(self, raw_data: dict[str, Any]):
        """Mapping intelligent des données basé sur les clés réelles de l'appareil."""
        _LOGGER.debug("Extraction des données pour l'ID %s", self._device_id)

        # 1. Niveau de Batterie (SOC)
        # On cherche 'soc', sinon 'reserved' (souvent utilisé comme seuil ou niveau)
        soc = raw_data.get("soc") or raw_data.get("reserved")
        if soc is not None:
            self.data["soc"] = float(soc)

        # 2. Puissance de Sortie (AC Power)
        # 'invPower' est la clé standard pour l'onduleur dans Storcube
        out_power = raw_data.get("invPower") or raw_data.get("totalInvPower") or raw_data.get("outputPower")
        if out_power is not None:
            self.data["power"] = float(out_power)

        # 3. Solaire Panneau 1
        pv1 = raw_data.get("pv1power") or raw_data.get("totalPv1power") or raw_data.get("pvPower")
        if pv1 is not None:
            self.data["pv1"] = float(pv1)

        # 4. Solaire Panneau 2
        pv2 = raw_data.get("pv2power") or raw_data.get("totalPv2power")
        if pv2 is not None:
            self.data["pv2"] = float(pv2)

        # 5. Température
        temp = raw_data.get("temp") or raw_data.get("temperature")
        if temp is not None:
            self.data["temp"] = float(temp)

        # 6. État de connexion
        online = raw_data.get("mainEquipOnline") or raw_data.get("fgOnline") or raw_data.get("isWork")
        if online is not None:
            self.data["is_online"] = (int(online) == 1)

    async def _update_rest_data(self):
        """Exécute la requête HTTP vers l'API Storcube."""
        if not self._auth_token:
            return

        headers = {
            "Authorization": self._auth_token,
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "Content-Type": "application/json"
        }
        
        url = f"{OUTPUT_URL}{self._device_id}"
        
        async with self.session.get(url, headers=headers, timeout=15) as resp:
            if resp.status == 200:
                res = await resp.json()
                if res.get("code") == 200 and "data" in res:
                    # L'API renvoie souvent une liste d'un seul élément
                    raw = res["data"][0] if isinstance(res["data"], list) and len(res["data"]) > 0 else res["data"]
                    if raw:
                        self._extract_values(raw)
                else:
                    _LOGGER.warning("Réponse API Storcube inattendue : %s", res.get("msg"))
            elif resp.status == 401:
                _LOGGER.warning("Token expiré, tentative de renouvellement au prochain cycle")
                self._auth_token = None

    async def async_setup(self):
        """Initialisation optionnelle."""
        pass

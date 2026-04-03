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
    OUTPUT_URL,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Gère la récupération des données via REST uniquement (Version Stable)."""

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
        # IMPORTANT : Ces clés doivent correspondre à ce que sensor.py appelle
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
        """Méthode principale appelée par Home Assistant selon SCAN_INTERVAL."""
        try:
            # 1. Vérifier/Renouveler le token si nécessaire
            if not self._auth_token:
                await self.async_renew_token()
            
            # 2. Récupérer les données
            await self._update_rest_data()
            
            # On retourne une copie pour déclencher la mise à jour des entités
            return dict(self.data)
            
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.error("Erreur Storcube (%s) : %s", self._device_id, err)
            raise UpdateFailed(f"Erreur de communication : {err}")

    async def async_renew_token(self):
        """Authentification auprès de l'API Baterway."""
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD]
        }
        
        try:
            async with self.session.post(TOKEN_URL, json=payload, timeout=10) as resp:
                if resp.status == 401:
                    raise ConfigEntryAuthFailed("Identifiants Storcube invalides")
                
                res = await resp.json()
                if res.get("code") == 200 and "data" in res:
                    self._auth_token = res["data"]["token"]
                    _LOGGER.info("Storcube : Token rafraîchi avec succès")
                else:
                    msg = res.get("msg", "Erreur inconnue")
                    _LOGGER.error("Échec d'authentification : %s", msg)
                    raise UpdateFailed(f"Auth fail: {msg}")
        except asyncio.TimeoutError:
            raise UpdateFailed("Délai d'attente dépassé lors de l'authentification")

    def _extract_values(self, raw_data: dict[str, Any]):
        """Mapping des clés API vers les variables Home Assistant."""
        
        _LOGGER.debug("Données brutes reçues : %s", raw_data)
        
        # Stockage brut pour diagnostic
        self.data["extra"] = raw_data

        # 1. SOC (Batterie) -> Utilise 'reserved' (70%)
        # On essaie 'reserved', sinon 'soc', sinon on garde l'ancienne valeur
        soc_val = raw_data.get("reserved") if raw_data.get("reserved") is not None else raw_data.get("soc")
        self.data["soc"] = self._safe_float(soc_val, self.data["soc"])

        # 2. Puissance Sortie -> Utilise 'outputPower' (150W)
        out_val = raw_data.get("outputPower") if raw_data.get("outputPower") is not None else raw_data.get("invPower")
        self.data["power"] = self._safe_float(out_val, self.data["power"])

        # 3. Solaire PV -> Mapping flexible
        pv_val = raw_data.get("pv1power") or raw_data.get("pvPower") or raw_data.get("ppv")
        self.data["pv1"] = self._safe_float(pv_val, self.data["pv1"])

        # 4. État en ligne -> 1 = Online
        online = raw_data.get("mainEquipOnline") or raw_data.get("fgOnline")
        self.data["is_online"] = (str(online) == "1")

    async def _update_rest_data(self):
        """Exécute la requête de récupération des données de l'appareil."""
        if not self._auth_token:
            return

        headers = {
            "Authorization": self._auth_token,
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "Content-Type": "application/json"
        }
        
        # L'URL finale ressemble à : http://.../V2/ID_APPAREIL
        url = f"{OUTPUT_URL}{self._device_id}"
        
        try:
            async with self.session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    if res.get("code") == 200 and "data" in res:
                        payload = res["data"]
                        
                        # Si l'API renvoie une liste, on prend le premier élément
                        if isinstance(payload, list) and len(payload) > 0:
                            self._extract_values(payload[0])
                        elif isinstance(payload, dict):
                            self._extract_values(payload)
                    else:
                        _LOGGER.warning("Réponse API anormale : %s", res)
                
                elif resp.status == 401:
                    _LOGGER.warning("Session expirée, le token sera renouvelé au prochain cycle")
                    self._auth_token = None
                    
        except Exception as e:
            _LOGGER.error("Erreur lors de l'appel API REST : %s", e)

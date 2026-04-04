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
    DOMAIN,
    PAYLOAD_KEY_SOC,
    PAYLOAD_KEY_POWER,
    PAYLOAD_KEY_PV,
    ATTR_EXTRA_STATE,
    SCAN_INTERVAL_SECONDS,
    TIMEOUT_SECONDS,
    DETAIL_URL,
    CONF_DEVICE_ID,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
    TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinateur hybride : Cloud (Polling) + MQTT (Push)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )

        self.hass = hass
        self.entry = entry
        self._device_id = entry.data.get(CONF_DEVICE_ID)
        self._token: str | None = None

        self.data = {
            "soc": 0.0,
            "power": 0.0,
            "pv": 0.0,
            "online": False,
            ATTR_EXTRA_STATE: {},
        }

    async def _async_get_token(self) -> str | None:
        """Récupère le token d'authentification Storcube."""
        try:
            payload = {
                "loginName": self.entry.data.get(CONF_LOGIN_NAME),
                "password": self.entry.data.get(CONF_AUTH_PASSWORD),
                "appCode": "Storcube"
            }
            session = async_get_clientsession(self.hass)
            async with async_timeout.timeout(10):
                response = await session.post(TOKEN_URL, json=payload)
                res_data = await response.json()
                
                # Vérification du code de retour API (200 = Succès)
                if res_data.get("code") != 200:
                    _LOGGER.error("Erreur login API : %s", res_data.get("msg", "Inconnu"))
                    return None

                token = res_data.get("data", {}).get("token")
                if token:
                    _LOGGER.info("Nouveau token Storcube récupéré avec succès")
                    return str(token)
                
                return None
        except Exception:
            _LOGGER.exception("Erreur critique lors de l'authentification :")
            return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération des données via l'API REST (Polling)."""
        if not self._device_id:
            return self.data

        # 1. Gestion du Token
        if not self._token:
            self._token = await self._async_get_token()
            if not self._token:
                return self.data

        # 2. Appel à l'URL DETAIL
        url = f"{DETAIL_URL}{self._device_id}"
        
        headers = {
            "Authorization": f"Bearer {self._token}",
            "token": self._token
        }
        
        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                session = async_get_clientsession(self.hass)
                response = await session.get(url, headers=headers)
                
                if response.status == 401:
                    _LOGGER.warning("Token expiré, sera renouvelé au prochain cycle")
                    self._token = None
                    return self.data

                if response.status != 200:
                    _LOGGER.debug("Serveur injoignable (Status: %s)", response.status)
                    return self.data

                payload = await response.json()
                
                # Log de débogage pour voir la structure reçue
                _LOGGER.debug("Données reçues pour %s: %s", self._device_id, payload)

                data_part = payload.get("data")
                
                # Validation : on ne parse que si 'data' est un dictionnaire
                if isinstance(data_part, dict):
                    self._parse_payload(data_part)
                elif isinstance(payload, dict) and PAYLOAD_KEY_SOC in payload:
                    self._parse_payload(payload)
                else:
                    _LOGGER.debug("Réponse vide ou incorrecte (data: %s)", data_part)
                
                return self.data

        except Exception as err:
            _LOGGER.debug("Erreur lors de la récupération des données : %s", err)
            return self.data

    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """Mise à jour poussée par MQTT."""
        self._parse_payload(payload)
        self.async_set_updated_data(self.data)

    def _parse_payload(self, payload: dict[str, Any]) -> None:
        """Extraction et conversion des valeurs."""
        if not payload or not isinstance(payload, dict):
            return

        self.data[ATTR_EXTRA_STATE] = payload
        self.data["soc"] = self._to_float(payload.get(PAYLOAD_KEY_SOC), self.data["soc"])
        self.data["power"] = self._to_float(payload.get(PAYLOAD_KEY_POWER), self.data["power"])
        self.data["pv"] = self._to_float(payload.get(PAYLOAD_KEY_PV), self.data["pv"])

        # Gestion de l'état en ligne (plusieurs variantes de clés possibles)
        online_val = payload.get("online") or payload.get("fgOnline")
        if online_val is not None:
            self.data["online"] = str(online_val).lower() in ("1", "true", "yes", "on", "online")

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        """Conversion sécurisée en nombre flottant."""
        try:
            if value in (None, ""): 
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

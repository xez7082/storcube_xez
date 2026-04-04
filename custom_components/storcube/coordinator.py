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
    DETAIL_URL,  # On utilise DETAIL_URL maintenant
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
                token = res_data.get("data", {}).get("token")
                if token:
                    return str(token)
                return None
        except Exception as err:
            _LOGGER.error("Erreur d'authentification : %s", err)
            return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération des données via l'API REST (Polling)."""
        if not self._device_id:
            return self.data

        if not self._token:
            self._token = await self._async_get_token()

        # CHANGEMENT ICI : On utilise DETAIL_URL pour avoir les données réelles
        url = f"{DETAIL_URL}{self._device_id}"
        
        headers = {
            "Authorization": f"Bearer {self._token}" if self._token else "",
            "token": self._token if self._token else ""
        }
        
        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                session = async_get_clientsession(self.hass)
                response = await session.get(url, headers=headers)
                
                if response.status == 401:
                    self._token = None
                    return self.data

                if response.status != 200:
                    return self.data

                payload = await response.json()
                _LOGGER.debug("Réponse DETAIL pour %s: %s", self._device_id, payload)

                data_part = payload.get("data")
                # Si data_part est un dict, c'est ce qu'on veut. 
                # Si c'est 0 ou None, on garde les anciennes données.
                if isinstance(data_part, dict):
                    self._parse_payload(data_part)
                elif isinstance(payload, dict) and "soc" in payload:
                    self._parse_payload(payload)
                
                return self.data

        except Exception as err:
            _LOGGER.debug("Erreur polling pour %s: %s", self._device_id, err)
            return self.data

    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """MQTT Push."""
        self._parse_payload(payload)
        self.async_set_updated_data(self.data)

    def _parse_payload(self, payload: dict[str, Any]) -> None:
        """Extrait les valeurs du JSON."""
        if not payload or not isinstance(payload, dict):
            return

        self.data[ATTR_EXTRA_STATE] = payload
        self.data["soc"] = self._to_float(payload.get(PAYLOAD_KEY_SOC), self.data["soc"])
        self.data["power"] = self._to_float(payload.get(PAYLOAD_KEY_POWER), self.data["power"])
        self.data["pv"] = self._to_float(payload.get(PAYLOAD_KEY_PV), self.data["pv"])

        online_val = payload.get("online") or payload.get("fgOnline")
        if online_val is not None:
            self.data["online"] = str(online_val).lower() in ("1", "true", "yes", "on", "online")

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value in (None, ""): return default
            return float(value)
        except (TypeError, ValueError):
            return default

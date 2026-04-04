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
    """Coordinateur avec fonction de découverte pour résoudre le problème 'data: 0'."""

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
        """Récupère le token d'authentification."""
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
        except Exception:
            _LOGGER.exception("Erreur lors de la récupération du token")
            return None

    async def _async_discover_devices(self):
        """Récupère la liste réelle des équipements pour trouver le bon ID."""
        url = "http://baterway.com/api/equip/user/list"
        headers = {"token": self._token}
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                _LOGGER.error("--- DISCOVERY : Liste des IDs valides sur ce compte ---")
                _LOGGER.error(data)
                _LOGGER.error("-------------------------------------------------------")
        except Exception as err:
            _LOGGER.error("Erreur découverte : %s", err)

    async def _async_update_data(self) -> dict[str, Any]:
        """Mise à jour des données."""
        if not self._token:
            self._token = await self._async_get_token()
            if self._token:
                # On lance la découverte une seule fois pour voir les vrais IDs dans les logs
                await self._async_discover_devices()
            else:
                return self.data

        url = f"{DETAIL_URL}{self._device_id}"
        headers = {"token": self._token, "Content-Type": "application/json"}
        
        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                session = async_get_clientsession(self.hass)
                response = await session.get(url, headers=headers)
                payload = await response.json()
                
                # Debug de la réponse
                _LOGGER.debug("Réponse pour %s: %s", self._device_id, payload)

                data_part = payload.get("data")
                if isinstance(data_part, dict):
                    self._parse_payload(data_part)
                else:
                    _LOGGER.warning("L'ID %s renvoie 'data: 0'. Vérifiez les logs ERROR pour l'ID correct.", self._device_id)
                
                return self.data
        except Exception as err:
            _LOGGER.debug("Erreur API : %s", err)
            return self.data

    def update_from_ws(self, payload: dict[str, Any]) -> None:
        self._parse_payload(payload)
        self.async_set_updated_data(self.data)

    def _parse_payload(self, payload: dict[str, Any]) -> None:
        self.data[ATTR_EXTRA_STATE] = payload
        self.data["soc"] = self._to_float(payload.get(PAYLOAD_KEY_SOC), self.data["soc"])
        self.data["power"] = self._to_float(payload.get(PAYLOAD_KEY_POWER), self.data["power"])
        self.data["pv"] = self._to_float(payload.get(PAYLOAD_KEY_PV), self.data["pv"])
        online_val = payload.get("online") or payload.get("fgOnline")
        if online_val is not None:
            self.data["online"] = str(online_val).lower() in ("1", "true", "yes", "on", "online")

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value) if value not in (None, "") else default
        except (TypeError, ValueError):
            return default

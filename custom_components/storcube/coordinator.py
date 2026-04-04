from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import async_timeout
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    PAYLOAD_KEY_SOC,
    PAYLOAD_KEY_POWER,
    PAYLOAD_KEY_PV,
    ATTR_EXTRA_STATE,
    SCAN_INTERVAL_SECONDS,
    TIMEOUT_SECONDS,
    STATUS_URL,
    CONF_DEVICE_ID,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinateur hybride : Push (MQTT) et Polling (API REST)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # On active un rafraîchissement toutes les 30s en secours
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )

        self.hass = hass
        self.entry = entry
        self._device_id = entry.data.get(CONF_DEVICE_ID)

        # État interne initial
        self.data = {
            "soc": 0.0,
            "power": 0.0,
            "pv": 0.0,
            "online": False,
            ATTR_EXTRA_STATE: {},
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération des données via l'API REST (Fallback)."""
        if not self._device_id:
            return self.data

        url = f"{STATUS_URL}{self._device_id}"
        
        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                session = self.hass.helpers.aiohttp_client.async_get_clientsession()
                response = await session.get(url)
                
                if response.status != 200:
                    _LOGGER.warning("Serveur Storcube injoignable (Status: %s)", response.status)
                    return self.data

                payload = await response.json()
                # On traite le JSON reçu du cloud comme s'il venait de MQTT
                self._parse_payload(payload.get("data", payload))
                
                return self.data

        except Exception as err:
            _LOGGER.debug("Le Cloud n'a pas répondu, on garde les valeurs MQTT : %s", err)
            return self.data

    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """Point d'entrée pour les messages poussés par MQTT."""
        _LOGGER.debug("Réception MQTT pour %s", self._device_id)
        self._parse_payload(payload)
        # Notification immédiate à HA (sans attendre les 30s)
        self.async_set_updated_data(self.data)

    def _parse_payload(self, payload: dict[str, Any]) -> None:
        """Logique commune de parsing (Cloud et MQTT)."""
        if not isinstance(payload, dict):
            return

        try:
            self.data[ATTR_EXTRA_STATE] = payload

            # Extraction des valeurs
            self.data["soc"] = self._to_float(payload.get(PAYLOAD_KEY_SOC), self.data["soc"])
            self.data["power"] = self._to_float(payload.get(PAYLOAD_KEY_POWER), self.data["power"])
            self.data["pv"] = self._to_float(payload.get(PAYLOAD_KEY_PV), self.data["pv"])

            # Etat Online
            online_val = payload.get("online") or payload.get("fgOnline")
            if online_val is not None:
                self.data["online"] = str(online_val).lower() in ("1", "true", "yes", "on", "online")

        except Exception as err:
            _LOGGER.error("Erreur de parsing : %s", err)

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

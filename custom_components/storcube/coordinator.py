from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Storcube coordinator (SAFE VERSION)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="storcube",
            update_interval=None,  # MQTT / push only (pas de polling)
        )

        self.hass = hass
        self.entry = entry
        self.session = async_get_clientsession(hass)

        self.data: dict[str, Any] = {
            "soc": 0.0,
            "power": 0.0,
            "pv": 0.0,
            "online": False,
            "raw": {},
        }

    async def _async_update_data(self):
        """No polling (MQTT / WS future)."""
        return self.data

    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """Call this when receiving data (WS/MQTT later)."""
        try:
            self.data["raw"] = payload

            self.data["soc"] = float(payload.get("soc", 0) or 0)
            self.data["power"] = float(payload.get("outputPower", 0) or 0)
            self.data["pv"] = float(payload.get("pvPower", 0) or 0)

            online = payload.get("online") or payload.get("fgOnline")
            self.data["online"] = str(online) in ("1", "true", "True")

            self.async_set_updated_data(dict(self.data))

        except Exception as err:
            _LOGGER.error("Parse error: %s", err)

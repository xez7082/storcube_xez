from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """StorCube coordinator (MQTT / WS push only)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="storcube",
            update_interval=None,  # push only
        )

        self.hass = hass
        self.entry = entry

        # 🔥 IMPORTANT : utiliser self.data (pas self._data)
        self.data: dict[str, Any] = {
            "soc": 0.0,
            "power": 0.0,
            "pv": 0.0,
            "online": False,
            "raw": {},
        }

    async def _async_update_data(self):
        """
        No polling mode.
        Data updated only via update_from_ws().
        """
        return self.data

    # =========================================================
    # ENTRY POINT MQTT / WS
    # =========================================================
    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """Push new data from MQTT / WebSocket."""

        try:
            # store raw payload
            self.data["raw"] = payload

            # values mapping
            self.data["soc"] = self._to_float(payload.get("soc"))
            self.data["power"] = self._to_float(payload.get("outputPower"))
            self.data["pv"] = self._to_float(payload.get("pvPower"))

            # online detection
            online = payload.get("online") or payload.get("fgOnline")
            self.data["online"] = str(online).lower() in ("1", "true", "yes", "on")

            # 🔥 PUSH UPDATE TO HOME ASSISTANT
            self.async_set_updated_data(dict(self.data))

        except Exception as err:
            _LOGGER.exception("StorCube parse error: %s", err)

    # =========================================================
    # SAFE CONVERTER
    # =========================================================
    def _to_float(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

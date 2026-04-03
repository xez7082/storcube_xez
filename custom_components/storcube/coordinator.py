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

        # 🔥 INTERNAL STATE (IMPORTANT FIX)
        self._data: dict[str, Any] = {
            "soc": 0.0,
            "power": 0.0,
            "pv": 0.0,
            "online": False,
            "raw": {},
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """
        No polling mode.
        Data is only updated via MQTT / WS callback.
        """
        return self._data

    # =========================================================
    # MQTT / WS ENTRY POINT
    # =========================================================
    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """Push new data from MQTT / WebSocket."""

        try:
            # store raw payload
            self._data["raw"] = payload

            # mapping safe
            self._data["soc"] = self._to_float(payload.get("soc"))
            self._data["power"] = self._to_float(payload.get("outputPower"))
            self._data["pv"] = self._to_float(payload.get("pvPower"))

            # online detection safe
            online = payload.get("online") or payload.get("fgOnline")
            self._data["online"] = str(online).lower() in (
                "1", "true", "yes", "on"
            )

            # 🔥 PUSH UPDATE TO HOME ASSISTANT
            self.async_set_updated_data(dict(self._data))

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

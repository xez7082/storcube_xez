from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name="storcube",
            update_interval=timedelta(seconds=30),
        )
        self.data: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """On ne fait plus de requêtes Cloud pour éviter les erreurs DNS."""
        # On garde simplement les dernières données reçues par MQTT
        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        """C'est ici que tout va se passer."""
        _LOGGER.warning("DONNÉE REÇUE PAR MQTT pour %s: %s", device_id, payload)
        
        if device_id not in self.data:
            self.data[device_id] = {}
        
        self.data[device_id].update(payload)
        self.async_set_updated_data(self.data)

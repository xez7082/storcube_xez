from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, entry):
        super().__init__(
            hass, _LOGGER, name="storcube",
            update_interval=timedelta(minutes=5), # On espace les vérifications
        )
        self.data: dict[str, Any] = {}

    async def _async_update_data(self):
        """Mode attente passive : ne fait aucune requête pour éviter les blocages."""
        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]):
        """Si jamais la batterie envoie un message MQTT, on le capture ici."""
        if device_id not in self.data:
            self.data[device_id] = {}
        self.data[device_id].update(payload)
        _LOGGER.warning("Réveil MQTT détecté pour %s !", device_id)
        self.async_set_updated_data(self.data)

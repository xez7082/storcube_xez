from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name="storcube",
            update_interval=timedelta(seconds=30),
        )
        self.data: dict[str, Any] = {}
        # ON FORCE L'IP DE TA BATTERIE ICI
        self.device_ip = "192.168.1.190" 
        self.device_sn = "9105231027496254"

    async def _async_update_data(self) -> dict[str, Any]:
        """Tentative de lecture DIRECTE sur l'IP de la batterie."""
        session = async_get_clientsession(self.hass)
        
        # On teste les deux chemins locaux connus pour les S1000
        urls = [
            f"http://{self.device_ip}/rpc/GetStatus",
            f"http://{self.device_ip}/status",
            f"http://{self.device_ip}/api/status"
        ]

        for url in urls:
            try:
                async with async_timeout.timeout(5):
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            res = await resp.json()
                            _LOGGER.warning("VICTOIRE IP [%s]: %s", url, res)
                            self.data[self.device_sn] = res
                            return self.data
            except Exception:
                continue

        _LOGGER.debug("L'IP %s ne répond pas en HTTP. En attente MQTT...", self.device_ip)
        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        """Réception via MQTT (si la batterie se décide à parler)."""
        _LOGGER.warning("MQTT REÇU pour %s: %s", device_id, payload)
        if device_id not in self.data:
            self.data[device_id] = {}
        self.data[device_id].update(payload)
        self.async_set_updated_data(self.data)

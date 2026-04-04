from __future__ import annotations
import logging
import socket
import asyncio
from datetime import timedelta
from typing import Any
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, entry) -> None:
        super().__init__(hass, _LOGGER, name="storcube", update_interval=timedelta(seconds=30))
        self.data: dict[str, Any] = {}
        self.device_sn = "9105231027496254"

    async def _async_update_data(self) -> dict[str, Any]:
        """On écoute si la batterie envoie des paquets UDP sur le réseau."""
        # On ne fait rien ici, on laisse le serveur UDP remplir self.data
        return self.data

    def start_udp_listener(self):
        """Lance un écouteur sur les ports classiques des modules Doit.am."""
        def listen():
            # On écoute sur tous les ports suspects (UDP)
            ports = [12476, 48899, 10001]
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            
            for port in ports:
                try:
                    sock.bind(('', port))
                    _LOGGER.warning("Radar UDP activé sur le port %s", port)
                    data, addr = sock.recvfrom(1024)
                    if data:
                        _LOGGER.warning("🔥 UDP CAPTÉ de %s : %s", addr, data.hex())
                except:
                    continue
        
        # Note: ceci est une version simplifiée pour tester
        asyncio.get_event_loop().run_in_executor(None, listen)

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        if device_id not in self.data: self.data[device_id] = {}
        self.data[device_id].update(payload)
        self.async_set_updated_data(self.data)

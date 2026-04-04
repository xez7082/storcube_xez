from __future__ import annotations

import logging
import asyncio
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
            update_interval=timedelta(seconds=20),
        )
        self.entry = entry
        self.data: dict[str, Any] = {}
        # Configuration forcée pour ton module Doit.am
        self.device_ip = "192.168.1.190"
        self.device_sn = "9105231027496254"

    async def _async_update_data(self) -> dict[str, Any]:
        """Lecture sur le pont TCP 8080 du module ESP8266."""
        
        # 1. Tentative de connexion TCP brute sur le port 8080
        try:
            _LOGGER.debug("Connexion TCP 8080 vers %s", self.device_ip)
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.device_ip, 8080), 
                timeout=4
            )
            
            # Lecture des données envoyées par la batterie
            raw_data = await reader.read(2048)
            writer.close()
            await writer.wait_closed()

            if raw_data:
                decoded_text = raw_data.decode('utf-8', errors='ignore')
                _LOGGER.warning("DONNÉES REÇUES [8080]: %s", decoded_text[:150])
                
                # Test si c'est du JSON
                if "{" in decoded_text and "}" in decoded_text:
                    import json
                    try:
                        start = decoded_text.find("{")
                        end = decoded_text.rfind("}") + 1
                        self.data[self.device_sn] = json.loads(decoded_text[start:end])
                        return self.data
                    except Exception:
                        pass
                
                # Sinon on stocke en brut
                self.data[self.device_sn] = {"raw": decoded_text}
                return self.data

        except Exception as e:
            _LOGGER.debug("Le port 8080 n'a pas répondu : %s", e)

        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        """Mise à jour via MQTT."""
        if device_id not in self.data:
            self.data[device_id] = {}
        self.data[device_id].update(payload)
        _LOGGER.warning("MQTT reçu pour %s", device_id)
        self.async_set_updated_data(self.data)

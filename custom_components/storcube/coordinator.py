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
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry
        self.data: dict[str, Any] = {}
        # Configuration IP détectée lors du scan
        self.device_ip = "192.168.1.190"
        self.device_sn = "9105231027496254"

    async def _async_update_data(self) -> dict[str, Any]:
        """Interrogation du pont TCP 8080 avec commande de réveil."""
        
        try:
            _LOGGER.debug("Tentative de connexion TCP 8080 vers %s", self.device_ip)
            # Ouverture de la socket
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.device_ip, 8080), 
                timeout=5
            )
            
            # Envoi d'une commande de statut générique pour modules DT-06 / Doit.am
            # On tente le format JSON et le format texte simple
            _LOGGER.debug("Envoi commande de réveil...")
            writer.write(b'{"cmd":"get_status"}\n')
            await writer.drain()
            
            # Petite pause pour laisser la batterie répondre via le pont série
            await asyncio.sleep(1)
            
            # Lecture de la réponse
            raw_data = await reader.read(2048)
            
            # Fermeture propre
            writer.close()
            await writer.wait_closed()

            if raw_data:
                decoded_text = raw_data.decode('utf-8', errors='ignore').strip()
                _LOGGER.warning("🔥 RÉPONSE REÇUE [8080]: %s", decoded_text)
                
                # Si la réponse est du JSON, on la décode
                if "{" in decoded_text and "}" in decoded_text:
                    import json
                    try:
                        start = decoded_text.find("{")
                        end = decoded_text.rfind("}") + 1
                        json_content = json.loads(decoded_text[start:end])
                        self.data[self.device_sn] = json_content
                        return self.data
                    except Exception:
                        pass
                
                # Sinon on stocke le texte brut
                self.data[self.device_sn] = {"raw_data": decoded_text}
                return self.data

        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout : La batterie 192.168.1.190 ne répond pas sur le port 8080.")
        except Exception as e:
            _LOGGER.error("Erreur lors de la communication TCP : %s", e)

        return self.data

    def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
        """Mise à jour via MQTT (écoute passive)."""
        if device_id not in self.data:
            self.data[device_id] = {}
        self.data[device_id].update(payload)
        _LOGGER.warning("Donnée MQTT captée pour %s", device_id)
        self.async_set_updated_data(self.data)

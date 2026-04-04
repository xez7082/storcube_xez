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
         # Configuration forcée suite au scan réseau
         self.device_ip = "192.168.1.190"
         self.device_sn = "9105231027496254"

     async def _async_update_data(self) -> dict[str, Any]:
         """Lecture sur le pont TCP 8080 du module Doit.am."""
         
         # 1. TENTATIVE TCP BRUTE (Le port 8080 des modules Doit.am)
         try:
             _LOGGER.debug("Connexion TCP au port 8080 de %s", self.device_ip)
             reader, writer = await asyncio.wait_for(
                 asyncio.open_connection(self.device_ip, 8080), 
                 timeout=4
             )
             
             # On lit ce que la batterie "crache" naturellement
             raw_data = await reader.read(2048)
             writer.close()
             await writer.wait_closed()

             if raw_data:
                 decoded_text = raw_data.decode('utf-8', errors='ignore')
                 _LOGGER.warning("DONNÉES REÇUES [8080]: %s", decoded_text[:100])
                 
                 # Si c'est du JSON, on l'extrait
                 if "{" in decoded_text and "}" in decoded_text:
                     import json
                     start = decoded_text.find("{")
                     end = decoded_text.rfind("}") + 1
                     self.data[self.device_sn] = json.loads(decoded_text[start:end])
                 else:
                     # Sinon on stocke le brut pour analyse
                     self.data[self.device_sn] = {"raw_hex": raw_data.hex()}
                 
                 return self.data

         except Exception as e:
             _LOGGER.debug("Le port 8080 TCP ne répond pas : %s", e)

         # 2. TENTATIVE HTTP (Fallback au cas où)
         session = async_get_clientsession(self.hass)
         url = f"http://{self.device_ip}/status" # Parfois dispo sur ces modules
         try:
             async with async_timeout.timeout(3):
                 async with session.get(url) as resp:
                     if resp.status == 200:
                         res = await resp.json()
                         self.data[self.device_sn] = res
         except:
             pass

         return self.data

     def update_from_mqtt(self, device_id: str, payload: dict[str, Any]) -> None:
         """Mise à jour via MQTT si un message arrive."""
         if device_id not in self.data:
             self.data[device_id] = {}
         self.data[device_id].update(payload)
         _LOGGER.warning("Donnée MQTT reçue pour %s", device_id)
         self.async_set_updated_data(self.data)

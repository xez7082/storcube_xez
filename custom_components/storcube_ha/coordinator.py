"""Data Coordinator for Storcube Battery Monitor."""
from __future__ import annotations

import logging
import json
import asyncio
from datetime import timedelta
from typing import Any

import aiohttp
import websockets
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components import mqtt
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_APP_CODE,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
    TOKEN_URL,
    WS_URI,
    OUTPUT_URL,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Gère la récupération des données via REST, WebSocket et MQTT."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self._auth_token: str | None = None
        self._device_id = entry.data[CONF_DEVICE_ID]
        
        # Structure de données plate pour que les sensors s'y retrouvent facilement
        self.data = {
            "soc": None,
            "power": 0,
            "pv1": 0,
            "pv2": 0,
            "temp": 0,
            "is_online": False
        }

    async def async_setup(self):
        """Configuration initiale des écouteurs (appelé par __init__.py)."""
        await self.async_setup_listeners()

    async def _async_update_data(self) -> dict[str, Any]:
        """Mise à jour périodique via REST API."""
        try:
            if not self._auth_token:
                await self.async_renew_token()

            await self._update_rest_data()
            return self.data
        except Exception as err:
            _LOGGER.error("Erreur lors de la mise à jour Storcube : %s", err)
            raise UpdateFailed(f"Erreur de communication : {err}") from err

    async def async_renew_token(self):
        """Récupère un nouveau token d'accès."""
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD]
        }
        try:
            async with self.session.post(TOKEN_URL, json=payload, timeout=15) as resp:
                if resp.status == 401:
                    raise ConfigEntryAuthFailed("Identifiants Storcube invalides")
                
                res = await resp.json()
                if res.get("code") == 200:
                    self._auth_token = res["data"]["token"]
                    _LOGGER.debug("Nouveau token Storcube généré")
                else:
                    _LOGGER.error("Échec récupération Token: %s", res.get("message"))
        except Exception as err:
            _LOGGER.error("Erreur réseau lors de l'auth: %s", err)

    async def _update_rest_data(self):
        """Récupère les données via l'API REST et met à jour self.data."""
        if not self._auth_token:
            return

        headers = {
            "Authorization": self._auth_token,
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube")
        }
        url = f"{OUTPUT_URL}{self._device_id}"
        
        try:
            async with self.session.get(url, headers=headers, timeout=10) as resp:
                res = await resp.json()
                if res.get("code") == 200 and res.get("data"):
                    raw = res["data"][0] if isinstance(res["data"], list) else res["data"]
                    
                    # Mapping des données REST vers notre structure plate
                    self.data["soc"] = raw.get("batteryLevel") or raw.get("soc")
                    self.data["temp"] = raw.get("temperature") or raw.get("temp")
                    self.async_set_updated_data(self.data)
        except Exception as err:
            _LOGGER.debug("REST API non disponible (normal si WebSocket actif): %s", err)

    async def async_setup_listeners(self):
        """Configure les écouteurs MQTT et WebSocket."""
        
        # 1. MQTT
        @callback
        def _handle_mqtt_msg(msg):
            try:
                payload = json.loads(msg.payload)
                # On détecte le type de donnée par le topic (ex: storcube/ID/power)
                topic_type = msg.topic.split("/")[-1]
                
                if topic_type == "power":
                    self.data["power"] = payload.get("value", 0)
                elif topic_type == "solar":
                    self.data["pv1"] = payload.get("pv1", 0)
                    self.data["pv2"] = payload.get("pv2", 0)
                
                self.async_set_updated_data(self.data)
            except Exception as err:
                _LOGGER.error("Erreur MQTT: %s", err)

        await mqtt.async_subscribe(self.hass, f"storcube/{self._device_id}/#", _handle_mqtt_msg)

        # 2. WebSocket (en tâche de fond)
        self.hass.loop.create_task(self._listen_websocket())

    async def _listen_websocket(self):
        """Boucle WebSocket pour les données en temps réel."""
        while True:
            if not self._auth_token:
                await asyncio.sleep(5)
                continue

            try:
                # Ajout du token dans l'URL ou les headers selon l'API
                headers = {"Authorization": self._auth_token}
                async with websockets.connect(WS_URI, extra_headers=headers) as ws:
                    _LOGGER.info("WebSocket Storcube connecté")
                    while True:
                        msg = await ws.recv()
                        payload = json.loads(msg)
                        
                        # Extraction des données selon le format Storcube
                        # On cherche notre device dans la liste reçue
                        devices = payload.get("list", [])
                        for device in devices:
                            if device.get("equipId") == self._device_id:
                                self.data["soc"] = device.get("batteryLevel")
                                self.data["power"] = device.get("currentPower")
                                self.data["pv1"] = device.get("pvPower1")
                                self.data["pv2"] = device.get("pvPower2")
                                self.data["is_online"] = device.get("online", False)
                                
                                self.async_set_updated_data(self.data)
            except Exception as err:
                _LOGGER.debug("Reconnexion WebSocket dans 15s... (%s)", err)
                await asyncio.sleep(15)

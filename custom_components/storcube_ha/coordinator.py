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
        
        # Initialisation de la structure de données
        self.data = {
            "websocket": {},
            "rest_api": {},
            "firmware": {},
            "raw_mqtt": {}
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Méthode principale de mise à jour (appelée par le cycle Coordinator)."""
        try:
            # 1. Vérifier/Récupérer le Token
            if not self._auth_token:
                await self.async_renew_token()

            # 2. Récupérer les données REST (Scène/Output)
            await self._update_rest_data()

            return self.data
        except Exception as err:
            raise UpdateFailed(f"Erreur lors de la mise à jour : {err}") from err

    async def async_renew_token(self):
        """Récupère un nouveau token d'accès."""
        payload = {
            "appCode": self.entry.data[CONF_APP_CODE],
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD]
        }
        async with self.session.post(TOKEN_URL, json=payload) as resp:
            if resp.status == 401:
                raise ConfigEntryAuthFailed("Identifiants Storcube invalides")
            res = await resp.json()
            if res.get("code") == 200:
                self._auth_token = res["data"]["token"]
                _LOGGER.debug("Nouveau token Storcube généré")
            else:
                raise UpdateFailed(f"Erreur API Token: {res.get('message')}")

    async def _update_rest_data(self):
        """Récupère les données via l'API REST."""
        headers = {
            "Authorization": self._auth_token,
            "appCode": self.entry.data[CONF_APP_CODE]
        }
        url = f"{OUTPUT_URL}{self.entry.data[CONF_DEVICE_ID]}"
        
        try:
            async with self.session.get(url, headers=headers, timeout=10) as resp:
                res = await resp.json()
                if res.get("code") == 200 and res.get("data"):
                    # On stocke les données par device_id
                    device_data = res["data"][0] if isinstance(res["data"], list) else res["data"]
                    self.data["rest_api"][self.entry.data[CONF_DEVICE_ID]] = device_data
        except Exception as err:
            _LOGGER.error("Erreur REST API: %s", err)

    async def async_setup_listeners(self):
        """Configure les écouteurs asynchrones (MQTT et WebSocket)."""
        
        # 1. MQTT Natif Home Assistant
        @callback
        def _handle_mqtt_msg(msg):
            """Callback quand un message MQTT arrive."""
            try:
                payload = json.loads(msg.payload)
                topic_type = msg.topic.split("/")[-1]
                self.data["raw_mqtt"][topic_type] = payload.get("value")
                self.async_set_updated_data(self.data)
            except Exception as err:
                _LOGGER.error("Erreur lecture MQTT: %s", err)

        # Abonnement dynamique via le module MQTT de HA
        await mqtt.async_subscribe(self.hass, f"storcube/{self.entry.data[CONF_DEVICE_ID]}/#", _handle_mqtt_msg)

        # 2. Démarrer le WebSocket en tâche de fond
        self.hass.loop.create_task(self._listen_websocket())

    async def _listen_websocket(self):
        """Boucle de lecture WebSocket."""
        while True:
            if not self._auth_token:
                await asyncio.sleep(5)
                continue

            try:
                headers = {"Authorization": self._auth_token}
                async with websockets.connect(WS_URI, extra_headers=headers) as ws:
                    _LOGGER.info("Connecté au WebSocket Storcube")
                    while True:
                        msg = await ws.recv()
                        payload = json.loads(msg)
                        if "list" in payload:
                            for device in payload["list"]:
                                d_id = device.get("equipId")
                                self.data["websocket"][d_id] = device
                            
                            # On force la mise à jour des entités HA
                            self.async_set_updated_data(self.data)
            except Exception as err:
                _LOGGER.warning("Déconnexion WS (%s), reconnexion dans 10s", err)
                await asyncio.sleep(10)

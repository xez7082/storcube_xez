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
        self._device_id = str(entry.data[CONF_DEVICE_ID]).strip()
        
        self.data = {
            "soc": 0,
            "power": 0,
            "pv1": 0,
            "pv2": 0,
            "temp": 0,
            "is_online": False
        }

    async def async_setup(self):
        """Configuration initiale des écouteurs."""
        self.hass.loop.create_task(self.async_setup_listeners())

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
                    _LOGGER.info("Storcube: Nouveau Token récupéré")
        except Exception as err:
            _LOGGER.error("Erreur d'authentification Storcube: %s", err)

    def _extract_values(self, source_data: dict[str, Any]):
        """Extrait les valeurs réelles identifiées."""
        _LOGGER.debug("Extraction Storcube pour %s: %s", self._device_id, source_data)

        # Batterie (SOC) -> Identifié comme 'reserved' dans tes logs
        soc = source_data.get("reserved")
        if soc is not None:
            self.data["soc"] = float(soc)

        # Puissance de sortie -> Identifié comme 'outputPower'
        power = source_data.get("outputPower")
        if power is not None:
            self.data["power"] = float(power)

        # Solaire PV1 et PV2 (On ajoute plusieurs variantes par précaution)
        pv1 = source_data.get("pvPower1") or source_data.get("ppv1") or source_data.get("pv1")
        if pv1 is not None: self.data["pv1"] = float(pv1)

        pv2 = source_data.get("pvPower2") or source_data.get("ppv2") or source_data.get("pv2")
        if pv2 is not None: self.data["pv2"] = float(pv2)

        # Température
        temp = source_data.get("temperature") or source_data.get("temp")
        if temp is not None: self.data["temp"] = float(temp)

        # Statut en ligne
        online = source_data.get("fgOnline") or source_data.get("mainEquipOnline")
        if online is not None:
            self.data["is_online"] = (int(online) == 1)

    async def _update_rest_data(self):
        """Récupère les données via l'API REST."""
        if not self._auth_token: return
        
        headers = {
            "Authorization": self._auth_token, 
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube")
        }
        url = f"{OUTPUT_URL}{self._device_id}"
        
        try:
            async with self.session.get(url, headers=headers, timeout=10) as resp:
                res = await resp.json()
                if res.get("code") == 200 and "data" in res:
                    raw_data = res["data"]
                    raw = raw_data[0] if isinstance(raw_data, list) and len(raw_data) > 0 else raw_data
                    if raw:
                        self._extract_values(raw)
                        self.async_set_updated_data(self.data)
        except Exception as err:
            _LOGGER.debug("REST Storcube discret : %s", err)

    async def async_setup_listeners(self):
        """Abonnement MQTT et WebSocket."""
        # MQTT
        try:
            @callback
            def _handle_mqtt_msg(msg):
                try:
                    payload = json.loads(msg.payload)
                    self._extract_values(payload)
                    self.async_set_updated_data(self.data)
                except Exception: pass
            await mqtt.async_subscribe(self.hass, f"storcube/{self._device_id}/#", _handle_mqtt_msg)
        except Exception: pass

        # WebSocket Task
        self.hass.loop.create_task(self._listen_websocket())

    async def _listen_websocket(self):
        """Boucle WebSocket pour les mises à jour en temps réel."""
        while True:
            if not self._auth_token:
                await asyncio.sleep(10)
                continue
            try:
                # Correction majeure ici pour éviter l'erreur de headers
                async with websockets.connect(
                    WS_URI, 
                    extra_headers=[("Authorization", self._auth_token)]
                ) as ws:
                    _LOGGER.info("WebSocket Storcube: Connecté")
                    while True:
                        msg = await ws.recv()
                        payload = json.loads(msg)
                        devices = payload.get("list", [])
                        for device in devices:
                            # Vérification multi-clés pour l'ID
                            e_id = str(device.get("equipId") or device.get("id") or "")
                            if e_id == self._device_id:
                                self._extract_values(device)
                                self.async_set_updated_data(self.data)
            except Exception as err:
                _LOGGER.debug("Reconnexion WebSocket Storcube dans 15s : %s", err)
                await asyncio.sleep(15)

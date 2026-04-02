"""Support for Storcube Battery Monitor sensors."""
from __future__ import annotations

import logging
import json
import asyncio
import aiohttp
import websockets
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    PERCENTAGE,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_APP_CODE,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
    WS_URI,
    TOKEN_URL,
    OUTPUT_URL,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    config = config_entry.data
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = [
        StorcubeBatteryLevelSensor(config),
        StorcubeBatteryPowerSensor(config),
        StorcubeBatteryTemperatureSensor(config),
        StorcubeBatteryCapacityWhSensor(config),
        StorcubeBatteryStatusSensor(config),
        StorcubeBatteryThresholdSensor(config),
        StorcubeSolarPowerSensor(config),
        StorcubeSolarEnergySensor(config),
        StorcubeSolarPowerSensor2(config),
        StorcubeSolarEnergySensor2(config),
        StorcubeSolarEnergyTotalSensor(config),
        StorcubeOutputPowerSensor(config),
        StorcubeOutputEnergySensor(config),
        StorcubeStatusSensor(config),
        StorcubeModelSensor(config),
        StorcubeSerialNumberSensor(config),
        StorcubeOutputTypeSensor(config),
        StorcubeReservedSensor(config),
        StorcubeWorkStatusSensor(config),
        StorcubeOnlineSensor(config),
        StorcubeErrorCodeSensor(config),
        StorcubeFirmwareSensor(config, coordinator),
        StorcubeOperatingModeSensor(config),
    ]

    async_add_entities(sensors)

    # Stockage des instances pour accès par les fonctions de mise à jour
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    # On évite d'écraser le coordinateur déjà présent
    if isinstance(hass.data[DOMAIN][config_entry.entry_id], dict):
        hass.data[DOMAIN][config_entry.entry_id]["sensors"] = sensors
    else:
        # Si c'est juste l'objet coordinateur, on transforme en dict
        coord_obj = hass.data[DOMAIN][config_entry.entry_id]
        hass.data[DOMAIN][config_entry.entry_id] = {
            "coordinator": coord_obj,
            "sensors": sensors
        }

    # Lancement des boucles de données
    hass.loop.create_task(websocket_to_mqtt(hass, config, config_entry))
    hass.loop.create_task(output_api_to_mqtt(hass, config, config_entry))

class StorcubeBatterySensor(SensorEntity):
    """Classe de base pour les capteurs Storcube."""

    def __init__(self, config: ConfigType) -> None:
        self._config = config
        self._websocket_data: dict[str, Any] = {}
        self._attr_native_value = None
        self._attr_has_entity_name = True

    @callback
    def handle_state_update(self, payload: dict[str, Any]) -> None:
        """Centralisation de la réception des données."""
        try:
            if "websocket_data" in payload:
                self._websocket_data = payload["websocket_data"]
            elif "rest_data" in payload:
                rd = payload["rest_data"]
                self._websocket_data = {
                    "list": [{
                        "outputType": rd.get("outputType"),
                        "equipId": rd.get("equipId"),
                        "reserved": rd.get("reserved"),
                        "invPower": rd.get("outputPower"),
                        "workStatus": rd.get("workStatus"),
                        "rgOnline": rd.get("fgOnline"),
                        "mainEquipOnline": rd.get("mainEquipOnline"),
                        "equipModelCode": rd.get("equipModelCode"),
                        "version": rd.get("version", ""),
                        "isWork": 1 if rd.get("workStatus") == 1 else 0,
                        "errorCode": rd.get("errorCode", 0),
                        "operatingMode": rd.get("operatingMode", 0)
                    }]
                }
            elif isinstance(payload, dict) and ("list" in payload or "totalPv1power" in payload):
                self._websocket_data = payload
            
            self._update_value_from_sources()
        except Exception as e:
            _LOGGER.error("Erreur mise à jour %s: %s", self.entity_id, e)

    def _update_value_from_sources(self):
        """Méthode à surcharger."""
        pass

class StorcubeBatteryLevelSensor(StorcubeBatterySensor):
    """Niveau de batterie (SoC)."""
    def __init__(self, config):
        super().__init__(config)
        self._attr_name = "Niveau Batterie"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_unique_id = f"{config[CONF_DEVICE_ID]}_battery_level"

    def _update_value_from_sources(self):
        if self._websocket_data.get("list"):
            val = self._websocket_data["list"][0].get("soc")
            if val is not None:
                self._attr_native_value = val
                self.async_write_ha_state()

class StorcubeSolarPowerSensor(StorcubeBatterySensor):
    """Puissance PV1."""
    def __init__(self, config):
        super().__init__(config)
        self._attr_name = "Puissance Solaire 1"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_unique_id = f"{config[CONF_DEVICE_ID]}_solar_power_1"

    def _update_value_from_sources(self):
        val = self._websocket_data.get("totalPv1power")
        if val is None and self._websocket_data.get("list"):
            val = self._websocket_data["list"][0].get("pv1power")
        
        if val is not None:
            self._attr_native_value = val
            self.async_write_ha_state()

class StorcubeFirmwareSensor(StorcubeBatterySensor):
    """Capteur Firmware complexe avec attributs."""
    def __init__(self, config, coordinator):
        super().__init__(config)
        self.coordinator = coordinator
        self._attr_name = "Firmware"
        self._attr_unique_id = f"{config[CONF_DEVICE_ID]}_firmware_info"
        self._attr_icon = "mdi:update"
        self._firmware_data = {}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._firmware_data

    def _update_value_from_sources(self):
        # Priorité aux données du coordinateur si présent
        if self.coordinator and self.coordinator.data:
            fw = self.coordinator.data.get("firmware", {})
            if fw:
                self._firmware_data = fw
                ver = fw.get("current_version", "Inconnue")
                if fw.get("upgrade_available"):
                    self._attr_native_value = f"Update available ({fw.get('latest_version')})"
                else:
                    self._attr_native_value = f"Up to date ({ver})"
                self.async_write_ha_state()

# ... (Les autres classes suivent la même logique simplifiée de _update_value_from_sources)

async def websocket_to_mqtt(hass, config, config_entry):
    """Boucle WebSocket robuste."""
    device_id = config[CONF_DEVICE_ID]
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                # Auth
                auth_payload = {
                    "appCode": config[CONF_APP_CODE],
                    "loginName": config[CONF_LOGIN_NAME],
                    "password": config[CONF_AUTH_PASSWORD]
                }
                async with session.post(TOKEN_URL, json=auth_payload, ssl=False) as resp:
                    data = await resp.json()
                    if data.get("code") != 200:
                        raise Exception(f"Auth failed: {data.get('message')}")
                    token = data["data"]["token"]

                # WS
                async with websockets.connect(f"{WS_URI}{token}", ping_interval=15) as ws:
                    await ws.send(json.dumps({"reportEquip": [device_id]}))
                    while True:
                        msg = await ws.recv()
                        if msg == "SUCCESS": continue
                        
                        payload = json.loads(msg)
                        # Distribution aux capteurs
                        entry_data = hass.data[DOMAIN][config_entry.entry_id]
                        if isinstance(entry_data, dict) and "sensors" in entry_data:
                            for sensor in entry_data["sensors"]:
                                sensor.handle_state_update(payload)
        except Exception as e:
            _LOGGER.error("WebSocket Error: %s. Retrying in 10s...", e)
            await asyncio.sleep(10)

async def output_api_to_mqtt(hass, config, config_entry):
    """Polling API REST pour les données complémentaires."""
    while True:
        try:
            # Logique similaire au WS pour obtenir le token et requêter OUTPUT_URL
            # Puis distribuer via : sensor.handle_state_update({"rest_data": equip_data})
            await asyncio.sleep(30)
        except Exception as e:
            await asyncio.sleep(10)

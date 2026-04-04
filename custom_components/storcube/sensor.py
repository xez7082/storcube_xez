from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

# =========================================================
# BASE SENSOR
# =========================================================
class StorcubeBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor StorCube."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        # Utilisation de CONF_DEVICE_ID (singulier comme dans ton config_flow probable)
        self._device_id = entry.data.get(CONF_DEVICE_ID, "unknown")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"StorCube {self._device_id}",
            manufacturer="StorCube",
            model="S1000",
        )

    def _get_val(self, keys: list[str], default: float = 0.0) -> float:
        """Cherche une valeur parmi plusieurs clés possibles, y compris dans 'list'."""
        data = self.coordinator.data
        if not data:
            return default
        
        # 1. Chercher dans 'list' si présent (format standard Storcube)
        if "list" in data and isinstance(data["list"], list) and len(data["list"]) > 0:
            equip = data["list"][0]
            for key in keys:
                if key in equip and equip[key] is not None:
                    return float(equip[key])

        # 2. Chercher à la racine (format simplifié S1000)
        for key in keys:
            if key in data and data[key] is not None:
                return float(data[key])
        
        return default

# =========================================================
# BATTERY LEVEL
# =========================================================
class StorcubeBatteryLevelSensor(StorcubeBaseSensor):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Battery Level"
        self._attr_unique_id = f"storcube_{self._device_id}_battery_level"

    @property
    def native_value(self) -> float:
        # Cherche 'soc' ou 'battery_level'
        return self._get_val(["soc", "battery_level"])

# =========================================================
# OUTPUT POWER (Injection Maison)
# =========================================================
class StorcubeBatteryPowerSensor(StorcubeBaseSensor):
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Output Power"
        self._attr_unique_id = f"storcube_{self._device_id}_battery_power"

    @property
    def native_value(self) -> float:
        # Cherche 'invPower', 'power' ou 'p_out'
        return self._get_val(["invPower", "totalInvPower", "power", "pout"])

# =========================================================
# SOLAR PV
# =========================================================
class StorcubeSolarPowerSensor(StorcubeBaseSensor):
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, pv_index: int) -> None:
        super().__init__(coordinator, entry)
        self._pv_index = pv_index
        self._attr_name = f"Solar PV{pv_index}"
        self._attr_unique_id = f"storcube_{self._device_id}_solar_pv{pv_index}"

    @property
    def native_value(self) -> float:
        # Cherche 'pv1power' ou 'ppv1' ou 'totalPv1power'
        idx = self._pv_index
        keys = [f"pv{idx}power", f"totalPv{idx}power", f"ppv{idx}", f"pv{idx}"]
        return self._get_val(keys)

# =========================================================
# TEMPERATURE
# =========================================================
class StorcubeTemperatureSensor(StorcubeBaseSensor):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Temperature"
        self._attr_unique_id = f"storcube_{self._device_id}_temperature"

    @property
    def native_value(self) -> float:
        # Cherche 'temp' ou 'temperature'
        return self._get_val(["temp", "temperature", "t"])

# =========================================================
# SETUP ENTRY
# =========================================================
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    # On récupère le coordinateur selon la structure définie dans __init__.py
    data = hass.data[DOMAIN][entry.entry_id]
    
    # Si ton __init__ stocke directement le coordinator
    if isinstance(data, dict):
        coordinator = data.get("coordinator")
    else:
        coordinator = data

    if not coordinator:
        _LOGGER.error("StorCube coordinator missing for %s", entry.entry_id)
        return

    entities = [
        StorcubeBatteryLevelSensor(coordinator, entry),
        StorcubeBatteryPowerSensor(coordinator, entry),
        StorcubeSolarPowerSensor(coordinator, entry, 1),
        StorcubeSolarPowerSensor(coordinator, entry, 2), # Ajout du PV2 par défaut
        StorcubeTemperatureSensor(coordinator, entry),
    ]

    async_add_entities(entities)

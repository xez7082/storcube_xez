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

from .const import DOMAIN, CONF_DEVICE_IDS

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

        # 🔥 FIX IMPORTANT : device_id correct
        device_ids = entry.data.get(CONF_DEVICE_IDS, [])
        self._device_id = str(device_ids[0]) if device_ids else "unknown"

        # Device grouping HA
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"StorCube {self._device_id}",
            manufacturer="StorCube",
            model="S1000",
        )

    def _safe(self, key: str, default: Any = None) -> Any:
        """Safe access coordinator data."""
        return (self.coordinator.data or {}).get(key, default)


# =========================================================
# BATTERY LEVEL
# =========================================================
class StorcubeBatteryLevelSensor(StorcubeBaseSensor):
    """Battery SOC sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)

        self._attr_name = "Battery Level"

        # 🔥 FIX unique_id stable
        self._attr_unique_id = f"storcube_{self._device_id}_battery_level"

    @property
    def native_value(self) -> float:
        return float(self._safe("soc", 0.0) or 0.0)


# =========================================================
# POWER OUTPUT
# =========================================================
class StorcubeBatteryPowerSensor(StorcubeBaseSensor):
    """AC output power."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)

        self._attr_name = "Output Power"
        self._attr_unique_id = f"storcube_{self._device_id}_battery_power"

    @property
    def native_value(self) -> float:
        return float(self._safe("power", 0.0) or 0.0)


# =========================================================
# SOLAR PV
# =========================================================
class StorcubeSolarPowerSensor(StorcubeBaseSensor):
    """Solar PV sensor."""

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
        return float(self._safe(f"pv{self._pv_index}", 0.0) or 0.0)


# =========================================================
# TEMPERATURE
# =========================================================
class StorcubeTemperatureSensor(StorcubeBaseSensor):
    """Temperature sensor."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)

        self._attr_name = "Temperature"
        self._attr_unique_id = f"storcube_{self._device_id}_temperature"

    @property
    def native_value(self) -> float:
        return float(self._safe("temp", 0.0) or 0.0)


# =========================================================
# SETUP ENTRY
# =========================================================
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")

    if not coordinator:
        _LOGGER.error("StorCube coordinator missing for %s", entry.entry_id)
        return

    sensors: list[SensorEntity] = [
        StorcubeBatteryLevelSensor(coordinator, entry),
        StorcubeBatteryPowerSensor(coordinator, entry),
        StorcubeSolarPowerSensor(coordinator, entry, 1),
        StorcubeTemperatureSensor(coordinator, entry),
    ]

    async_add_entities(sensors)

"""Support for Storcube sensors."""
from __future__ import annotations

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# Importation cruciale
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class StorcubeBaseSensor(CoordinatorEntity, SensorEntity):
    """Classe de base pour les capteurs Storcube."""
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        # On s'assure de récupérer l'ID de l'appareil correctement
        self._device_id = str(entry.data.get("device_id", "unknown")).strip()
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"Storcube {self._device_id}",
            "manufacturer": "Storcube",
        }

class StorcubeBatteryLevelSensor(StorcubeBaseSensor):
    """Niveau de batterie (%)."""
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Niveau de batterie"
        self._attr_unique_id = f"{self._device_id}_battery_level"

    @property
    def native_value(self):
        return self.coordinator.data.get("soc")

class StorcubeBatteryPowerSensor(StorcubeBaseSensor):
    """Puissance de la batterie (W)."""
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Puissance batterie"
        self._attr_unique_id = f"{self._device_id}_battery_power"

    @property
    def native_value(self):
        return self.coordinator.data.get("power")

class StorcubeSolarPowerSensor(StorcubeBaseSensor):
    """Production Solaire (W)."""
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, pv_index):
        super().__init__(coordinator, entry)
        self._pv_index = pv_index
        self._attr_name = f"Production Solaire PV{pv_index}"
        self._attr_unique_id = f"{self._device_id}_solar_pv{pv_index}"

    @property
    def native_value(self):
        return self.coordinator.data.get(f"pv{self._pv_index}")

class StorcubeTemperatureSensor(StorcubeBaseSensor):
    """Température (°C)."""
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Température"
        self._attr_unique_id = f"{self._device_id}_temperature"

    @property
    def native_value(self):
        return self.coordinator.data.get("temp")

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configuration des capteurs Storcube."""
    
    # Vérification sécurisée de la présence des données dans hass.data
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("Données de l'intégration introuvables pour %s", entry.entry_id)
        return

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Ajout des entités
    async_add_entities([
        StorcubeBatteryLevelSensor(coordinator, entry),
        StorcubeBatteryPowerSensor(coordinator, entry),
        StorcubeSolarPowerSensor(coordinator, entry, "1"),
        StorcubeSolarPowerSensor(coordinator, entry, "2"),
        StorcubeTemperatureSensor(coordinator, entry),
    ])

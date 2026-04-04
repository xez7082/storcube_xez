from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configuration des capteurs Storcube à partir de l'entrée de config."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_ids = entry.data.get("device_ids", [entry.data.get("device_id")])

    entities = []
    for device_id in device_ids:
        # On détermine si c'est le maître ou l'esclave pour le nommage des entités
        suffix = "maitre" if device_id == device_ids[0] else "esclave"
        
        entities.extend([
            StorCubeSensor(coordinator, device_id, "soc", "Capacité Batterie", PERCENTAGE, SensorDeviceClass.BATTERY, suffix),
            StorCubeSensor(coordinator, device_id, "invPower", "Puissance de Sortie", UnitOfPower.WATT, SensorDeviceClass.POWER, suffix),
            StorCubeSensor(coordinator, device_id, "pv1power", "Solaire PV1", UnitOfPower.WATT, SensorDeviceClass.POWER, suffix),
            StorCubeSensor(coordinator, device_id, "pv2power", "Solaire PV2", UnitOfPower.WATT, SensorDeviceClass.POWER, suffix),
            StorCubeSensor(coordinator, device_id, "temp", "Température", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, suffix),
        ])

    async_add_entities(entities)

class StorCubeSensor(CoordinatorEntity, SensorEntity):
    """Représentation d'un capteur StorCube."""

    def __init__(self, coordinator, device_id, key, name, unit, device_class, suffix):
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_name = f"{name} {device_id} {suffix}"
        # C'EST ICI QUE LE NOM UNIQUE EST GÉNÉRÉ POUR TES ALERTES
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}"
        # On force l'ID de l'entité pour correspondre à tes automatisations
        self.entity_id = f"sensor.{name.lower().replace(' ', '_')}_{device_id}_{suffix}"
        
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Retourne la valeur du capteur depuis les données du coordinateur."""
        # On cherche la valeur dans les données globales ou spécifiques à l'ID
        data = self.coordinator.data
        return data.get(self._key, 0)

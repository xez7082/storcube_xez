from __future__ import annotations
import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE, UnitOfPower, UnitOfTemperature, UnitOfEnergy
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_ids = entry.data.get("device_ids", [entry.data.get("device_id")])

    entities = []
    for index, device_id in enumerate(device_ids):
        suffix = "maitre" if index == 0 else "esclave"
        dev_id_str = str(device_id).strip()
        
        # Définition des capteurs
        sensors = [
            ("soc", "Capacité Batterie", PERCENTAGE, SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT),
            ("invPower", "Puissance Sortie", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
            ("pv1power", "Solaire PV1", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
            ("pv2power", "Solaire PV2", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
            ("temp", "Température Batterie", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
            ("capacity", "Capacité Wh", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY_STORAGE, SensorStateClass.MEASUREMENT),
            ("reserved", "Seuil Batterie", PERCENTAGE, None, SensorStateClass.MEASUREMENT),
            ("isWork", "État En Ligne", None, None, None),
            ("workStatus", "Statut Travail", None, None, None),
            ("errorCode", "Code Erreur", None, None, None),
            ("outputType", "Type Sortie", None, None, None),
        ]

        for key, name, unit, d_class, s_class in sensors:
            entities.append(StorCubeSensor(coordinator, dev_id_str, key, name, unit, d_class, s_class, suffix))

    async_add_entities(entities)

class StorCubeSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device_id, key, name, unit, device_class, state_class, suffix):
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}_{suffix}"
        self.entity_id = f"sensor.{name.lower().replace(' ', '_')}_{device_id}_{suffix}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = {"identifiers": {(DOMAIN, self._device_id)}, "name": f"StorCube S1000 ({suffix})"}

    @property
    def native_value(self):
        if not self.coordinator.data or self._device_id not in self.coordinator.data:
            return None

        device_data = self.coordinator.data[self._device_id]
        
        # Sécurité si device_data n'est pas un dictionnaire
        if not isinstance(device_data, dict):
            _LOGGER.warning("Les données pour %s ne sont pas un dictionnaire: %s", self._device_id, device_data)
            return device_data if self._key in ["soc", "invPower"] else None

        # Système de mapping intelligent (cherche toutes les variantes possibles)
        mapping = {
            "soc": ["soc", "battery_soc", "bat_soc", "battery_level"],
            "invPower": ["invPower", "p_out", "outputPower", "out_p"],
            "pv1power": ["pv1power", "p_pv1", "pv1_p", "totalPv1power"],
            "pv2power": ["pv2power", "p_pv2", "pv2_p", "totalPv2power"],
            "temp": ["temp", "temperature", "temp_c", "bat_temp"],
            "isWork": ["isWork", "rgOnline", "online", "mainEquipOnline"],
            "capacity": ["capacity", "cap", "total_cap"],
            "reserved": ["reserved", "threshold", "limit"]
        }

        # 1. On cherche via le mapping
        if self._key in mapping:
            for alt_key in mapping[self._key]:
                if alt_key in device_data:
                    val = device_data[alt_key]
                    if self._key == "isWork": return "Online" if val == 1 else "Offline"
                    return val

        # 2. On cherche la clé brute si rien trouvé dans le mapping
        return device_data.get(self._key)

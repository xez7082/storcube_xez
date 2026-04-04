from __future__ import annotations

import logging
from datetime import datetime
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
    UnitOfEnergy
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configuration de TOUS les capteurs Storcube."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    device_ids = entry.data.get("device_ids")
    if not device_ids:
        device_ids = [entry.data.get("device_id")]

    entities = []
    for index, device_id in enumerate(device_ids):
        suffix = "maitre" if index == 0 else "esclave"
        dev_id_str = str(device_id).strip()
        
        # Liste exhaustive des capteurs à créer pour chaque batterie
        sensor_definitions = [
            # --- BATTERIE ---
            ("soc", "Capacité Batterie", PERCENTAGE, SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT),
            ("temp", "Température Batterie", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
            ("capacity", "Capacité Wh", UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY_STORAGE, SensorStateClass.MEASUREMENT),
            ("reserved", "Seuil Batterie", PERCENTAGE, None, SensorStateClass.MEASUREMENT),
            
            # --- PUISSANCE (Watts) ---
            ("invPower", "Puissance Sortie", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
            ("pv1power", "Solaire PV1", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
            ("pv2power", "Solaire PV2", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
            
            # --- ÉTAT SYSTÈME ---
            ("workStatus", "Statut Travail", None, None, None),
            ("outputType", "Type Sortie", None, None, None),
            ("isWork", "État En Ligne", None, None, None),
            ("errorCode", "Code Erreur", None, None, None),
            ("version", "Version Firmware", None, None, None),
        ]

        for key, name, unit, dev_class, state_class in sensor_definitions:
            entities.append(
                StorCubeSensor(coordinator, dev_id_str, key, name, unit, dev_class, state_class, suffix)
            )

    async_add_entities(entities)

class StorCubeSensor(CoordinatorEntity, SensorEntity):
    """Représentation universelle d'un capteur StorCube."""

    def __init__(self, coordinator, device_id, key, name, unit, device_class, state_class, suffix):
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        
        # Identification
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}"
        
        # Génération de l'entity_id propre
        slug_name = name.lower().replace(" ", "_").replace("é", "e")
        self.entity_id = f"sensor.{slug_name}_{device_id}_{suffix}"
        
        # Propriétés HA
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"StorCube S1000 ({suffix})",
            "manufacturer": "StorCube",
            "model": "S1000",
        }

    @property
    def native_value(self):
        """Récupération de la valeur avec gestion des erreurs de type."""
        if not isinstance(self.coordinator.data, dict):
            return None

        device_data = self.coordinator.data.get(self._device_id)
        if not isinstance(device_data, dict):
            return None

        # Mapping pour trouver la bonne clé selon ce que renvoie l'API
        mapping = {
            "invPower": ["invPower", "p_out", "outputPower"],
            "pv1power": ["pv1power", "p_pv1", "totalPv1power"],
            "pv2power": ["pv2power", "p_pv2", "totalPv2power"],
            "soc": ["soc", "battery_soc"],
            "temp": ["temp", "temperature"],
            "workStatus": ["workStatus", "status"],
            "isWork": ["isWork", "rgOnline", "mainEquipOnline"]
        }

        # On cherche la valeur
        val = None
        if self._key in mapping:
            for potential_key in mapping[self._key]:
                if potential_key in device_data:
                    val = device_data[potential_key]
                    break
        
        if val is None:
            val = device_data.get(self._key)

        # Petit traitement spécial pour l'état de travail (isWork)
        if self._key == "isWork" and val is not None:
            return "Online" if val == 1 else "Offline"

        return val

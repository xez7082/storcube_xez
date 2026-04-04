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
    """Configuration des capteurs Storcube via le coordinateur."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Récupération des IDs, gestion du cas liste ou ID unique
    device_ids = entry.data.get("device_ids")
    if not device_ids:
        device_ids = [entry.data.get("device_id")]

    entities = []
    for index, device_id in enumerate(device_ids):
        suffix = "maitre" if index == 0 else "esclave"
        dev_id_str = str(device_id).strip()
        
        # Liste des définitions de capteurs (Clé, Nom, Unité, DeviceClass, StateClass)
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
    """Représentation d'un capteur StorCube."""

    def __init__(self, coordinator, device_id, key, name, unit, device_class, state_class, suffix):
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        
        # Formatage des noms et IDs uniques
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}_{suffix}"
        
        # Entity ID forcé pour éviter les doublons aléatoires
        slug_name = name.lower().replace(' ', '_').replace('é', 'e')
        self.entity_id = f"sensor.{slug_name}_{device_id}_{suffix}"
        
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
        """Récupération de la valeur depuis les données du coordinateur."""
        if not self.coordinator.data or self._device_id not in self.coordinator.data:
            return None

        device_data = self.coordinator.data[self._device_id]
        
        # Si on reçoit 0 ou un type non-dictionnaire (ton erreur actuelle), on retourne None sans loguer d'erreur
        if not isinstance(device_data, dict):
            return None

        # Système de mapping pour s'adapter aux différentes réponses possibles de l'API
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

        # 1. Tentative via le mapping
        val = None
        if self._key in mapping:
            for alt_key in mapping[self._key]:
                if alt_key in device_data:
                    val = device_data[alt_key]
                    break
        
        # 2. Si rien trouvé dans le mapping, on tente la clé brute
        if val is None:
            val = device_data.get(self._key)

        # Traitement spécial pour les états binaires
        if self._key == "isWork" and val is not None:
            return "Online" if val == 1 else "Offline"

        return val

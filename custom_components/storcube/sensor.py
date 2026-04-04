from __future__ import annotations

import logging
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

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configuration des capteurs Storcube à partir de l'entrée de config."""
    # On récupère l'objet coordinateur directement (doit être l'objet, pas un dict)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Récupération des IDs (liste ou ID unique)
    device_ids = entry.data.get("device_ids")
    if not device_ids:
        device_ids = [entry.data.get("device_id")]

    entities = []
    for index, device_id in enumerate(device_ids):
        # Identification Maître / Esclave
        suffix = "maitre" if index == 0 else "esclave"
        dev_id_str = str(device_id).strip()
        
        _LOGGER.debug("Création des capteurs pour l'appareil %s (%s)", dev_id_str, suffix)
        
        entities.extend([
            StorCubeSensor(coordinator, dev_id_str, "soc", "Capacité Batterie", PERCENTAGE, SensorDeviceClass.BATTERY, suffix),
            StorCubeSensor(coordinator, dev_id_str, "invPower", "Puissance de Sortie", UnitOfPower.WATT, SensorDeviceClass.POWER, suffix),
            StorCubeSensor(coordinator, dev_id_str, "pv1power", "Solaire PV1", UnitOfPower.WATT, SensorDeviceClass.POWER, suffix),
            StorCubeSensor(coordinator, dev_id_str, "pv2power", "Solaire PV2", UnitOfPower.WATT, SensorDeviceClass.POWER, suffix),
            StorCubeSensor(coordinator, dev_id_str, "temp", "Température", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, suffix),
        ])

    async_add_entities(entities)

class StorCubeSensor(CoordinatorEntity, SensorEntity):
    """Représentation d'un capteur StorCube."""

    def __init__(self, coordinator, device_id, key, name, unit, device_class, suffix):
        """Initialisation du capteur."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._suffix = suffix
        
        # Formatage du nom pour l'interface
        self._attr_name = f"{name} {suffix}"
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}"
        
        # ID de l'entité pour tes automatisations
        slug_name = name.lower().replace(" ", "_").replace("é", "e")
        self.entity_id = f"sensor.{slug_name}_{device_id}_{suffix}"
        
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"StorCube S1000 ({suffix})",
            "manufacturer": "StorCube",
            "model": "S1000",
        }

    @property
    def native_value(self):
        """Récupère la valeur en temps réel avec protection contre les types invalides."""
        # Vérification que coordinator.data est bien un dictionnaire
        if not isinstance(self.coordinator.data, dict):
            return 0

        # Récupération des données de CETTE batterie spécifique
        device_data = self.coordinator.data.get(self._device_id)
        
        # SÉCURITÉ : Si device_data est un entier (ex: 50) ou n'existe pas, on gère proprement
        if not isinstance(device_data, dict):
            # Si l'API renvoie directement une valeur numérique pour cet ID
            if isinstance(device_data, (int, float)):
                return device_data
            return 0
        
        # Mapping de sécurité pour les clés de l'API Cloud/MQTT
        mapping = {
            "invPower": ["invPower", "p_out", "outputPower", "out_p"],
            "pv1power": ["pv1power", "p_pv1", "pv1_p"],
            "pv2power": ["pv2power", "p_pv2", "pv2_p"],
            "soc": ["soc", "battery_soc", "bat_soc"],
            "temp": ["temp", "temperature", "temp_c"]
        }

        # On teste les clés du mapping
        if self._key in mapping:
            for potential_key in mapping[self._key]:
                if potential_key in device_data:
                    return device_data[potential_key]

        # Fallback sur la clé directe
        return device_data.get(self._key, 0)

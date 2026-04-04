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
    
    # On récupère les IDs depuis les données de l'entrée (config_flow)
    device_ids = entry.data.get("device_ids")
    if not device_ids:
        device_ids = [entry.data.get("device_id")]

    entities = []
    for index, device_id in enumerate(device_ids):
        # On détermine le suffixe selon l'ordre (Maître en premier, puis Esclave)
        suffix = "maitre" if index == 0 else "esclave"
        
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
        self._device_id = str(device_id)
        self._key = key
        
        # Nom affiché dans l'interface
        self._attr_name = f"{name} {suffix}"
        
        # ID unique pour éviter les doublons dans la base HA
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_{key}"
        
        # ID de l'entité (sensor.nom_batterie_maitre) pour tes automatisations
        # Attention : on nettoie les espaces et on met tout en minuscule
        slug_name = name.lower().replace(" ", "_").replace("é", "e")
        self.entity_id = f"sensor.{slug_name}_{self._device_id}_{suffix}"
        
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT

        # Informations sur l'appareil (pour regrouper les capteurs dans HA)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"StorCube S1000 ({suffix})",
            "manufacturer": "StorCube",
            "model": "S1000",
        }

    @property
    def native_value(self):
        """Retourne la valeur du capteur depuis le dictionnaire du coordinateur."""
        # On va chercher dans coordinator.data["910523..."]["soc"]
        device_data = self.coordinator.data.get(self._device_id, {})
        
        # Mapping de secours si le nom de l'API cloud est différent
        mapping = {
            "invPower": ["p_out", "outputPower", "invPower"],
            "pv1power": ["p_pv1", "pv1power"],
            "pv2power": ["p_pv2", "pv2power"],
            "soc": ["battery_soc", "soc"],
            "temp": ["temperature", "temp"]
        }

        # On teste les différentes clés possibles reçues du Cloud
        if self._key in mapping:
            for potential_key in mapping[self._key]:
                if potential_key in device_data:
                    return device_data[potential_key]

        return device_data.get(self._key, 0)

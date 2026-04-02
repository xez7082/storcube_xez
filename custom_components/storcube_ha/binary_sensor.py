"""Binary sensor platform for Storcube Battery Monitor."""
from __future__ import annotations

import json
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, ICON_CONNECTION
from .coordinator import StorCubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator: StorCubeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Créer les entités si des données sont présentes
    if not coordinator.data:
        return

    async_add_entities(
        StorCubeBatteryConnectionSensor(coordinator, equip_id)
        for equip_id in coordinator.data
    )

class StorCubeBatteryConnectionSensor(CoordinatorEntity[StorCubeDataUpdateCoordinator], BinarySensorEntity):
    """Binary sensor for battery connection status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True  # Recommandé pour les noms d'entités modernes
    _attr_icon = ICON_CONNECTION

    def __init__(self, coordinator: StorCubeDataUpdateCoordinator, equip_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._equip_id = equip_id
        # unique_id doit être immuable et inclure le domaine
        self._attr_unique_id = f"{DOMAIN}_{equip_id}_connectivity"
        
        # Avec has_entity_name = True, le nom de l'entité sera complété par le nom du device
        self._attr_name = "Connectivity" 
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._equip_id)},
            name=f"StorCube Battery {self._equip_id}",
            manufacturer="StorCube",
            model="Battery Monitor",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        battery_data = self.coordinator.data.get(self._equip_id)
        
        if not battery_data:
            return None

        raw_status = battery_data.get("battery_status")
        
        # Gestion du cas où battery_status est déjà un dictionnaire ou encore une string JSON
        if isinstance(raw_status, str):
            try:
                status_dict = json.loads(raw_status)
                return status_dict.get("value") == 1
            except (json.JSONDecodeError, TypeError):
                return False
        elif isinstance(raw_status, dict):
            return raw_status.get("value") == 1
            
        return False

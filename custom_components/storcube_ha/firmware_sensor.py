"""Capteur de firmware pour l'intégration Storcube Battery Monitor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    NAME,
    ATTR_FIRMWARE_CURRENT,
    ATTR_FIRMWARE_LATEST,
    ATTR_FIRMWARE_UPGRADE_AVAILABLE,
    ATTR_FIRMWARE_NOTES,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurer le capteur de firmware."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # On n'ajoute l'entité que si des données de firmware sont présentes
    async_add_entities([StorCubeFirmwareSensor(coordinator, config_entry)])

class StorCubeFirmwareSensor(CoordinatorEntity, SensorEntity):
    """Capteur pour les informations de firmware StorCube."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialiser le capteur de firmware."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        
        # Propriétés de base de l'entité
        self._attr_name = "Firmware StorCube"
        self._attr_unique_id = f"{config_entry.entry_id}_firmware"
        self._attr_icon = "mdi:update"
        
        # Device Info pour lier le capteur à l'appareil principal
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=NAME,
            manufacturer="StorCube",
        )

    @property
    def native_value(self) -> str | None:
        """Retourner l'état du capteur (version et statut)."""
        firmware_data = self.coordinator.data.get("firmware", {})
        current_version = firmware_data.get("current_version", "Inconnue")
        upgrade_available = firmware_data.get("upgrade_available", False)
        
        if upgrade_available:
            return f"Mise à jour disponible ({current_version})"
        return f"À jour ({current_version})"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Retourner les attributs supplémentaires à partir du coordinateur."""
        firmware_data = self.coordinator.data.get("firmware", {})
        
        return {
            ATTR_FIRMWARE_CURRENT: firmware_data.get("current_version", "Inconnue"),
            ATTR_FIRMWARE_LATEST: firmware_data.get("latest_version", "Inconnue"),
            ATTR_FIRMWARE_UPGRADE_AVAILABLE: firmware_data.get("upgrade_available", False),
            ATTR_FIRMWARE_NOTES: firmware_data.get("firmware_notes", []),
            "last_check": firmware_data.get("last_check", "Jamais"),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Gérer la mise à jour des données du coordinateur."""
        # Cette méthode est appelée automatiquement par CoordinatorEntity
        # Elle déclenche l'écriture de l'état dans HA
        self.async_write_ha_state()

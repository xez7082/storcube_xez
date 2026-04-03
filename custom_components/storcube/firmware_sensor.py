"""Capteur de firmware pour l'intégration StorCube Battery Monitor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
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
    """Setup firmware sensor."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([
        StorCubeFirmwareSensor(coordinator, config_entry)
    ])


class StorCubeFirmwareSensor(CoordinatorEntity, SensorEntity):
    """Sensor firmware StorCube."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)

        self.config_entry = config_entry

        self._attr_name = "StorCube Firmware"
        self._attr_unique_id = f"{config_entry.entry_id}_firmware"

        self._attr_icon = "mdi:update"
        self._attr_device_class = SensorDeviceClass.ENUM

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=NAME,
            manufacturer="StorCube",
        )

    # -------------------------
    # SAFE DATA ACCESS
    # -------------------------
    def _fw(self) -> dict[str, Any]:
        """Récupération sécurisée firmware."""
        data = self.coordinator.data or {}

        # compatible plusieurs structures possibles
        return (
            data.get("firmware")
            or data
            or {}
        )

    # -------------------------
    # STATE
    # -------------------------
    @property
    def native_value(self) -> str:
        fw = self._fw()

        current = fw.get("current_version", "Unknown")
        upgrade = bool(fw.get("upgrade_available", False))

        if upgrade:
            return f"Update available ({current})"

        return f"Up to date ({current})"

    # -------------------------
    # ATTRIBUTES
    # -------------------------
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        fw = self._fw()

        return {
            ATTR_FIRMWARE_CURRENT: fw.get("current_version", "Unknown"),
            ATTR_FIRMWARE_LATEST: fw.get("latest_version", "Unknown"),
            ATTR_FIRMWARE_UPGRADE_AVAILABLE: fw.get("upgrade_available", False),
            ATTR_FIRMWARE_NOTES: fw.get("firmware_notes", []),
        }

    # -------------------------
    # UPDATE HANDLING
    # -------------------------
    @callback
    def _handle_coordinator_update(self) -> None:
        """Sync HA state with coordinator."""
        self.async_write_ha_state()

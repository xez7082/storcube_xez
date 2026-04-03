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
    """Set up binary sensor platform."""
    coordinator: StorCubeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # 🔥 FIX: coordinator.data est un dict unique, pas une liste de devices
    async_add_entities([StorCubeBatteryConnectionSensor(coordinator)])


class StorCubeBatteryConnectionSensor(
    CoordinatorEntity[StorCubeDataUpdateCoordinator],
    BinarySensorEntity,
):
    """Binary sensor for battery connection status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True
    _attr_icon = ICON_CONNECTION

    def __init__(self, coordinator: StorCubeDataUpdateCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{DOMAIN}_connectivity"
        self._attr_name = "Connectivity"

        # 🔥 FIX: DeviceInfo doit être UNIQUE PAR DEVICE mais pas par entité si 1 device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator._device_id)},
            name=f"StorCube Battery {coordinator._device_id}",
            manufacturer="StorCube",
            model="Battery Monitor",
        )

    @property
    def is_on(self) -> bool:
        """Return connection status."""
        data = self.coordinator.data

        if not data:
            return False

        # 🔥 adapte selon ton API réelle
        status = data.get("is_online")

        if status is None:
            return False

        if isinstance(status, bool):
            return status

        if isinstance(status, (int, str)):
            return str(status) in ("1", "true", "True")

        return False

"""Services for StorCube Battery Monitor."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import async_get as dr_async_get
from homeassistant.helpers import device_registry as dr
from homeassistant.const import CONF_DEVICE_ID

from .const import (
    DOMAIN,
    SERVICE_CHECK_FIRMWARE,
    ATTR_FIRMWARE_CURRENT,
    ATTR_FIRMWARE_LATEST,
    ATTR_FIRMWARE_UPGRADE_AVAILABLE,
    ATTR_FIRMWARE_NOTES,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_POWER = "set_power"
SERVICE_SET_THRESHOLD = "set_threshold"

ATTR_POWER = "power"
ATTR_THRESHOLD = "threshold"
ATTR_DEVICE_ID = "device_id"


# -------------------------
# SCHEMAS
# -------------------------
SET_POWER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_POWER): vol.Coerce(int),
    }
)

SET_THRESHOLD_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_THRESHOLD): vol.All(int, vol.Range(min=0, max=100)),
    }
)


# -------------------------
# COORDINATOR FINDER SAFE
# -------------------------
async def _get_coordinator(hass: HomeAssistant, device_id: str):
    """Find coordinator safely."""

    if DOMAIN not in hass.data:
        raise HomeAssistantError("StorCube not loaded")

    # search through all entries
    for entry_id, entry_data in hass.data[DOMAIN].items():
        if not isinstance(entry_data, dict):
            continue

        coordinator = entry_data.get("coordinator")

        if not coordinator:
            continue

        # match device_id safely
        if getattr(coordinator, "_device_id", None) == device_id:
            return coordinator

    raise HomeAssistantError(f"Coordinator not found for device {device_id}")


# -------------------------
# SERVICES
# -------------------------
async def async_setup_services(hass: HomeAssistant) -> None:
    """Register StorCube services."""

    # POWER
    async def handle_set_power(call: ServiceCall) -> None:
        device_id = call.data[ATTR_DEVICE_ID]
        power = call.data[ATTR_POWER]

        coordinator = await _get_coordinator(hass, device_id)

        try:
            await coordinator.set_power_value(power)
        except Exception as err:
            _LOGGER.exception("set_power failed")
            raise HomeAssistantError(str(err)) from err

    # THRESHOLD
    async def handle_set_threshold(call: ServiceCall) -> None:
        device_id = call.data[ATTR_DEVICE_ID]
        threshold = call.data[ATTR_THRESHOLD]

        coordinator = await _get_coordinator(hass, device_id)

        try:
            await coordinator.set_threshold_value(threshold)
        except Exception as err:
            _LOGGER.exception("set_threshold failed")
            raise HomeAssistantError(str(err)) from err

    # FIRMWARE (response service)
    async def handle_check_firmware(call: ServiceCall) -> dict:
        device_id = call.data.get(ATTR_DEVICE_ID)

        coordinator = await _get_coordinator(hass, device_id)

        firmware = await coordinator.check_firmware_upgrade()

        if not firmware:
            return {
                "status": "no_data",
                ATTR_FIRMWARE_CURRENT: "Unknown",
                ATTR_FIRMWARE_LATEST: "Unknown",
                ATTR_FIRMWARE_UPGRADE_AVAILABLE: False,
                ATTR_FIRMWARE_NOTES: [],
            }

        return {
            "status": "ok",
            ATTR_FIRMWARE_CURRENT: firmware.get("current_version", "Unknown"),
            ATTR_FIRMWARE_LATEST: firmware.get("latest_version", "Unknown"),
            ATTR_FIRMWARE_UPGRADE_AVAILABLE: firmware.get(
                "upgrade_available", False
            ),
            ATTR_FIRMWARE_NOTES: firmware.get("firmware_notes", []),
        }

    # -------------------------
    # REGISTER SERVICES
    # -------------------------
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_POWER,
        handle_set_power,
        schema=SET_POWER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_THRESHOLD,
        handle_set_threshold,
        schema=SET_THRESHOLD_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_FIRMWARE,
        handle_check_firmware,
        schema=vol.Schema({ATTR_DEVICE_ID: cv.string}),
    )


# -------------------------
# UNLOAD
# -------------------------
async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister services."""
    for service in (
        SERVICE_SET_POWER,
        SERVICE_SET_THRESHOLD,
        SERVICE_CHECK_FIRMWARE,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)

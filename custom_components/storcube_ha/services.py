"""Services pour l'intégration Storcube Battery Monitor."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    SERVICE_CHECK_FIRMWARE,
    ATTR_FIRMWARE_CURRENT,
    ATTR_FIRMWARE_LATEST,
    ATTR_FIRMWARE_UPGRADE_AVAILABLE,
    ATTR_FIRMWARE_NOTES,
)

# Constantes de service
SERVICE_SET_POWER = "set_power"
SERVICE_SET_THRESHOLD = "set_threshold"

ATTR_POWER = "power"
ATTR_THRESHOLD = "threshold"

# Schémas de validation
SET_POWER_SCHEMA = cv.make_entity_service_schema({
    vol.Required(ATTR_POWER): cv.positive_int,
})

SET_THRESHOLD_SCHEMA = cv.make_entity_service_schema({
    vol.Required(ATTR_THRESHOLD): vol.All(
        vol.Coerce(int),
        vol.Range(min=0, max=100)
    ),
})

async def async_setup_services(hass: HomeAssistant) -> None:
    """Configurer les services pour l'intégration."""

    async def get_coordinator(call: ServiceCall):
        """Récupérer le coordinateur approprié pour l'appel de service."""
        # On cherche l'entity_id dans les données de l'appel
        device_id = call.data.get("device_id")
        if not device_id:
            # Si pas de device_id, on prend le premier disponible (fallback)
            if not hass.data.get(DOMAIN):
                raise HomeAssistantError("Storcube integration not loaded")
            return list(hass.data[DOMAIN].values())[0]["coordinator"]
        
        # Logique pour retrouver le coordinateur via le device registry
        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(device_id)
        if not device:
            raise HomeAssistantError(f"Device {device_id} not found")
            
        for entry_id in device.config_entries:
            if entry_id in hass.data[DOMAIN]:
                return hass.data[DOMAIN][entry_id]["coordinator"]
        
        raise HomeAssistantError("No coordinator found for this device")

    async def handle_set_power(call: ServiceCall) -> None:
        """Gérer le service set_power."""
        coordinator = await get_coordinator(call)
        power = call.data[ATTR_POWER]
        try:
            await coordinator.set_power_value(power)
        except Exception as err:
            raise HomeAssistantError(f"Error setting power: {err}") from err

    async def handle_set_threshold(call: ServiceCall) -> None:
        """Gérer le service set_threshold."""
        coordinator = await get_coordinator(call)
        threshold = call.data[ATTR_THRESHOLD]
        try:
            await coordinator.set_threshold_value(threshold)
        except Exception as err:
            raise HomeAssistantError(f"Error setting threshold: {err}") from err

    async def handle_check_firmware(call: ServiceCall) -> ServiceResponse:
        """Gérer le service check_firmware avec retour de données."""
        coordinator = await get_coordinator(call)
        firmware_info = await coordinator.check_firmware_upgrade()
        
        if not firmware_info:
            return {"status": "no_data"}

        return {
            ATTR_FIRMWARE_CURRENT: firmware_info.get("current_version", "Inconnue"),
            ATTR_FIRMWARE_LATEST: firmware_info.get("latest_version", "Inconnue"),
            ATTR_FIRMWARE_UPGRADE_AVAILABLE: firmware_info.get("upgrade_available", False),
            ATTR_FIRMWARE_NOTES: firmware_info.get("firmware_notes", [])
        }

    # Enregistrement des services
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
        schema=cv.make_entity_service_schema({}),
        supports_response=SupportsResponse.ONLY,
    )

async def async_unload_services(hass: HomeAssistant) -> None:
    """Décharger les services."""
    for service in [SERVICE_SET_POWER, SERVICE_SET_THRESHOLD, SERVICE_CHECK_FIRMWARE]:
        hass.services.async_remove(DOMAIN, service)

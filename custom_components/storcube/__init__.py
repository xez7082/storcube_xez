"""The Storcube integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import StorCubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Storcube from a config entry."""

    _LOGGER.debug("Starting Storcube integration for: %s", entry.title)

    # 🔥 SAFE INIT DOMAIN STORAGE
    hass.data.setdefault(DOMAIN, {})

    try:
        # Coordinator
        coordinator = StorCubeDataUpdateCoordinator(hass, entry)

        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
        }

        # FIRST REFRESH (critical)
        await coordinator.async_config_entry_first_refresh()

        # Forward platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    except Exception as err:
        _LOGGER.exception("Unable to setup Storcube integration")
        raise ConfigEntryNotReady(f"Storcube setup failed: {err}") from err

    # Optional services
    try:
        from .services import async_setup_services
        await async_setup_services(hass)
    except ImportError:
        _LOGGER.debug("No services module found (skipping)")
    except Exception as err:
        _LOGGER.exception("Error while setting up services: %s", err)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Storcube config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        domain_data = hass.data.get(DOMAIN)

        if domain_data:
            domain_data.pop(entry.entry_id, None)

        if not domain_data:
            hass.data.pop(DOMAIN, None)

    return unload_ok


# 🔥 FIX IMPORTANT POUR TON ERREUR ACTUELLE
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle config entry migrations (fix 'Migration handler not found')."""

    _LOGGER.debug("Migrating Storcube config entry %s", config_entry.entry_id)

    # no schema change yet
    return True

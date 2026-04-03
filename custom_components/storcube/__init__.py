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

    hass.data.setdefault(DOMAIN, {})

    try:
        coordinator = StorCubeDataUpdateCoordinator(hass, entry)

        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
        }

        # IMPORTANT: first refresh MUST NOT block forever (WS starts inside coordinator)
        await coordinator.async_config_entry_first_refresh()

        # Forward platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    except ConfigEntryNotReady:
        raise

    except Exception as err:
        _LOGGER.exception("Unable to setup Storcube integration")
        raise ConfigEntryNotReady(f"Storcube setup failed: {err}") from err

    # Optional services (safe import)
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

    # unload platforms first
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        domain_data = hass.data.get(DOMAIN)

        if domain_data:
            coordinator = domain_data.get(entry.entry_id, {}).get("coordinator")

            # 🔥 CLEAN STOP WS TASK
            if coordinator and hasattr(coordinator, "_ws_task"):
                task = coordinator._ws_task
                if task:
                    task.cancel()

            domain_data.pop(entry.entry_id, None)

        if not domain_data:
            hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_migrate_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Handle config entry migrations (fix 'Migration handler not found')."""

    _LOGGER.debug(
        "Migrating Storcube config entry %s (version %s)",
        config_entry.entry_id,
        config_entry.version,
    )

    # No schema changes yet
    return True

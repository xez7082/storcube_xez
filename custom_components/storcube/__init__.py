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
    """Set up a Storcube instance from the UI."""

    _LOGGER.debug("Starting Storcube integration for: %s", entry.title)

    # 1. Storage init
    hass.data.setdefault(DOMAIN, {})

    # 2. Coordinator init
    coordinator = StorCubeDataUpdateCoordinator(hass, entry)

    # 3. Optional setup (WebSocket, etc.)
    if hasattr(coordinator, "async_setup"):
        try:
            await coordinator.async_setup()
        except Exception as err:
            _LOGGER.exception("Error during coordinator setup: %s", err)

    # 4. First data refresh (MANDATORY)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.exception("Unable to fetch initial Storcube data")
        raise ConfigEntryNotReady(f"Connection error: {err}") from err

    # 5. Store coordinator
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # 6. Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 7. Optional services
    try:
        from .services import async_setup_services
    except ImportError:
        _LOGGER.debug("No services.py file found.")
    else:
        try:
            await async_setup_services(hass)
        except Exception:
            _LOGGER.exception("Error while setting up services")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Storcube config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok

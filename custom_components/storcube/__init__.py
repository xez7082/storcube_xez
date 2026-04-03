"""The Storcube integration."""

from __future__ import annotations

import logging
import json

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components import mqtt

from .const import DOMAIN, CONF_DEVICE_IDS
from .coordinator import StorCubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


# =========================================================
# SETUP ENTRY
# =========================================================
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Storcube from a config entry."""

    _LOGGER.debug("Starting Storcube integration for: %s", entry.title)

    hass.data.setdefault(DOMAIN, {})

    try:
        # 🔥 CREATE COORDINATOR
        coordinator = StorCubeDataUpdateCoordinator(hass, entry)

        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
        }

        # 🔥 FIRST REFRESH
        await coordinator.async_config_entry_first_refresh()

        # =========================================================
        # 🔥 MQTT SUBSCRIPTION (FIX PRINCIPAL)
        # =========================================================
        device_ids = entry.data.get(CONF_DEVICE_IDS, [])

        if not device_ids:
            raise ConfigEntryNotReady("No device IDs configured")

        device_id = device_ids[0]

        topic = f"storcube/{device_id}/#"

        _LOGGER.warning("Subscribing to MQTT topic: %s", topic)

        async def message_received(msg):
            try:
                payload = json.loads(msg.payload)

                _LOGGER.debug("MQTT RECEIVED: %s", payload)

                coordinator.update_from_ws(payload)

            except Exception as err:
                _LOGGER.error("MQTT parse error: %s", err)

        await mqtt.async_subscribe(hass, topic, message_received)

        # =========================================================
        # PLATFORMS
        # =========================================================
        await hass.config_entries.async_forward_entry_setups(
            entry,
            PLATFORMS,
        )

    except ConfigEntryNotReady:
        raise

    except Exception as err:
        _LOGGER.exception("Unable to setup Storcube integration")
        raise ConfigEntryNotReady(f"Storcube setup failed: {err}") from err

    # =========================================================
    # SERVICES (OPTIONAL)
    # =========================================================
    try:
        from .services import async_setup_services

        await async_setup_services(hass)

    except ImportError:
        _LOGGER.debug("No services module found (skipping services)")

    except Exception as err:
        _LOGGER.exception("Error while setting up services: %s", err)

    return True


# =========================================================
# UNLOAD ENTRY
# =========================================================
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Storcube config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        domain_data = hass.data.get(DOMAIN)

        if domain_data:
            entry_data = domain_data.get(entry.entry_id)

            if entry_data:
                coordinator = entry_data.get("coordinator")

                # 🔥 STOP WS TASK IF EXISTS
                ws_task = getattr(coordinator, "_ws_task", None)

                if ws_task:
                    try:
                        ws_task.cancel()
                    except Exception:
                        pass

                domain_data.pop(entry.entry_id, None)

        if not domain_data:
            hass.data.pop(DOMAIN, None)

    return unload_ok


# =========================================================
# MIGRATION HANDLER
# =========================================================
async def async_migrate_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Handle config entry migrations."""

    _LOGGER.debug(
        "Migrating Storcube entry %s from version %s",
        config_entry.entry_id,
        config_entry.version,
    )

    return True

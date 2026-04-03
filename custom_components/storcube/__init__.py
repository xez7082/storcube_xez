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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Storcube from a config entry."""

    _LOGGER.debug("Starting Storcube integration for: %s", entry.title)

    hass.data.setdefault(DOMAIN, {})

    try:
        coordinator = StorCubeDataUpdateCoordinator(hass, entry)

        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
        }

        await coordinator.async_config_entry_first_refresh()

        # =========================================================
        # MQTT SUBSCRIBE
        # =========================================================
        device_ids = entry.data.get(CONF_DEVICE_IDS, [])

        if not device_ids:
            raise ConfigEntryNotReady("No device IDs configured")

        device_id = device_ids[0]
        topic = f"storcube/{device_id}/#"

        _LOGGER.warning("Subscribing to MQTT topic: %s", topic)

        async def message_received(msg):
            try:
                if not msg.payload:
                    return

                payload = json.loads(msg.payload)

                _LOGGER.debug("MQTT RECEIVED (%s): %s", topic, payload)

                coordinator.update_from_ws(payload)

            except json.JSONDecodeError:
                _LOGGER.error("Invalid JSON payload: %s", msg.payload)

            except Exception as err:
                _LOGGER.exception("MQTT parse error: %s", err)

        unsubscribe = await mqtt.async_subscribe(
            hass,
            topic,
            message_received,
            qos=0,
        )

        # 🔥 important pour clean unload
        hass.data[DOMAIN][entry.entry_id]["unsubscribe"] = unsubscribe

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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Storcube config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        entry_data = hass.data[DOMAIN].get(entry.entry_id)

        if entry_data:
            unsubscribe = entry_data.get("unsubscribe")

            if unsubscribe:
                unsubscribe()

            hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok

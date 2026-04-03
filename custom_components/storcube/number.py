"""Number platform for StorCube Battery Monitor."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    NAME,
    SET_POWER_URL,
    SET_THRESHOLD_URL,
    TOKEN_URL,
    CONF_APP_CODE,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
)

_LOGGER = logging.getLogger(__name__)


# -------------------------
# SETUP
# -------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    entities = [
        StorcubePowerNumber(hass, config_entry),
        StorcubeThresholdNumber(hass, config_entry),
    ]

    async_add_entities(entities)


# -------------------------
# BASE CLASS
# -------------------------
class StorcubeBaseNumber(NumberEntity):
    """Base class for StorCube numbers."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.hass = hass
        self.config_entry = config_entry
        self._session = async_get_clientsession(hass)

        self._device_id = config_entry.data.get("device_id")

        self._token: str | None = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=NAME,
            manufacturer="StorCube",
        )

    # -------------------------
    # TOKEN (cached)
    # -------------------------
    async def _get_token(self) -> str | None:
        if self._token:
            return self._token

        payload = {
            "appCode": self.config_entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.config_entry.data.get(CONF_LOGIN_NAME),
            "password": self.config_entry.data.get(CONF_AUTH_PASSWORD),
        }

        try:
            async with self._session.post(
                TOKEN_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:

                data = await resp.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("Auth error: %s", err)
            return None

        if resp.status != 200 or data.get("code") != 200:
            _LOGGER.error("Auth failed: %s", data)
            return None

        token = (data.get("data") or {}).get("token")
        if not token:
            return None

        self._token = str(token)
        return self._token


# -------------------------
# POWER CONTROL
# -------------------------
class StorcubePowerNumber(StorcubeBaseNumber):
    """Power control."""

    def __init__(self, hass, config_entry) -> None:
        super().__init__(hass, config_entry)

        self._attr_name = "Power Output"
        self._attr_unique_id = f"{self._device_id}_power"

        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_native_min_value = 0
        self._attr_native_max_value = 800
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER

        self._attr_native_value = 100

    async def async_set_native_value(self, value: float) -> None:
        token = await self._get_token()
        if not token:
            return

        headers = {
            "Authorization": token,
            "appCode": "Storcube",
        }

        params = {
            "equipId": self._device_id,
            "power": int(value),
        }

        try:
            async with self._session.get(
                SET_POWER_URL,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:

                res = await resp.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("set_power error: %s", err)
            return

        if resp.status == 200 and res.get("code") == 200:
            self._attr_native_value = value
            self.async_write_ha_state()
        else:
            _LOGGER.error("set_power failed: %s", res)


# -------------------------
# THRESHOLD CONTROL
# -------------------------
class StorcubeThresholdNumber(StorcubeBaseNumber):
    """Battery threshold control."""

    def __init__(self, hass, config_entry) -> None:
        super().__init__(hass, config_entry)

        self._attr_name = "Battery Threshold"
        self._attr_unique_id = f"{self._device_id}_threshold"

        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER

        self._attr_native_value = 80

    async def async_set_native_value(self, value: float) -> None:
        token = await self._get_token()
        if not token:
            return

        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "appCode": "Storcube",
        }

        payload = {
            "equipId": self._device_id,
            "reserved": str(int(value)),
        }

        try:
            async with self._session.post(
                SET_THRESHOLD_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:

                res = await resp.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("set_threshold error: %s", err)
            return

        if resp.status == 200 and res.get("code") == 200:
            self._attr_native_value = value
            self.async_write_ha_state()
        else:
            _LOGGER.error("set_threshold failed: %s", res)

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    DOMAIN,
    CONF_DEVICE_IDS,
    CONF_APP_CODE,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
    TOKEN_URL,
    DETAIL_URL,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Handle Storcube API data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )

        self.entry = entry
        self.session = async_get_clientsession(hass)
        self._auth_token: str | None = None

        device_ids = entry.data.get(CONF_DEVICE_IDS, [])
        if not device_ids:
            raise ValueError("No device IDs configured")

        self._device_id = str(device_ids[0]).strip()

        self.data: dict[str, Any] = {
            "soc": 0.0,
            "power": 0.0,
            "pv1": 0.0,
            "is_online": False,
            "extra": {},
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value in (None, ""):
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if not self._auth_token:
                await self._async_renew_token()

            await self._async_update_rest_data()
            return dict(self.data)

        except ConfigEntryAuthFailed:
            raise

        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _async_renew_token(self) -> None:
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD],
        }

        async with self.session.post(
            TOKEN_URL, json=payload, timeout=10
        ) as resp:
            res = await resp.json()

            _LOGGER.debug("TOKEN RESPONSE: %s", res)

            if resp.status == 401:
                raise ConfigEntryAuthFailed("Invalid credentials")

            if resp.status == 200 and res.get("code") == 200:
                token = res["data"]["token"]
                self._auth_token = str(token).strip()
                return

            raise UpdateFailed(f"Auth failed: {res}")

    def _extract_values(self, raw_data: dict[str, Any]) -> None:
        _LOGGER.debug("Raw data (%s): %s", self._device_id, raw_data)

        self.data["extra"] = raw_data

        self.data["soc"] = self._safe_float(
            raw_data.get("soc")
            or raw_data.get("batteryLevel")
            or raw_data.get("reserved"),
            self.data["soc"],
        )

        self.data["power"] = self._safe_float(
            raw_data.get("outputPower")
            or raw_data.get("invPower")
            or raw_data.get("outPower"),
            self.data["power"],
        )

        self.data["pv1"] = self._safe_float(
            raw_data.get("pvPower")
            or raw_data.get("pv1Power")
            or raw_data.get("ppv"),
            self.data["pv1"],
        )

        online = raw_data.get("fgOnline") or raw_data.get("mainEquipOnline")
        self.data["is_online"] = str(online) == "1"

    async def _async_update_rest_data(self) -> None:
        if not self._auth_token:
            raise UpdateFailed("No auth token")

        # 🔥 FIX IMPORTANT : API attend souvent token direct ou Bearer
        headers = {
            "Authorization": f"Bearer {self._auth_token}",
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "Content-Type": "application/json",
        }

        url = f"{DETAIL_URL}{self._device_id}"

        _LOGGER.debug("REQUEST URL: %s", url)
        _LOGGER.debug("REQUEST HEADERS: %s", headers)

        async with self.session.get(
            url, headers=headers, timeout=15
        ) as resp:
            res = await resp.json()

            _LOGGER.debug("API RESPONSE (%s): %s", self._device_id, res)

            if resp.status == 401:
                self._auth_token = None
                raise UpdateFailed("Token expired")

            if resp.status == 200 and res.get("code") == 200:
                data_block = res.get("data")

                if data_block is None:
                    raise UpdateFailed("No data field in response")

                if isinstance(data_block, list):
                    if not data_block:
                        raise UpdateFailed("Empty device list")
                    data_block = data_block[0]

                if isinstance(data_block, dict):
                    self._extract_values(data_block)
                    return

                raise UpdateFailed("Invalid data format")

            raise UpdateFailed(f"API error: {res}")

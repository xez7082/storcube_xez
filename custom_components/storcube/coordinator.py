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

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="storcube",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )

        self.entry = entry
        self.session = async_get_clientsession(hass)
        self._auth_token: str | None = None

        # 🔥 SAFE DEVICE IDS HANDLING
        device_ids = entry.data.get(CONF_DEVICE_IDS)

        if not device_ids:
            raise ValueError("No device IDs configured")

        if isinstance(device_ids, str):
            device_ids = [device_ids]

        self._device_id = str(device_ids[0]).strip()

        self.data: dict[str, Any] = {
            "soc": 0.0,
            "power": 0.0,
            "pv1": 0.0,
            "is_online": False,
            "extra": {},
        }

    # -------------------------
    # UTILS
    # -------------------------
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value in (None, ""):
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    # -------------------------
    # MAIN LOOP
    # -------------------------
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

    # -------------------------
    # AUTH
    # -------------------------
    async def _async_renew_token(self) -> None:
        payload = {
            "appCode": self.entry.data.get(CONF_APP_CODE, "Storcube"),
            "loginName": self.entry.data[CONF_LOGIN_NAME],
            "password": self.entry.data[CONF_AUTH_PASSWORD],
        }

        async with self.session.post(TOKEN_URL, json=payload, timeout=10) as resp:
            res = await resp.json()

            _LOGGER.debug("TOKEN RESPONSE: %s", res)

            if resp.status == 401:
                raise ConfigEntryAuthFailed("Invalid credentials")

            if resp.status == 200 and res.get("code") == 200:
                token = (res.get("data") or {}).get("token")
                if not token:
                    raise UpdateFailed("Token missing in response")

                self._auth_token = str(token).strip()
                return

            raise UpdateFailed(f"Auth failed: {res}")

    # -------------------------
    # DATA PARSING
    # -------------------------
    def _extract_values(self, raw_data: dict[str, Any]) -> None:
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

    # -------------------------
    # API CALL (FINAL FIX CLEAN)
    # -------------------------
    async def _async_update_rest_data(self) -> None:
        if not self._auth_token:
            raise UpdateFailed("No auth token")

        headers = {
            "Authorization": self._auth_token,
            "Content-Type": "application/json",
        }

        url = DETAIL_URL
        params = {"equipId": self._device_id}

        _LOGGER.debug("REQUEST URL: %s", url)
        _LOGGER.debug("REQUEST PARAMS: %s", params)

        async with self.session.get(
            url,
            headers=headers,
            params=params,
            timeout=15,
        ) as resp:

            res = await resp.json()

            _LOGGER.debug("API RESPONSE (%s): %s", self._device_id, res)

            # AUTH EXPIRED
            if resp.status == 401 or res.get("code") == 401:
                self._auth_token = None
                raise ConfigEntryAuthFailed("Token expired")

            # SUCCESS
            if resp.status == 200 and res.get("code") == 200:
                data_block = res.get("data")

                # 🔥 IMPORTANT FIX: retry instead of crash
                if data_block in (None, 0, "", []):
                    _LOGGER.warning(
                        "Empty data received for device %s (retry later)",
                        self._device_id,
                    )
                    raise UpdateFailed("Empty API data")

                if isinstance(data_block, list):
                    data_block = data_block[0] if data_block else None

                if isinstance(data_block, dict):
                    self._extract_values(data_block)
                    return

                raise UpdateFailed(f"Invalid data format: {data_block}")

            raise UpdateFailed(f"API error: {res}")

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

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
    # SAFE CONVERT
    # -------------------------
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value in (None, "", "null"):
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    # -------------------------
    # MAIN UPDATE
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
    # AUTH (FIX IMPORTANT)
    # -------------------------
    async def _async_renew_token(self) -> None:
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)
        app_code = self.entry.data.get(CONF_APP_CODE, "Storcube")

        # 🔥 FIX CRITIQUE (TON BUG "凭据不能为空")
        if not login or not password:
            _LOGGER.error("Missing credentials: login=%s password=%s", login, password)
            raise ConfigEntryAuthFailed("Missing credentials")

        payload = {
            "appCode": app_code,
            "loginName": login,
            "password": password,
        }

        async with self.session.post(
            TOKEN_URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:

            res = await resp.json()
            _LOGGER.debug("TOKEN RESPONSE: %s", res)

            if resp.status == 401:
                raise ConfigEntryAuthFailed("Invalid credentials")

            if resp.status == 200 and res.get("code") == 200:
                token = (res.get("data") or {}).get("token")
                if not token:
                    raise UpdateFailed("Token missing")

                self._auth_token = str(token).strip()
                return

        raise UpdateFailed(f"Auth failed: {res}")

    # -------------------------
    # PARSE
    # -------------------------
    def _extract_values(self, raw_data: dict[str, Any]) -> None:
        self.data["extra"] = raw_data

        self.data["soc"] = self._safe_float(
            raw_data.get("soc")
            or raw_data.get("batteryLevel")
            or raw_data.get("reserved"),
        )

        self.data["power"] = self._safe_float(
            raw_data.get("outputPower")
            or raw_data.get("invPower")
            or raw_data.get("outPower"),
        )

        self.data["pv1"] = self._safe_float(
            raw_data.get("pvPower")
            or raw_data.get("pv1Power")
            or raw_data.get("ppv"),
        )

        online = raw_data.get("fgOnline") or raw_data.get("mainEquipOnline")
        self.data["is_online"] = str(online) in ("1", "true", "True")

    # -------------------------
    # API CALL
    # -------------------------
    async def _async_update_rest_data(self) -> None:
        if not self._auth_token:
            raise UpdateFailed("No auth token")

        headers = {
            "Authorization": self._auth_token,
        }

        params = {"equipId": self._device_id}

        _LOGGER.debug("REQUEST URL: %s", DETAIL_URL)
        _LOGGER.debug("REQUEST PARAMS: %s", params)

        try:
            async with self.session.get(
                DETAIL_URL,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:

                res = await resp.json()

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"HTTP error: {err}") from err

        _LOGGER.debug("API RESPONSE (%s): %s", self._device_id, res)

        # AUTH EXPIRED
        if resp.status == 401 or res.get("code") == 401:
            self._auth_token = None
            raise ConfigEntryAuthFailed("Token expired")

        # SUCCESS
        if resp.status == 200 and res.get("code") == 200:

            data_block = res.get("data")

            # 🔥 FIX: API retourne parfois 0 (cas réel chez toi)
            if data_block in (None, 0, "", [], {}):
                _LOGGER.warning(
                    "Empty API data (device=%s) -> keeping previous state",
                    self._device_id,
                )
                return

            if isinstance(data_block, list):
                data_block = data_block[0] if data_block else None

            if isinstance(data_block, dict):
                self._extract_values(data_block)
                return

            _LOGGER.warning("Unexpected data format: %s", data_block)
            return

        raise UpdateFailed(f"API error: {res}")

from __future__ import annotations

import logging
import asyncio
import json
import aiohttp
import websockets

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

        self.hass = hass
        self.entry = entry
        self.session = async_get_clientsession(hass)

        self._auth_token: str | None = None
        self._ws_task = None

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
    # START (IMPORTANT WS)
    # -------------------------
    async def async_config_entry_first_refresh(self):
        await self._async_renew_token()
        self._start_ws()
        return await super().async_config_entry_first_refresh()

    # -------------------------
    # AUTH ONLY
    # -------------------------
    async def _async_renew_token(self) -> None:
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)
        app_code = self.entry.data.get(CONF_APP_CODE, "Storcube")

        if not login or not password:
            _LOGGER.error("Missing credentials")
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

            if resp.status == 401:
                raise ConfigEntryAuthFailed("Invalid credentials")

            if resp.status == 200 and res.get("code") == 200:
                self._auth_token = (res.get("data") or {}).get("token")
                if not self._auth_token:
                    raise UpdateFailed("Token missing")
                return

        raise UpdateFailed(f"Auth failed: {res}")

    # -------------------------
    # WEBSOCKET START
    # -------------------------
    def _start_ws(self):
        if self._ws_task:
            return

        self._ws_task = self.hass.async_create_background_task(
            self._ws_loop(),
            "storcube_ws",
        )

    # -------------------------
    # WEBSOCKET LOOP
    # -------------------------
    async def _ws_loop(self):
        url = f"ws://baterway.com:9501/equip/info/{self._device_id}"

        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    _LOGGER.info("WebSocket connected")

                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)

                        _LOGGER.debug("WS DATA: %s", data)

                        self._extract_values(data)

                        # push update to HA
                        self.async_set_updated_data(dict(self.data))

            except Exception as err:
                _LOGGER.warning("WS error: %s (retry in 5s)", err)
                await asyncio.sleep(5)

    # -------------------------
    # PARSE DATA
    # -------------------------
    def _extract_values(self, raw_data: dict[str, Any]) -> None:
        self.data["extra"] = raw_data

        self.data["soc"] = self._safe_float(
            raw_data.get("soc") or raw_data.get("batteryLevel")
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
    # SAFE FLOAT
    # -------------------------
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value in (None, "", "null"):
                return default
            return float(value)
        except Exception:
            return default

    # -------------------------
    # KEEP ALIVE (NO REST POLLING)
    # -------------------------
    async def _async_update_data(self):
        return dict(self.data)

"""Gestion des mises à jour de firmware pour StorCube."""
from __future__ import annotations

import logging
import json
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import HomeAssistantError

from .const import (
    FIRMWARE_URL,
    TOKEN_URL,
    DEFAULT_APP_CODE,
)

_LOGGER = logging.getLogger(__name__)


class StorCubeFirmwareManager:
    """Firmware manager StorCube."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        login_name: str,
        auth_password: str,
        app_code: str = DEFAULT_APP_CODE,
    ):
        self.hass = hass
        self.device_id = device_id
        self.login_name = login_name
        self.auth_password = auth_password
        self.app_code = app_code

        self._session = async_get_clientsession(hass)
        self._token: str | None = None

    # -------------------------
    # AUTH (cached token)
    # -------------------------
    async def _get_auth_token(self) -> str | None:
        if self._token:
            return self._token

        payload = {
            "appCode": self.app_code,
            "loginName": self.login_name,
            "password": self.auth_password,
        }

        try:
            async with self._session.post(
                TOKEN_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:

                data = await resp.json()

                if resp.status != 200 or data.get("code") != 200:
                    _LOGGER.error("Auth error StorCube: %s", data)
                    return None

                token = (data.get("data") or {}).get("token")
                if not token:
                    _LOGGER.error("Token missing in response")
                    return None

                self._token = str(token).strip()
                return self._token

        except aiohttp.ClientError as err:
            _LOGGER.error("Auth request failed: %s", err)
            return None

    # -------------------------
    # FIRMWARE CHECK
    # -------------------------
    async def check_firmware_upgrade(self) -> dict[str, Any] | None:
        token = await self._get_auth_token()
        if not token:
            _LOGGER.warning("No token available for firmware check")
            return None

        headers = {
            "Authorization": token,
            "appCode": self.app_code,
            "accept-language": "fr-FR",
            "user-agent": "HomeAssistant-StorCube",
        }

        try:
            url = f"{FIRMWARE_URL}{self.device_id}"

            async with self._session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:

                data = await resp.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("Firmware HTTP error: %s", err)
            return None

        if resp.status != 200 or data.get("code") != 200:
            _LOGGER.error("Firmware API error: %s", data)
            return None

        fw = data.get("data") or {}

        # -------------------------
        # VERSION FIX LOGIC (SAFE)
        # -------------------------
        latest_version = (
            fw.get("lastBigVersion")
            or fw.get("currentBigVersion")
            or "Unknown"
        )

        current_version = fw.get("deviceVersion") or "Unknown"

        upgrade_available = bool(
            fw.get("upgread")  # API typo kept
            or fw.get("upgrade")
            or fw.get("updateAvailable")
        )

        # -------------------------
        # NOTES PARSING SAFE
        # -------------------------
        firmware_notes: list[str] = []

        for remark in fw.get("remarkList", []) or []:
            content = remark.get("remark", "")

            try:
                parsed = json.loads(content)
                firmware_notes.append(
                    parsed.get("fr")
                    or parsed.get("en")
                    or content
                )
            except (json.JSONDecodeError, TypeError):
                firmware_notes.append(content)

        return {
            "upgrade_available": upgrade_available,
            "current_version": current_version,
            "latest_version": latest_version,
            "firmware_notes": firmware_notes,
        }

    # -------------------------
    # HA FORMATTER
    # -------------------------
    async def get_firmware_info(self) -> dict[str, Any]:
        data = await self.check_firmware_upgrade()

        if not data:
            return {
                "current_version": "Unknown",
                "latest_version": "Unknown",
                "upgrade_available": False,
                "firmware_notes": [],
                "status": "error",
            }

        return {**data, "status": "ok"}

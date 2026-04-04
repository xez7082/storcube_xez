from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    PAYLOAD_KEY_SOC,
    PAYLOAD_KEY_POWER,
    PAYLOAD_KEY_PV,
    ATTR_EXTRA_STATE,
    SCAN_INTERVAL_SECONDS,
    TIMEOUT_SECONDS,
    DETAIL_URL,
    CONF_DEVICE_ID,
    CONF_LOGIN_NAME,
    CONF_AUTH_PASSWORD,
    TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinateur optimisé pour l'extraction des IDs réels."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.hass = hass
        self.entry = entry
        self._device_id = entry.data.get(CONF_DEVICE_ID)
        self._token: str | None = None
        self.data = {
            "soc": 0.0,
            "power": 0.0,
            "pv": 0.0,
            "online": False,
            ATTR_EXTRA_STATE: {},
        }

    async def _async_get_token(self) -> str | None:
        """Récupère le token d'authentification."""
        try:
            payload = {
                "loginName": self.entry.data.get(CONF_LOGIN_NAME),
                "password": self.entry.data.get(CONF_AUTH_PASSWORD),
                "appCode": "Storcube"
            }
            session = async_get_clientsession(self.hass)
            async with async_timeout.timeout(10):
                response = await session.post(TOKEN_URL, json=payload)
                res_data = await response.json()
                token = res_data.get("data", {}).get("token")
                return str(token) if token else None
        except Exception:
            _LOGGER.exception("Erreur Token")
            return None

    async def _async_discover_devices(self):
        """Sonde les endpoints pour trouver les IDs valides."""
        # On essaie les deux endpoints de liste connus
        for path in ["/api/equip/user/list", "/api/equip/list"]:
            url = f"http://baterway.com{path}"
            headers = {"token": self._token}
            try:
                session = async_get_clientsession(self.hass)
                async with session.get(url, headers=headers, timeout=10) as resp:
                    res = await resp.json()
                    devices = res.get("data", [])
                    if isinstance(devices, list) and len(devices) > 0:
                        _LOGGER.error(f"--- DÉCOUVERTE VIA {path} ---")
                        for d in devices:
                            # On logge uniquement le strict nécessaire pour éviter les coupures
                            d_id = d.get('id')
                            d_sn = d.get('deviceSn')
                            d_name = d.get('aliasName') or d.get('deviceName')
                            _LOGGER.error(f"TROUVÉ: [{d_name}] ID: {d_id} | SN: {d_sn}")
                        _LOGGER.error("----------------------------------")
                        return # On s'arrête si on a trouvé
            except Exception:
                continue

    async def _async_update_data(self) -> dict[str, Any]:
        """Polling des données."""
        if not self._token:
            self._token = await self._async_get_token()
            if self._token:
                await self._async_discover_devices()
            else:
                return self.data

        url = f"{DETAIL_URL}{self._device_id}"
        headers = {"token": self._token, "Content-Type": "application/json"}
        
        try:
            async with async_timeout.timeout(TIMEOUT_SECONDS):
                session = async_get_clientsession(self.hass)
                response = await session.get(url, headers=headers)
                payload = await response.json()
                
                data_part = payload.get("data")
                if isinstance(data_part, dict):
                    self._parse_payload(data_part)
                else:
                    _LOGGER.debug(f"ID {self._device_id} incorrect (data: 0). Utilise l'ID ou SN trouvé dans les logs ERROR.")
                
                return self.data
        except Exception as err:
            _LOGGER.debug("Erreur polling: %s", err)
            return self.data

    def update_from_ws(self, payload: dict[str, Any]) -> None:
        self._parse_payload(payload)
        self.async_set_updated_data(self.data)

    def _parse_payload(self, payload: dict[str, Any]) -> None:
        self.data[ATTR_EXTRA_STATE] = payload
        self.data["soc"] = self._to_float(payload.get(PAYLOAD_KEY_SOC), self.data["soc"])
        self.data["power"] = self._to_float(payload.get(PAYLOAD_KEY_POWER), self.data["power"])
        self.data["pv"] = self._to_float(payload.get(PAYLOAD_KEY_PV), self.data["pv"])
        online_val = payload.get("online") or payload.get("fgOnline")
        if online_val is not None:
            self.data["online"] = str(online_val).lower() in ("1", "true", "yes", "on", "online")

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value) if value not in (None, "") else default
        except (TypeError, ValueError):
            return default

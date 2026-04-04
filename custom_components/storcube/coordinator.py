from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN, SCAN_INTERVAL_SECONDS,
    CONF_LOGIN_NAME, CONF_AUTH_PASSWORD, TOKEN_URL,
    CONF_DEVICE_IDS,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self._token: str | None = None

    async def _async_get_token(self) -> str | None:
        login = self.entry.data.get(CONF_LOGIN_NAME)
        password = self.entry.data.get(CONF_AUTH_PASSWORD)
        payload = {"loginName": login, "password": password, "appCode": "Storcube"}
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.post(TOKEN_URL, json=payload)
                res_data = await response.json()
                return res_data.get("data", {}).get("token")
        except Exception as e:
            _LOGGER.error("Erreur Token : %s", e)
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        if not self._token:
            self._token = await self._async_get_token()
        if not self._token:
            raise UpdateFailed("Authentification échouée")

        session = async_get_clientsession(self.hass)
        headers = {"token": self._token, "appCode": "Storcube", "Content-Type": "application/json"}
        
        new_global_data = {}
        
        try:
            # On demande la liste globale des équipements
            list_url = "http://baterway.com/api/equip/list"
            
            async with async_timeout.timeout(10):
                async with session.get(list_url, headers=headers) as resp:
                    res = await resp.json()
                    _LOGGER.debug("Réponse Liste Storcube: %s", res)

                    # Analyse de la réponse 'data'
                    data_payload = res.get("data")
                    items = []

                    if isinstance(data_payload, list):
                        # Cas 1: 'data' est directement la liste
                        items = data_payload
                    elif isinstance(data_payload, dict):
                        # Cas 2: 'data' est un dictionnaire contenant 'list'
                        items = data_payload.get("list", [])
                    
                    # On traite les items trouvés
                    if items:
                        for item in items:
                            if isinstance(item, dict):
                                device_sn = str(item.get("deviceSn") or item.get("deviceId") or "")
                                if device_sn:
                                    new_global_data[device_sn] = item
                    else:
                        _LOGGER.debug("Aucun équipement trouvé dans 'data' (data=%s)", data_payload)
                        
                    # Si la liste est vide, on tente quand même le détail en dernier recours
                    if not new_global_data:
                        # On récupère les IDs configurés
                        device_ids = self.entry.data.get(CONF_DEVICE_IDS) or [self.entry.data.get("device_id")]
                        for d_id in device_ids:
                            detail_url = f"http://baterway.com/api/equip/detail?device_id={d_id}"
                            async with session.get(detail_url, headers=headers) as d_resp:
                                d_res = await d_resp.json()
                                if d_res.get("code") == 200 and isinstance(d_res.get("data"), dict):
                                    new_global_data[str(d_id)] = d_res["data"]

        except Exception as err:
            _LOGGER.error("Erreur lors de la récupération : %s", err)

        return new_global_data if new_global_data else self.data

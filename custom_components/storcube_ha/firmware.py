"""Gestion des mises à jour de firmware pour StorCube."""
from __future__ import annotations

import logging
import json
from typing import Any

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
    """Gestionnaire des mises à jour de firmware StorCube."""

    def __init__(self, hass: HomeAssistant, device_id: str, login_name: str, 
                 auth_password: str, app_code: str = DEFAULT_APP_CODE):
        """Initialiser le gestionnaire de firmware."""
        self.hass = hass
        self.device_id = device_id
        self.login_name = login_name
        self.auth_password = auth_password
        self.app_code = app_code
        self._session = async_get_clientsession(hass) # Utilisation de la session HA

    async def get_auth_token(self) -> str | None:
        """Obtenir le token d'authentification."""
        credentials = {
            "appCode": self.app_code,
            "loginName": self.login_name,
            "password": self.auth_password
        }
        headers = {"Content-Type": "application/json"}

        try:
            async with self._session.post(TOKEN_URL, json=credentials, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("code") == 200:
                        return data["data"]["token"]
                    _LOGGER.error("Erreur d'authentification StorCube: %s", data.get('message'))
                else:
                    _LOGGER.error("Erreur HTTP authentification: %s", response.status)
        except Exception as e:
            _LOGGER.error("Échec de connexion au serveur d'authentification: %s", e)
        return None

    async def check_firmware_upgrade(self) -> dict[str, Any] | None:
        """Vérifier si une mise à jour de firmware est disponible."""
        token = await self.get_auth_token()
        if not token:
            _LOGGER.warning("Impossible de vérifier le firmware sans token")
            return None

        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "appCode": self.app_code,
            "accept-language": "fr-FR",
            "user-agent": "HomeAssistant-StorCube-Integration"
        }

        try:
            url = f"{FIRMWARE_URL}{self.device_id}"
            async with self._session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    _LOGGER.error("Erreur HTTP firmware: %s", response.status)
                    return None
                
                data = await response.json()
                if data.get("code") != 200:
                    _LOGGER.error("Erreur API firmware: %s", data.get('message'))
                    return None

                fw_data = data.get("data", {})
                
                # Logique de version : currentBigVersion est souvent la cible (dernière version)
                latest_version = fw_data.get("currentBigVersion") or fw_data.get("lastBigVersion", "Inconnue")
                current_version = fw_data.get("lastBigVersion", "Inconnue")
                upgrade_available = fw_data.get("upgread", False) # Note: 'upgread' est une faute de frappe côté API StorCube
                
                # Traitement des notes de mise à jour
                firmware_notes = []
                for remark in fw_data.get("remarkList", []):
                    content = remark.get("remark", "")
                    try:
                        # Tentative de décodage si JSON (multi-langue)
                        notes_json = json.loads(content)
                        firmware_notes.append(notes_json.get("fr", notes_json.get("en", content)))
                    except (json.JSONDecodeError, TypeError):
                        firmware_notes.append(content)

                return {
                    "upgrade_available": upgrade_available,
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "firmware_notes": firmware_notes
                }

        except Exception as e:
            _LOGGER.error("Erreur lors de la vérification du firmware: %s", e)
            return None

    async def get_firmware_info(self) -> dict[str, Any]:
        """Obtenir les informations formatées pour les entités HA."""
        data = await self.check_firmware_upgrade()
        if not data:
            return {
                "current_version": "Inconnue",
                "latest_version": "Inconnue",
                "upgrade_available": False,
                "firmware_notes": [],
                "status": "error"
            }
        return {**data, "status": "ok"}

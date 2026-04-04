from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

# Import des constantes pour le mapping propre
from .const import (
    DOMAIN,
    PAYLOAD_KEY_SOC,
    PAYLOAD_KEY_POWER,
    PAYLOAD_KEY_PV,
    ATTR_EXTRA_STATE,
)

_LOGGER = logging.getLogger(__name__)

class StorCubeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinateur StorCube (Mode Push via MQTT / WebSocket)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # Mode push uniquement, pas de rafraîchissement forcé
        )

        self.hass = hass
        self.entry = entry

        # État interne initial
        self.data = {
            "soc": 0.0,
            "power": 0.0,
            "pv": 0.0,
            "online": False,
            ATTR_EXTRA_STATE: {},
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """
        HA appelle cette méthode au démarrage.
        On retourne les dernières données connues.
        """
        return self.data

    # =========================================================
    # POINT D'ENTRÉE MQTT / WS (PUSH)
    # =========================================================
    def update_from_ws(self, payload: dict[str, Any]) -> None:
        """Met à jour les données dès qu'un message MQTT arrive."""

        if not isinstance(payload, dict):
            _LOGGER.error("Payload reçu invalide (pas un dictionnaire)")
            return

        try:
            # On stocke le payload complet dans 'extra' pour les attributs
            self.data[ATTR_EXTRA_STATE] = payload

            # Mapping sécurisé via les constantes
            # On tente de récupérer les valeurs, sinon on garde l'ancienne
            self.data["soc"] = self._to_float(payload.get(PAYLOAD_KEY_SOC), self.data["soc"])
            self.data["power"] = self._to_float(payload.get(PAYLOAD_KEY_POWER), self.data["power"])
            self.data["pv"] = self._to_float(payload.get(PAYLOAD_KEY_PV), self.data["pv"])

            # Détection de l'état 'online'
            # On teste 'online' puis 'fgOnline' (vu dans tes logs précédents)
            online_val = payload.get("online") if payload.get("online") is not None else payload.get("fgOnline")
            
            if online_val is not None:
                self.data["online"] = str(online_val).lower() in ("1", "true", "yes", "on", "online")

            _LOGGER.debug("Mise à jour StorCube effectuée : %s", self.data)

            # 🔥 NOTIFICATION IMMEDIATE DE HOME ASSISTANT
            self.async_set_updated_data(self.data)

        except Exception as err:
            _LOGGER.error("Erreur lors du parsing des données MQTT : %s", err)

    # =========================================================
    # CONVERTISSEUR SÉCURISÉ
    # =========================================================
    def _to_float(self, value: Any, default: float = 0.0) -> float:
        """Convertit en float sans jamais faire planter l'intégration."""
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

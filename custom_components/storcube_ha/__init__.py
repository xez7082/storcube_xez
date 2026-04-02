"""The Storcube integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import StorCubeDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

# Plateformes à charger (Sensor pour les données, Number pour les réglages)
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Configuration via configuration.yaml (non recommandé mais supporté)."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration d'une instance via l'UI."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialisation du coordinateur personnalisé
    coordinator = StorCubeDataUpdateCoordinator(hass, entry)
    
    try:
        # Premier rafraîchissement des données (bloquant pour valider la connexion)
        await coordinator.async_config_entry_first_refresh()
        
        # Initialisation spécifique au coordinateur (Websocket, etc.)
        if hasattr(coordinator, "async_setup"):
            await coordinator.async_setup()
            
    except Exception as err:
        _LOGGER.error("Erreur d'initialisation Storcube pour %s: %s", entry.title, err)
        raise ConfigEntryNotReady from err

    # Stockage des données de l'instance
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Enregistrement des plateformes (sensor.py, number.py...)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Enregistrement des services (Set Power, Set Threshold)
    # On ne les enregistre qu'une seule fois même si on a plusieurs batteries
    await async_setup_services(hass)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement d'une instance de batterie."""
    # 1. Déchargement des plateformes
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # 2. Récupération et nettoyage du coordinateur
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator = entry_data.get("coordinator")
        
        if coordinator and hasattr(coordinator, "async_shutdown"):
            await coordinator.async_shutdown()
        
        # 3. Nettoyage des services globaux 
        # Uniquement s'il ne reste plus aucune instance Storcube active
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
            hass.data.pop(DOMAIN)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rechargement de l'intégration (utile après une erreur de connexion)."""
    await hass.config_entries.async_reload(entry.entry_id)

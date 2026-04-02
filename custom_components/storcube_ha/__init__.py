"""The Storcube Battery Monitor Integration."""
from __future__ import annotations

import logging
import asyncio
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import StorCubeDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

# Liste des plateformes à charger
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Configuration via configuration.yaml (Ancienne méthode)."""
    # Note: On favorise aujourd'hui le passage par l'interface UI (Config Flow)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration d'une instance via l'UI."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialisation du coordinateur
    coordinator = StorCubeDataUpdateCoordinator(hass, entry)
    
    try:
        # On attend la première récupération de données avant de continuer
        await coordinator.async_config_entry_first_refresh()
        # Si vous avez une méthode setup personnalisée supplémentaire :
        if hasattr(coordinator, "async_setup"):
            await coordinator.async_setup()
            
    except Exception as e:
        _LOGGER.error("Erreur lors de l'initialisation du coordinateur StorCube: %s", e)
        raise ConfigEntryNotReady from e

    # Stockage du coordinateur pour un accès facile
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Enregistrement des plateformes (sensor, number, etc.)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Configuration des services globaux de l'intégration
    await async_setup_services(hass)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement d'une instance."""
    # Déchargement des plateformes
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Nettoyage si le coordinateur a une fonction shutdown
        if hasattr(coordinator, "async_shutdown"):
            await coordinator.async_shutdown()
        
        # On ne décharge les services que s'il n'y a plus d'autre instance active
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rechargement de l'intégration."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

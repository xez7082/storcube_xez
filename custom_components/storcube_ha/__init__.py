"""The Storcube integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import StorCubeDataUpdateCoordinator

# On force l'utilisation du nom de dossier actuel pour le log
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration d'une instance Storcube via l'UI."""
    
    _LOGGER.debug("Démarrage de l'intégration Storcube pour : %s", entry.title)
    
    # 1. Préparation du stockage
    hass.data.setdefault(DOMAIN, {})
    
    # 2. Initialisation du coordinateur
    coordinator = StorCubeDataUpdateCoordinator(hass, entry)
    
    # 3. Setup additionnel (WebSocket, etc.)
    if hasattr(coordinator, "async_setup"):
        try:
            await coordinator.async_setup()
        except Exception as err:
            _LOGGER.error("Erreur lors du setup du coordinateur : %s", err)

    # 4. Premier rafraîchissement des données
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Impossible de récupérer les premières données Storcube : %s", err)
        raise ConfigEntryNotReady(f"Erreur de connexion : {err}") from err

    # 5. Stockage des objets
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # 6. Lancement des capteurs (sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Gestion des services optionnels
    try:
        from .services import async_setup_services
        await async_setup_services(hass)
    except (ImportError, Exception):
        _LOGGER.debug("Pas de fichier services.py ou erreur de chargement des services.")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement d'une instance."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
        
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok

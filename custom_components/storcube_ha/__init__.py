"""The Storcube integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import StorCubeDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

# Plateformes à charger
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration d'une instance Storcube via l'UI."""
    hass.data.setdefault(DOMAIN, {})
    
    # 1. Initialisation du coordinateur
    coordinator = StorCubeDataUpdateCoordinator(hass, entry)
    
    try:
        # 2. Lancer les écouteurs (WebSocket / MQTT) AVANT le refresh
        # Cela permet d'avoir des données prêtes dès le premier cycle
        if hasattr(coordinator, "async_setup"):
            await coordinator.async_setup()
            
        # 3. Premier rafraîchissement des données REST
        # On utilise async_config_entry_first_refresh pour bloquer l'UI tant que 
        # la première connexion n'est pas validée (ou timeout après 60s)
        await coordinator.async_config_entry_first_refresh()
            
    except Exception as err:
        _LOGGER.error(
            "Échec de l'initialisation Storcube pour %s: %s", 
            entry.title, 
            err
        )
        raise ConfigEntryNotReady from err

    # 4. Stockage du coordinateur pour accès par les plateformes
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # 5. Enregistrement des plateformes (sensor.py, number.py...)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # 6. Enregistrement des services globaux
    # On vérifie si les services sont déjà enregistrés pour éviter les doublons
    await async_setup_services(hass)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement d'une instance de batterie."""
    # 1. Déchargement des plateformes (sensor, number...)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # 2. Récupération des données pour nettoyage
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator = entry_data.get("coordinator")
        
        # 3. Arrêt propre des tâches de fond (WebSocket)
        if coordinator and hasattr(coordinator, "async_shutdown"):
            await coordinator.async_shutdown()
        
        # 4. Nettoyage final
        # Si c'était la dernière batterie, on retire les services et le domaine
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
            hass.data.pop(DOMAIN)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rechargement de l'intégration."""
    await hass.config_entries.async_reload(entry.entry_id)

"""The Storcube integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import StorCubeDataUpdateCoordinator

# On se concentre sur SENSOR pour l'instant pour valider la communication
PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration d'une instance Storcube via l'UI."""
    
    # 1. Préparation du stockage
    hass.data.setdefault(DOMAIN, {})
    
    # 2. Initialisation du coordinateur
    coordinator = StorCubeDataUpdateCoordinator(hass, entry)
    
    # 3. Lancer la configuration (WebSocket / MQTT)
    # On appelle async_setup du coordinateur s'il existe
    if hasattr(coordinator, "async_setup"):
        await coordinator.async_setup()

    # 4. Premier rafraîchissement des données
    # Si ça échoue ici, HA affichera l'erreur dans les logs au démarrage
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Erreur lors du premier refresh Storcube: %s", err)
        raise ConfigEntryNotReady(f"Connexion impossible : {err}") from err

    # 5. Stockage définitif AVANT de charger les capteurs
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # 6. Chargement des plateformes (appelle sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Optionnel : Services (vérifie que services.py existe bien dans ton dossier)
    try:
        from .services import async_setup_services
        await async_setup_services(hass)
    except ImportError:
        _LOGGER.debug("Fichier services.py non trouvé, ignore l'étape.")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement d'une instance."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Si plus aucune batterie, on nettoie le domaine
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok

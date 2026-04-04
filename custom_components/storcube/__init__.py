from __future__ import annotations

import logging
import json

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components import mqtt

# Import des constantes - Vérifie bien si c'est CONF_DEVICE_ID ou IDS
from .const import DOMAIN, CONF_DEVICE_ID
from .coordinator import StorCubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration de l'intégration Storcube."""

    _LOGGER.info("Démarrage de l'intégration Storcube pour : %s", entry.title)

    hass.data.setdefault(DOMAIN, {})

    coordinator = StorCubeDataUpdateCoordinator(hass, entry)

    # 1. Premier rafraîchissement (Données Cloud)
    # On le fait AVANT MQTT pour avoir des valeurs même si MQTT échoue
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Erreur lors du premier rafraîchissement Cloud : %s", err)
        # On continue quand même pour essayer MQTT

    # 2. Préparation du stockage des données
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "unsubscribe": None
    }

    # 3. Configuration MQTT (Optionnel/Non-bloquant)
    # Récupération de l'ID (on gère le cas où c'est une liste ou un string)
    raw_id = entry.data.get(CONF_DEVICE_ID)
    device_id = raw_id[0] if isinstance(raw_id, list) else raw_id

    if device_id:
        topic = f"storcube/{device_id}/#"
        
        async def message_received(msg):
            """Traitement des messages MQTT entrants."""
            try:
                payload = json.loads(msg.payload)
                _LOGGER.debug("MQTT REÇU (%s): %s", device_id, payload)
                # On envoie les données MQTT au coordinateur
                if hasattr(coordinator, 'update_from_ws'):
                    coordinator.update_from_ws(payload)
            except Exception as err:
                _LOGGER.error("Erreur lecture MQTT sur %s: %s", device_id, err)

        # On vérifie si MQTT est disponible avant de s'abonner
        if await mqtt.async_wait_for_mqtt_client(hass):
            _LOGGER.warning("Abonnement au topic MQTT : %s", topic)
            unsubscribe = await mqtt.async_subscribe(
                hass,
                topic,
                message_received,
                qos=0,
            )
            hass.data[DOMAIN][entry.entry_id]["unsubscribe"] = unsubscribe
        else:
            _LOGGER.warning("MQTT non disponible, l'intégration utilisera uniquement le Cloud.")
    else:
        _LOGGER.error("Aucun Device ID trouvé pour l'abonnement MQTT")

    # 4. Lancement des plateformes (Sensors)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement de l'intégration."""
    
    # Désabonnement MQTT
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data and entry_data.get("unsubscribe"):
        entry_data["unsubscribe"]()
        _LOGGER.info("Désabonnement MQTT effectué.")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok

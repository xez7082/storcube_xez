from __future__ import annotations

import logging
import json
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt

from .const import DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_IDS
from .coordinator import StorCubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration de l'intégration Storcube."""

    _LOGGER.info("Démarrage de l'intégration Storcube : %s", entry.title)

    # Initialisation du stockage des données
    hass.data.setdefault(DOMAIN, {})

    coordinator = StorCubeDataUpdateCoordinator(hass, entry)

    # 1. Premier rafraîchissement (Données Cloud/API)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning("Le rafraîchissement Cloud a échoué, on continue avec MQTT : %s", err)

    # 2. Préparation du stockage dans hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "unsubscribe": None
    }

    # 3. Récupération du Device ID (Nettoyage pour le topic MQTT)
    raw_id = entry.data.get(CONF_DEVICE_IDS) or entry.data.get(CONF_DEVICE_ID)
    
    # On s'assure d'avoir un ID propre (string sans espaces)
    if isinstance(raw_id, list) and len(raw_id) > 0:
        device_id = str(raw_id[0]).strip()
    else:
        device_id = str(raw_id).strip() if raw_id else None

    if device_id and device_id != "None":
        topic = f"storcube/{device_id}/#"
        
        async def _message_received(msg):
            """Callback lors de la réception d'un message MQTT."""
            try:
                payload = json.loads(msg.payload)
                # _LOGGER.debug("MQTT REÇU (%s): %s", device_id, payload)
                
                # On envoie les données au coordinateur pour mettre à jour les sensors
                if hasattr(coordinator, 'update_from_ws'):
                    coordinator.update_from_ws(payload)
                else:
                    # Si la méthode n'existe pas, on met à jour manuellement les données
                    coordinator.async_set_updated_data(payload)
                    
            except Exception as err:
                _LOGGER.error("Erreur lecture MQTT sur %s: %s", device_id, err)

        # 4. Abonnement MQTT (avec attente si nécessaire)
        async def _subscribe_mqtt():
            try:
                # On attend que le client MQTT soit connecté
                connected = await mqtt.async_wait_for_mqtt_client(hass)
                if connected:
                    _LOGGER.info("Abonnement au topic temps réel : %s", topic)
                    unsubscribe = await mqtt.async_subscribe(
                        hass,
                        topic,
                        _message_received,
                        qos=0,
                    )
                    hass.data[DOMAIN][entry.entry_id]["unsubscribe"] = unsubscribe
                else:
                    _LOGGER.error("Impossible de s'abonner au MQTT : Client non connecté")
            except Exception as err:
                _LOGGER.error("Erreur lors de l'abonnement MQTT : %s", err)

        # Lancement de l'abonnement en arrière-plan pour ne pas bloquer le démarrage
        entry.async_create_background_task(hass, _subscribe_mqtt(), "storcube_mqtt_sub")
        
    else:
        _LOGGER.error("ERREUR CRITIQUE : Aucun Device ID valide trouvé pour l'abonnement MQTT")

    # 5. Lancement des plateformes (sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement propre de l'intégration."""
    
    # Désabonnement MQTT
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data and entry_data.get("unsubscribe"):
        entry_data["unsubscribe"]()
        _LOGGER.info("Désabonnement MQTT Storcube effectué.")

    # Déchargement des plateformes
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

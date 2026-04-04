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

    # 1. Initialisation du coordinateur
    coordinator = StorCubeDataUpdateCoordinator(hass, entry)

    # 2. Premier rafraîchissement (Données Cloud/API)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning("Le rafraîchissement Cloud a échoué, on continue avec MQTT : %s", err)

    # 3. STOCKAGE CORRECT (L'objet coordinator doit être la racine)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 4. Préparation MQTT
    raw_id = entry.data.get(CONF_DEVICE_IDS) or entry.data.get(CONF_DEVICE_ID)
    
    # Extraction propre du premier ID pour l'écoute MQTT
    device_id = None
    if isinstance(raw_id, list) and len(raw_id) > 0:
        device_id = str(raw_id[0]).strip()
    elif raw_id:
        device_id = str(raw_id).strip()

    if device_id and device_id != "None":
        topic = f"storcube/{device_id}/#"
        
        async def _message_received(msg):
            """Callback lors de la réception d'un message MQTT."""
            try:
                payload = json.loads(msg.payload)
                # On met à jour le coordinateur (qui lui-même mettra à jour les sensors)
                coordinator.update_from_ws(payload)
            except Exception as err:
                _LOGGER.error("Erreur lecture MQTT sur %s: %s", device_id, err)

        async def _subscribe_mqtt():
            try:
                # On attend que le client MQTT soit prêt
                if await mqtt.async_wait_for_mqtt_client(hass):
                    _LOGGER.info("Abonnement au topic temps réel : %s", topic)
                    # On stocke l'unsubscribe dans l'objet coordinator pour le retrouver au déchargement
                    coordinator._mqtt_unsubscribe = await mqtt.async_subscribe(
                        hass,
                        topic,
                        _message_received,
                        qos=0,
                    )
            except Exception as err:
                _LOGGER.error("Erreur lors de l'abonnement MQTT : %s", err)

        # Lancement en arrière-plan
        entry.async_create_background_task(hass, _subscribe_mqtt(), "storcube_mqtt_sub")
    
    # 5. Lancement des plateformes (sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement propre de l'intégration."""
    
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    
    # Désabonnement MQTT si le listener existe
    if coordinator and hasattr(coordinator, "_mqtt_unsubscribe") and coordinator._mqtt_unsubscribe:
        coordinator._mqtt_unsubscribe()
        _LOGGER.info("Désabonnement MQTT Storcube effectué.")

    # Déchargement des plateformes
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

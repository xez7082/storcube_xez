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
    # Note: On ne bloque pas si ça échoue (car le Cloud renvoie souvent 0 pour les S1000)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.debug("Rafraîchissement initial Cloud vide (attente MQTT) : %s", err)

    # 3. Stockage du coordinateur
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 4. Préparation MQTT pour TOUS les appareils configurés
    # On récupère la liste des IDs (pour s'abonner aux deux batteries)
    device_ids = entry.data.get(CONF_DEVICE_IDS)
    if not device_ids:
        device_ids = [entry.data.get(CONF_DEVICE_ID)]

    # Nettoyage de la liste
    device_ids = [str(d).strip() for d in device_ids if d]

    async def _subscribe_mqtt():
        try:
            if not await mqtt.async_wait_for_mqtt_client(hass):
                _LOGGER.error("Le client MQTT n'est pas prêt")
                return

            coordinator._mqtt_unsubs = []

            for dev_id in device_ids:
                topic = f"storcube/{dev_id}/#"
                
                # Définition du callback pour cet ID spécifique
                def create_callback(d_id):
                    async def _msg_received(msg):
                        try:
                            payload = json.loads(msg.payload)
                            # CORRECTION ICI : Appel de la nouvelle fonction du coordinator
                            coordinator.update_from_mqtt(d_id, payload)
                        except Exception as err:
                            _LOGGER.error("Erreur lecture MQTT sur %s: %s", d_id, err)
                    return _msg_received

                _LOGGER.info("Abonnement au topic temps réel : %s", topic)
                unsub = await mqtt.async_subscribe(
                    hass,
                    topic,
                    create_callback(dev_id),
                    qos=0,
                )
                coordinator._mqtt_unsubs.append(unsub)

        except Exception as err:
            _LOGGER.error("Erreur lors de l'abonnement MQTT : %s", err)

    # Lancement de l'abonnement en arrière-plan
    entry.async_create_background_task(hass, _subscribe_mqtt(), "storcube_mqtt_sub")
    
    # 5. Lancement des plateformes (sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement propre de l'intégration."""
    
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    
    # Désabonnement de tous les topics MQTT
    if coordinator and hasattr(coordinator, "_mqtt_unsubs"):
        for unsub in coordinator._mqtt_unsubs:
            unsub()
        _LOGGER.info("Désabonnement MQTT Storcube effectué.")

    # Déchargement des plateformes
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

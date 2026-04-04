from __future__ import annotations

import logging
import json

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components import mqtt

# On importe les deux variantes par sécurité
from .const import DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_IDS
from .coordinator import StorCubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration de l'intégration Storcube."""

    _LOGGER.info("Démarrage de l'intégration Storcube pour : %s", entry.title)

    hass.data.setdefault(DOMAIN, {})

    coordinator = StorCubeDataUpdateCoordinator(hass, entry)

    # 1. Premier rafraîchissement (Données Cloud)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Erreur lors du premier rafraîchissement Cloud : %s", err)

    # 2. Préparation du stockage
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "unsubscribe": None
    }

    # 3. Récupération ROBUSTE du Device ID
    # On cherche dans 'device_ids' (liste) PUIS dans 'device_id' (string)
    raw_id = entry.data.get(CONF_DEVICE_IDS) or entry.data.get(CONF_DEVICE_ID)
    
    # Si c'est une liste, on prend le premier élément
    device_id = raw_id[0] if isinstance(raw_id, list) and len(raw_id) > 0 else raw_id

    if device_id:
        # Nettoyage de l'ID (au cas où il y aurait des espaces)
        device_id = str(device_id).strip()
        topic = f"storcube/{device_id}/#"
        
        async def message_received(msg):
            """Traitement des messages MQTT entrants."""
            try:
                payload = json.loads(msg.payload)
                _LOGGER.debug("MQTT REÇU (%s): %s", device_id, payload)
                if hasattr(coordinator, 'update_from_ws'):
                    coordinator.update_from_ws(payload)
            except Exception as err:
                _LOGGER.error("Erreur lecture MQTT sur %s: %s", device_id, err)

        # Vérification disponibilité MQTT
        try:
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
                _LOGGER.warning("MQTT non disponible (timeout client).")
        except Exception as mqtt_err:
            _LOGGER.error("Erreur lors de l'abonnement MQTT : %s", mqtt_err)
    else:
        # Log détaillé pour débogage si l'ID manque encore
        _LOGGER.error("Aucun Device ID trouvé. Clés dans entry.data: %s", list(entry.data.keys()))

    # 4. Lancement des plateformes
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement propre."""
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

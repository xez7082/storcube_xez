async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configuration des capteurs Storcube."""
    
    # On récupère les données stockées par __init__.py
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    _LOGGER.debug("Initialisation des capteurs pour le device: %s", entry.data.get("device_id"))

    # Création de la liste des entités
    entities = [
        StorcubeBatteryLevelSensor(coordinator, entry),
        StorcubeBatteryPowerSensor(coordinator, entry),
        StorcubeSolarPowerSensor(coordinator, entry, "1"),
        StorcubeSolarPowerSensor(coordinator, entry, "2"),
        StorcubeTemperatureSensor(coordinator, entry),
    ]

    async_add_entities(entities)

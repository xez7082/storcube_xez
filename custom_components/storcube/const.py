from __future__ import annotations
from typing import Final

# =========================================================
# BASE INFO
# =========================================================
DOMAIN: Final = "storcube"
NAME: Final = "Storcube"
VERSION: Final = "1.2.4"
MANUFACTURER: Final = "Storcube"
DEVELOPER: Final = "xez7082"

# =========================================================
# CONFIG KEYS (Coaching: attention à la cohérence avec config_flow.py)
# =========================================================
CONF_DEVICE_ID: Final = "device_id"
CONF_DEVICE_IDS: Final = "device_ids" # Utilisé pour le stockage en liste

CONF_APP_CODE: Final = "app_code"
CONF_LOGIN_NAME: Final = "login_name"
CONF_AUTH_PASSWORD: Final = "auth_password"

CONF_DEBUG: Final = "debug"

# MQTT CONFIG (Pour connexion au broker Baterway ou local)
CONF_MQTT_HOST: Final = "mqtt_host"
CONF_MQTT_PORT: Final = "mqtt_port"
CONF_MQTT_USER: Final = "mqtt_user"
CONF_MQTT_PASSWORD: Final = "mqtt_password"
CONF_MQTT_TOPIC: Final = "mqtt_topic"

# =========================================================
# DEFAULTS
# =========================================================
DEFAULT_APP_CODE: Final = "Storcube"
DEFAULT_MQTT_HOST: Final = "baterway.com"
DEFAULT_MQTT_PORT: Final = 1883
# Le topic doit correspondre à ce que la batterie envoie réellement
DEFAULT_MQTT_TOPIC: Final = "storcube/{device_id}/#"

# =========================================================
# API ENDPOINTS (REST fallback)
# =========================================================
BASE_URL: Final = "http://baterway.com"

TOKEN_URL: Final = f"{BASE_URL}/api/user/app/login"
# Correction: Ajout du ?equipId= pour faciliter la concaténation dans le coordinator
DETAIL_URL: Final = f"{BASE_URL}/api/equip/detail?equipId="
STATUS_URL: Final = f"{BASE_URL}/api/equip/status?equipId=" # Ajout de sécurité
SCENE_URL: Final = f"{BASE_URL}/api/scene/user/list/V2?equipId="
FIRMWARE_URL: Final = f"{BASE_URL}/api/equip/version/need/upgrade?equipId="

SET_POWER_URL: Final = f"{BASE_URL}/api/slb/equip/set/power"
SET_THRESHOLD_URL: Final = f"{BASE_URL}/api/scene/threshold/set"

# =========================================================
# MQTT PAYLOAD KEYS (Le nom des champs dans le JSON reçu)
# =========================================================
# Mapping payload → HA pour centraliser en cas de changement d'API
PAYLOAD_KEY_SOC: Final = "soc"
PAYLOAD_KEY_POWER: Final = "outputPower"
PAYLOAD_KEY_PV: Final = "pvPower"
PAYLOAD_KEY_ONLINE: Final = "online"

# =========================================================
# ICONS (MDI)
# =========================================================
ICON_BATTERY: Final = "mdi:battery"
ICON_POWER: Final = "mdi:transmission-tower"
ICON_SOLAR: Final = "mdi:solar-power"
ICON_FIRMWARE: Final = "mdi:update"

# =========================================================
# TIMING & TIMEOUTS
# =========================================================
SCAN_INTERVAL_SECONDS: Final = 30
TIMEOUT_SECONDS: Final = 15 # Réduit de 30 à 15 pour éviter de bloquer HA trop longtemps

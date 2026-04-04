from __future__ import annotations
from typing import Final
from datetime import timedelta

# =========================================================
# BASE INFO
# =========================================================
DOMAIN: Final = "storcube"
NAME: Final = "Storcube"
VERSION: Final = "1.2.4"
MANUFACTURER: Final = "Storcube"
DEVELOPER: Final = "xez7082"

# =========================================================
# CONFIG KEYS
# =========================================================
CONF_DEVICE_ID: Final = "device_id"
CONF_DEVICE_IDS: Final = "device_ids"

CONF_APP_CODE: Final = "app_code"
CONF_LOGIN_NAME: Final = "login_name"
CONF_AUTH_PASSWORD: Final = "auth_password"

CONF_DEBUG: Final = "debug"

# MQTT CONFIG
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
DEFAULT_MQTT_TOPIC: Final = "storcube/{device_id}/#"

# =========================================================
# API ENDPOINTS
# =========================================================
# On définit deux bases : HTTP pour le login, HTTPS pour les données
BASE_URL: Final = "http://baterway.com"
BASE_URL_SECURE: Final = "https://baterway.com"

# Login en HTTP (résout souvent l'erreur d'authentification sur leurs serveurs)
TOKEN_URL: Final = f"{BASE_URL}/api/user/app/login"

# Utilise DETAIL_URL pour récupérer les capteurs réels
DETAIL_URL: Final = f"{BASE_URL_SECURE}/api/equip/detail?equipId="
STATUS_URL: Final = f"{BASE_URL_SECURE}/api/equip/status?equipId="

SCENE_URL: Final = f"{BASE_URL_SECURE}/api/scene/user/list/V2?equipId="
FIRMWARE_URL: Final = f"{BASE_URL_SECURE}/api/equip/version/need/upgrade?equipId="

SET_POWER_URL: Final = f"{BASE_URL_SECURE}/api/slb/equip/set/power"
SET_THRESHOLD_URL: Final = f"{BASE_URL_SECURE}/api/scene/threshold/set"

# =========================================================
# PAYLOAD MAPPING (Clés JSON Batterie)
# =========================================================
PAYLOAD_KEY_SOC: Final = "soc"
PAYLOAD_KEY_POWER: Final = "outputPower"
PAYLOAD_KEY_PV: Final = "pvPower"
PAYLOAD_KEY_ONLINE: Final = "online"

# Clé pour les attributs étendus
ATTR_EXTRA_STATE: Final = "extra"

# =========================================================
# ICONS & TIMING
# =========================================================
ICON_BATTERY: Final = "mdi:battery"
ICON_POWER: Final = "mdi:transmission-tower"
ICON_SOLAR: Final = "mdi:solar-power"

SCAN_INTERVAL_SECONDS: Final = 30
TIMEOUT_SECONDS: Final = 15

# Intervalle formaté pour le coordinateur
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=SCAN_INTERVAL_SECONDS)

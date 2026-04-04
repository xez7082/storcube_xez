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
# CONFIG KEYS
# =========================================================
# On garde les deux pour la transition entre les versions de l'intégration
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
BASE_URL: Final = "http://baterway.com"

TOKEN_URL: Final = f"{BASE_URL}/api/user/app/login"
# URLs avec paramètre prêt pour l'ID
DETAIL_URL: Final = f"{BASE_URL}/api/equip/detail?equipId="
STATUS_URL: Final = f"{BASE_URL}/api/equip/status?equipId="
SCENE_URL: Final = f"{BASE_URL}/api/scene/user/list/V2?equipId="
FIRMWARE_URL: Final = f"{BASE_URL}/api/equip/version/need/upgrade?equipId="

SET_POWER_URL: Final = f"{BASE_URL}/api/slb/equip/set/power"
SET_THRESHOLD_URL: Final = f"{BASE_URL}/api/scene/threshold/set"

# =========================================================
# PAYLOAD MAPPING
# =========================================================
# Clés utilisées pour extraire les données du JSON (Cloud ou MQTT)
PAYLOAD_KEY_SOC: Final = "soc"
PAYLOAD_KEY_POWER: Final = "outputPower"
PAYLOAD_KEY_PV: Final = "pvPower"
PAYLOAD_KEY_ONLINE: Final = "online"

# Clé de stockage interne pour les attributs
ATTR_EXTRA_STATE: Final = "extra"

# =========================================================
# ICONS & TIMING
# =========================================================
ICON_BATTERY: Final = "mdi:battery"
ICON_POWER: Final = "mdi:transmission-tower"
ICON_SOLAR: Final = "mdi:solar-power"

SCAN_INTERVAL_SECONDS: Final = 30
TIMEOUT_SECONDS: Final = 15

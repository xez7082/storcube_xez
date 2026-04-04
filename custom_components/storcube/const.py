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

# =========================================================
# CONFIG KEYS (Alignement avec sensor.py)
# =========================================================
# On garde une seule clé principale pour éviter les erreurs dans sensor.py
CONF_DEVICE_ID: Final = "device_id" 
CONF_DEVICE_IDS: Final = "device_ids" # Utilisé si tu as plusieurs batteries

CONF_APP_CODE: Final = "app_code"
CONF_LOGIN_NAME: Final = "login_name"
CONF_AUTH_PASSWORD: Final = "auth_password"

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
# Le format de topic utilisé par Storcube pour le monitoring
DEFAULT_MQTT_TOPIC: Final = "storcube/{device_id}/#" 

# =========================================================
# API ENDPOINTS
# =========================================================
BASE_URL: Final = "http://baterway.com"

TOKEN_URL: Final = f"{BASE_URL}/api/user/app/login"
DETAIL_URL: Final = f"{BASE_URL}/api/equip/detail" # On retire le ? car on l'ajoute en paramètre
STATUS_URL: Final = f"{BASE_URL}/api/equip/status"

SET_POWER_URL: Final = f"{BASE_URL}/api/slb/equip/set/power"
SET_THRESHOLD_URL: Final = f"{BASE_URL}/api/scene/threshold/set"

# =========================================================
# PAYLOAD MAPPING (Pour la S1000)
# =========================================================
# Ces clés doivent correspondre aux noms dans les messages MQTT de la S1000
PAYLOAD_KEY_SOC: Final = "soc"
PAYLOAD_KEY_POWER: Final = "invPower" # Souvent 'invPower' sur S1000
PAYLOAD_KEY_PV: Final = "pv1power"    # Souvent 'pv1power' sur S1000
PAYLOAD_KEY_TEMP: Final = "temp"

# =========================================================
# ICONS & TIMING
# =========================================================
ICON_BATTERY: Final = "mdi:battery"
ICON_POWER: Final = "mdi:transmission-tower"
ICON_SOLAR: Final = "mdi:solar-power"

SCAN_INTERVAL_SECONDS: Final = 30
TIMEOUT_SECONDS: Final = 15

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=SCAN_INTERVAL_SECONDS)

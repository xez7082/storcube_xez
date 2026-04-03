from __future__ import annotations
from typing import Final

# Informations de base
DOMAIN: Final = "storcube"
NAME: Final = "Storcube"
VERSION: Final = "1.2.3"
MANUFACTURER: Final = "Storcube"
DEVELOPER: Final = "xez7082"

# Configuration des clés
CONF_DEVICE_ID: Final = "device_id"
CONF_DEVICE_IDS: Final = "device_ids"
CONF_APP_CODE: Final = "app_code"
CONF_LOGIN_NAME: Final = "login_name"
CONF_AUTH_PASSWORD: Final = "auth_password"
CONF_DEBUG: Final = "debug"

# Valeurs par défaut
DEFAULT_PORT: Final = 1883
DEFAULT_APP_CODE: Final = "Storcube"

# API BASE
BASE_URL: Final = "http://baterway.com"

# 🚨 FIX IMPORTANT : PAS DE QUERY STRING DANS LES CONST
TOKEN_URL: Final = f"{BASE_URL}/api/user/app/login"
DETAIL_URL: Final = f"{BASE_URL}/api/equip/detail"
SCENE_URL: Final = f"{BASE_URL}/api/scene/user/list/V2"
FIRMWARE_URL: Final = f"{BASE_URL}/api/equip/version/need/upgrade"
SET_POWER_URL: Final = f"{BASE_URL}/api/slb/equip/set/power"
SET_THRESHOLD_URL: Final = f"{BASE_URL}/api/scene/threshold/set"

# WebSocket
WS_URI: Final = "ws://baterway.com:9501/equip/info/"

# MQTT Topics
TOPIC_BASE: Final = "storcube/{device_id}"
TOPIC_STATUS: Final = "status"
TOPIC_POWER: Final = "power"
TOPIC_SOLAR: Final = "solar"
TOPIC_SET_POWER: Final = "set_power"
TOPIC_OUTPUT_POWER: Final = "outputPower"
TOPIC_SET_THRESHOLD: Final = "set_threshold"

# Icônes
ICON_BATTERY: Final = "mdi:battery"
ICON_POWER: Final = "mdi:transmission-tower"
ICON_SOLAR: Final = "mdi:solar-power"
ICON_FIRMWARE: Final = "mdi:update"

# Services
SERVICE_CHECK_FIRMWARE: Final = "check_firmware"
SERVICE_SET_POWER: Final = "set_power"
SERVICE_SET_THRESHOLD: Final = "set_threshold"

# Firmware attributes
ATTR_FIRMWARE_CURRENT: Final = "current_version"
ATTR_FIRMWARE_LATEST: Final = "latest_version"
ATTR_FIRMWARE_UPGRADE_AVAILABLE: Final = "upgrade_available"
ATTR_FIRMWARE_NOTES: Final = "firmware_notes"

# Timings
SCAN_INTERVAL_SECONDS: Final = 30
TIMEOUT_SECONDS: Final = 30

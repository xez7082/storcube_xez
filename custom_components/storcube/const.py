from __future__ import annotations
from typing import Final

# -------------------------
# BASE INFO
# -------------------------
DOMAIN: Final = "storcube"
NAME: Final = "Storcube"
VERSION: Final = "1.2.3"
MANUFACTURER: Final = "Storcube"
DEVELOPER: Final = "xez7082"

# -------------------------
# CONFIG KEYS
# -------------------------
CONF_DEVICE_ID: Final = "device_id"
CONF_DEVICE_IDS: Final = "device_ids"

CONF_APP_CODE: Final = "appCode"
CONF_LOGIN_NAME: Final = "loginName"
CONF_AUTH_PASSWORD: Final = "password"

CONF_DEBUG: Final = "debug"

# -------------------------
# DEFAULTS
# -------------------------
DEFAULT_APP_CODE: Final = "Storcube"

# -------------------------
# API (REST fallback only)
# -------------------------
BASE_URL: Final = "http://baterway.com"

TOKEN_URL: Final = f"{BASE_URL}/api/user/app/login"
DETAIL_URL: Final = f"{BASE_URL}/api/equip/detail"
SCENE_URL: Final = f"{BASE_URL}/api/scene/user/list/V2"
FIRMWARE_URL: Final = f"{BASE_URL}/api/equip/version/need/upgrade"
SET_POWER_URL: Final = f"{BASE_URL}/api/slb/equip/set/power"
SET_THRESHOLD_URL: Final = f"{BASE_URL}/api/scene/threshold/set"

# -------------------------
# MQTT CONFIG (MAIN CHANNEL)
# -------------------------
MQTT_HOST: Final = "baterway.com"
MQTT_PORT: Final = 1883

MQTT_BASE_TOPIC: Final = "storcube/{device_id}"

# data topics
MQTT_TOPIC_STATE: Final = "state"
MQTT_TOPIC_STATUS: Final = "status"
MQTT_TOPIC_POWER: Final = "power"
MQTT_TOPIC_SOLAR: Final = "solar"
MQTT_TOPIC_OUTPUT_POWER: Final = "outputPower"

# discovery prefix HA
MQTT_DISCOVERY_PREFIX: Final = "homeassistant"

# -------------------------
# WEBSOCKET (NOT USED)
# -------------------------
WS_URI: Final = "ws://baterway.com:9501/equip/info/"

# -------------------------
# ICONS
# -------------------------
ICON_BATTERY: Final = "mdi:battery"
ICON_POWER: Final = "mdi:transmission-tower"
ICON_SOLAR: Final = "mdi:solar-power"
ICON_FIRMWARE: Final = "mdi:update"

# -------------------------
# SERVICES
# -------------------------
SERVICE_CHECK_FIRMWARE: Final = "check_firmware"
SERVICE_SET_POWER: Final = "set_power"
SERVICE_SET_THRESHOLD: Final = "set_threshold"

# -------------------------
# FIRMWARE ATTRIBUTES
# -------------------------
ATTR_FIRMWARE_CURRENT: Final = "current_version"
ATTR_FIRMWARE_LATEST: Final = "latest_version"
ATTR_FIRMWARE_UPGRADE_AVAILABLE: Final = "upgrade_available"
ATTR_FIRMWARE_NOTES: Final = "firmware_notes"

# -------------------------
# TIMING
# -------------------------
SCAN_INTERVAL_SECONDS: Final = 30
TIMEOUT_SECONDS: Final = 30

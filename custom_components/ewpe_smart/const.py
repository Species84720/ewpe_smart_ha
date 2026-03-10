"""Constants for the EWPE Smart integration."""

DOMAIN = "ewpe_smart"
PLATFORMS = ["fan", "sensor"]

# Network
DEFAULT_PORT = 7000
BROADCAST_ADDRESS = "255.255.255.255"
SCAN_TIMEOUT = 5
SOCKET_TIMEOUT = 5

# Encryption
GENERIC_KEY = "a3K8Bx%2r8Y7#xDh"

# Coordinator
SCAN_INTERVAL_SECONDS = 30

# Device parameters - Air Purifier
PARAM_POWER = "Pow"
PARAM_MODE = "Mod"
PARAM_FAN_SPEED = "WdSpd"
PARAM_AIR_QUALITY = "Air"
PARAM_CHILD_LOCK = "StHt"
PARAM_SLEEP = "SwhSlp"
PARAM_LIGHT = "Lig"
PARAM_FILTER_RESET = "FilCln"
PARAM_AUTO_FAN = "AutoHt"
PARAM_PM25 = "PM25"
PARAM_FILTER_LIFE = "RstDust"

# Power values
POWER_ON = 1
POWER_OFF = 0

# Mode values
MODE_AUTO = 0
MODE_MANUAL = 1
MODE_SLEEP = 2

MODE_NAMES = {
    MODE_AUTO: "Auto",
    MODE_MANUAL: "Manual",
    MODE_SLEEP: "Sleep",
}

# Fan speed values (EWPE Smart uses 0-3 typically for purifiers)
FAN_SPEED_AUTO = 0
FAN_SPEED_LOW = 1
FAN_SPEED_MEDIUM = 2
FAN_SPEED_HIGH = 3

FAN_SPEED_NAMES = {
    FAN_SPEED_AUTO: "Auto",
    FAN_SPEED_LOW: "Low",
    FAN_SPEED_MEDIUM: "Medium",
    FAN_SPEED_HIGH: "High",
}

FAN_SPEED_TO_PCT = {
    FAN_SPEED_AUTO: 0,
    FAN_SPEED_LOW: 33,
    FAN_SPEED_MEDIUM: 66,
    FAN_SPEED_HIGH: 100,
}

PCT_TO_FAN_SPEED = {
    0: FAN_SPEED_AUTO,
    33: FAN_SPEED_LOW,
    66: FAN_SPEED_MEDIUM,
    100: FAN_SPEED_HIGH,
}

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_MAC = "mac"
CONF_DEVICE_KEY = "device_key"
CONF_NAME = "name"
CONF_UPDATE_INTERVAL = "update_interval"

# Default values
DEFAULT_UPDATE_INTERVAL = 30
DEFAULT_NAME = "Ergo Air Purifier"

# Sensor attributes
ATTR_PM25 = "pm25"
ATTR_FILTER_LIFE = "filter_life_remaining"
ATTR_AIR_QUALITY = "air_quality"

# Air quality index mapping
AIR_QUALITY_MAP = {
    0: "Excellent",
    1: "Good",
    2: "Moderate",
    3: "Poor",
}

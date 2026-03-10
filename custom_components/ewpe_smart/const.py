"""Constants for the EWPE Smart integration."""

DOMAIN = "ewpe_smart"
PLATFORMS = ["fan", "sensor", "select", "switch"]

# Network
DEFAULT_PORT = 7000
SOCKET_TIMEOUT = 5

# Encryption
GENERIC_KEY = "a3K8Bx%2r8Y7#xDh"

# Coordinator
SCAN_INTERVAL_SECONDS = 30

# ── Device parameter keys ───────────────────────────────────────────────────
PARAM_POWER       = "Pow"      # 0=off 1=on
PARAM_MODE        = "Mod"      # 0=Auto 1=Manual 2=Sleep
PARAM_FAN_SPEED   = "WdSpd"    # 0=Auto 1=Low 2=Med 3=High
PARAM_CHILD_LOCK  = "StHt"     # 0=unlocked 1=locked
PARAM_SLEEP       = "SwhSlp"   # 0=off 1=on
PARAM_LIGHT       = "Lig"      # 0=off 1=on
PARAM_PM25_A      = "PM25"     # PM2.5 µg/m³ (variant A – most devices)
PARAM_PM25_B      = "pm25"     # PM2.5 µg/m³ (variant B – lowercase)
PARAM_FILTER      = "RstDust"  # Filter allowance remaining 0-100 %
PARAM_AIR_QUALITY = "Air"      # 0=Excellent 1=Good 2=Moderate 3=Poor

# All params we request on every poll
ALL_PARAMS = [
    PARAM_POWER, PARAM_MODE, PARAM_FAN_SPEED,
    PARAM_CHILD_LOCK, PARAM_SLEEP, PARAM_LIGHT,
    PARAM_PM25_A, PARAM_PM25_B,
    PARAM_FILTER, PARAM_AIR_QUALITY,
]

# ── Value maps ───────────────────────────────────────────────────────────────
POWER_ON  = 1
POWER_OFF = 0

MODE_AUTO   = 0
MODE_MANUAL = 1
MODE_SLEEP  = 2

MODE_TO_NAME = {MODE_AUTO: "Auto", MODE_MANUAL: "Manual", MODE_SLEEP: "Sleep"}
NAME_TO_MODE = {v: k for k, v in MODE_TO_NAME.items()}
MODE_NAMES   = list(MODE_TO_NAME.values())

FAN_SPEED_AUTO   = 0
FAN_SPEED_LOW    = 1
FAN_SPEED_MEDIUM = 2
FAN_SPEED_HIGH   = 3

FAN_SPEED_TO_NAME = {
    FAN_SPEED_AUTO:   "Auto",
    FAN_SPEED_LOW:    "Low",
    FAN_SPEED_MEDIUM: "Medium",
    FAN_SPEED_HIGH:   "High",
}
NAME_TO_FAN_SPEED = {v: k for k, v in FAN_SPEED_TO_NAME.items()}
FAN_SPEED_NAMES   = list(FAN_SPEED_TO_NAME.values())

FAN_SPEED_TO_PCT = {
    FAN_SPEED_AUTO: 0, FAN_SPEED_LOW: 33,
    FAN_SPEED_MEDIUM: 66, FAN_SPEED_HIGH: 100,
}

AIR_QUALITY_MAP = {0: "Excellent", 1: "Good", 2: "Moderate", 3: "Poor"}

# ── Config entry keys ────────────────────────────────────────────────────────
CONF_HOST            = "host"
CONF_PORT            = "port"
CONF_MAC             = "mac"
CONF_DEVICE_KEY      = "device_key"
CONF_NAME            = "name"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 30
DEFAULT_NAME            = "Ergo Air Purifier"

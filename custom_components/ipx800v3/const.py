"""Constants for the ipx800v3 integration."""
DOMAIN = "ipx800v3"

CONTROLLER = "controller"
COORDINATOR = "coordinator"
UNDO_UPDATE_LISTENER = "undo_update_listener"
GLOBAL_PARALLEL_UPDATES = 1
PUSH_USERNAME = "ipx800"

DEFAULT_SCAN_INTERVAL = 10
DEFAULT_TRANSITION = 0.5
REQUEST_REFRESH_DELAY = 0.5

CONF_DEVICES = "devices"

CONF_COMPONENT = "component"
CONF_DEFAULT_BRIGHTNESS = "default_brightness"
CONF_ID = "id"
CONF_PUSH_PASSWORD = "push_password"
CONF_TRANSITION = "transition"
CONF_TYPE = "type"

TYPE_RELAY = "relay"
TYPE_DIGITALIN = "digitalin"


CONF_COMPONENT_ALLOWED = [
    "light",
    "switch",
    "binary_sensor"
]

CONF_TYPE_ALLOWED = [
    TYPE_RELAY,
    TYPE_DIGITALIN,
]

PLATFORMS = [
    "binary_sensor",
    "light",
    "switch",
]

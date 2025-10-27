"""Constants for the eWeLink IoT integration."""

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "ewelink_iot"
PLATFORMS: Final = [Platform.SWITCH]

# API URLs
API_BASE_URL: Final = "https://api.ewelink.cc/v2"
WS_BASE_URL: Final = "wss://api.ewelink.cc:8080/api/ws"

# Config entry keys
CONF_APP_ID: Final = "app_id"
CONF_APP_SECRET: Final = "app_secret"
CONF_REGION: Final = "region"

# Default values
DEFAULT_APP_ID: Final = "4s1FXKC9FaGfoqXhmXSJneb3qcm1gOak"
DEFAULT_APP_SECRET: Final = "oKvCM06gvwkRbfetd6qWRrbC3rFrbIpV"
DEFAULT_REGION: Final = "cn"

# Regions
REGIONS: Final = {
    "cn": "China",
    "as": "Asia",
    "us": "Americas",
    "eu": "Europe",
}

# Device types
DEVICE_TYPE_SWITCH: Final = "switch"

# Websocket message types
WS_MSG_TYPE_HANDSHAKE: Final = "handshake"
WS_MSG_TYPE_UPDATE: Final = "update"

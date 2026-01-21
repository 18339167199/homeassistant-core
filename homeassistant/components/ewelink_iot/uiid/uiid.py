"""Base uiid coordinator class."""

from enum import StrEnum
import numbers
from typing import Any

from homeassistant.components.light import DEFAULT_MAX_KELVIN, DEFAULT_MIN_KELVIN

from ..utils import deep_get

SINGLE_PROTOCOL_UIIDS = [1]
MULTIPLE_SINGLE_PROTOCOL_UIIDS = [191]
MULTIPLE_UIIDS = []
SWITCH_UIIDS = [
    *SINGLE_PROTOCOL_UIIDS,
    *MULTIPLE_SINGLE_PROTOCOL_UIIDS,
    *MULTIPLE_UIIDS,
]


class SELECT_TYPE(StrEnum):
    """Select type."""

    STARTUP = "startup"


class SENSOR_TYPE(StrEnum):
    """Sensor type."""

    RSSI = "rssi"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    BATTERY = "battery"


class BINARY_SENSOR_TYPE(StrEnum):
    """Binary sensor type."""

    DOOR = "door"
    HUMAN = "human"


class SWITCH_STATE(StrEnum):
    """Switch state enum."""

    OFF = "off"
    ON = "on"


class PLATFORM(StrEnum):
    """Platform enum."""

    SWITCH = "switch"
    SENSOR = "sensor"
    LIGHT = "light"
    BINARY_SENSOR = "binary_sensor"
    EVENT = "event"
    SELECT = "select"


class EVENT_ENTITY_TYPE(StrEnum):
    """Event entity type."""

    BUTTON = "button"


class EVNET_TYPE(StrEnum):
    """Event type."""

    SINGLE_PRESS = "single_press"
    DOUBLE_PRESS = "double_press"
    LONG_PRESS = "long_press"


class STARTUP_OPTONS(StrEnum):
    """Startup Options."""

    ON = "on"
    OFF = "off"
    STAY = "stay"


class Uiid:
    """EWeLink Switch Coordinator."""

    def __init__(self, uiid) -> None:
        """Init."""
        self.uiid = uiid

    def get_params(
        self, device: dict, keys: list[str | int], defaultValue: Any = None
    ) -> Any | None:
        """Get value from device params."""
        return deep_get(device, ["itemData", "params", *keys], defaultValue)

    @property
    def platform_config(self):
        """Platform placeholder."""
        return []

    @property
    def min_color_temp_kelvin(self) -> int:
        """Get light min color temp."""
        return DEFAULT_MIN_KELVIN

    @property
    def max_color_temp_kelvin(self) -> int:
        """Get light max color temp."""
        return DEFAULT_MAX_KELVIN

    @property
    def ha_brightness_range(self):
        """HA brightness range."""
        return [1, 255]

    def get_switch_value(self, device: dict) -> bool:
        """Get ewelink switch device switch state."""
        if self.uiid in MULTIPLE_SINGLE_PROTOCOL_UIIDS:
            return (
                deep_get(
                    device,
                    ["itemData", "params", "switches", 0, "switch"],
                    SWITCH_STATE.OFF,
                )
                == SWITCH_STATE.ON
            )

        return (
            deep_get(device, ["itemData", "params", "switch"], SWITCH_STATE.OFF)
            == SWITCH_STATE.ON
        )

    def gen_control_switch_params(self, is_on: bool):
        "Gen control switch params."
        target = SWITCH_STATE.ON if is_on else SWITCH_STATE.OFF
        if self.uiid in MULTIPLE_SINGLE_PROTOCOL_UIIDS:
            return {
                "switches": [
                    {"switch": target if i == 0 else SWITCH_STATE.OFF, "outlet": i}
                    for i in range(4)
                ]
            }
        return {"switch": target}

    def get_startup_value(self, device: dict, outlet: int | None = None) -> str | None:
        """Get device startup state."""
        if not self.uiid:
            return None
        if self.uiid in SINGLE_PROTOCOL_UIIDS:
            return self.get_params(device, ["startup"])
        if self.uiid in MULTIPLE_SINGLE_PROTOCOL_UIIDS:
            return self.get_params(device, ["configure", 0, "startup"])
        if self.uiid in MULTIPLE_UIIDS and outlet:
            return self.get_params(device, ["configure", outlet, "startup"])
        return None

    def gen_control_startup_params(self, startup: str, outlet: int | None = None):
        """Gen control startup params."""
        if not self.uiid:
            return None
        if self.uiid in SINGLE_PROTOCOL_UIIDS:
            return {"startup": startup}
        if self.uiid in MULTIPLE_SINGLE_PROTOCOL_UIIDS:
            return {"configure": [{"outlet": 0, "startup": startup}]}
        if self.uiid in MULTIPLE_UIIDS and outlet is not None:
            return {"configure": [{"outlet": outlet, "startup": startup}]}
        return None

    def get_rssi_value(self, device: dict) -> int | None:
        """Get Rssi value."""
        return deep_get(device, ["itemData", "params", "rssi"], None)

    def get_temperature_value(self, device: dict) -> int | float | None:
        """Get temperature value."""
        str_value = deep_get(device, ["itemData", "params", "temperature"], None)
        if str_value is not None:
            return round(float(str_value) / 100, 1)
        return None

    def get_humidity_value(self, device: dict) -> int | float | None:
        """Get humidity value."""
        str_value = deep_get(device, ["itemData", "params", "humidity"], None)
        if str_value is not None:
            return round(float(str_value) / 100, 1)
        return None

    def get_battery_value(self, device: dict) -> int | float | None:
        """Get battery value."""
        value = deep_get(device, ["itemData", "params", "battery"], None)
        if isinstance(value, numbers.Number):
            return round(value)  # pyright: ignore[reportArgumentType]
        return round(int(value))

    def get_door_lock_value(self, device: dict) -> bool | None:
        """Get door sensor lock value."""
        value = deep_get(device, ["itemData", "params", "lock"], None)
        return bool(value)

    def get_human_exsit_value(self, device: dict) -> bool | None:
        """Get human sensor exist value."""
        value = deep_get(device, ["itemData", "params", "human"], None)
        return bool(value)

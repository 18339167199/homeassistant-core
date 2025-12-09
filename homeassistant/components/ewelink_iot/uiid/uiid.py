"""Base uiid coordinator class."""

from enum import StrEnum
import numbers

from ..utils import deep_get, get_device_uiid

SINGLE_PROTOCOL_UIIDS = [1]
MULTIPLE_SINGLE_PROTOCOL_UIIDS = [191]
SWITCH_UIIDS = [
    *SINGLE_PROTOCOL_UIIDS,
    *MULTIPLE_SINGLE_PROTOCOL_UIIDS,
]


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


class EVENT_ENTITY_TYPE(StrEnum):
    """Event entity type."""

    BUTTON = "button"


class EVNET_TYPE(StrEnum):
    """Event type."""

    SINGLE_PRESS = "single_press"
    DOUBLE_PRESS = "double_press"
    LONG_PRESS = "long_press"


class Uiid:
    """EWeLink Switch Coordinator."""

    def __init__(self, uiid) -> None:
        """Init."""
        self.uiid = uiid

    @property
    def platform_config(self):
        """Platform placeholder."""
        return []

    def get_switch_state(self, device: dict) -> bool:
        """Get ewelink switch device switch state."""
        uiid = get_device_uiid(device)
        if uiid in SINGLE_PROTOCOL_UIIDS:
            return (
                deep_get(device, ["itemData", "params", "switch"], SWITCH_STATE.OFF)
                == SWITCH_STATE.ON
            )
        if uiid in MULTIPLE_SINGLE_PROTOCOL_UIIDS:
            return (
                deep_get(
                    device,
                    ["itemData", "params", "switches", 0, "switch"],
                    SWITCH_STATE.OFF,
                )
                == SWITCH_STATE.ON
            )
        return False

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

    def get_rssi_value(self, device: dict) -> int | None:
        """Get Rssi value."""
        return deep_get(device, ["itemData", "params", "rssi"], None)

    def get_temperature_value(self, device: dict) -> numbers.Number | None:
        """Get temperature value."""
        str_value = deep_get(device, ["itemData", "params", "temperature"], None)
        if str_value is not None:
            return round(float(str_value) / 100, 1)
        return None

    def get_humidity_value(self, device: dict) -> numbers.Number | None:
        """Get humidity value."""
        str_value = deep_get(device, ["itemData", "params", "humidity"], None)
        if str_value is not None:
            return round(float(str_value) / 100, 1)
        return None

    def get_battery_value(self, device: dict) -> int | None:
        """Get battery value."""
        value = deep_get(device, ["itemData", "params", "battery"], None)
        if isinstance(value, numbers.Number):
            return round(value)
        return round(int(value))

    def get_door_lock_value(self, device: dict) -> bool | None:
        """Get door sensor lock value."""
        value = deep_get(device, ["itemData", "params", "lock"], None)
        return bool(value)

    def get_human_exsit_value(self, device: dict) -> bool | None:
        """Get human sensor exist value."""
        value = deep_get(device, ["itemData", "params", "human"], None)
        return bool(value)

    def get_light_on_state(self, device: dict) -> bool:
        """Return True if light is on."""
        return deep_get(device, ["itemData", "params", "switch"]) == SWITCH_STATE.ON

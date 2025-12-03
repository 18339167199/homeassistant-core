"""Uiid 7003: door sensor."""

from .uiid import BINARY_SENSOR_TYPE, PLATFORM, SENSOR_TYPE, Uiid


class Uiid7003(Uiid):
    """Uiid 7003."""

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(uiid=7003)

    @property
    def platform_config(self) -> list:
        """Platform config."""
        return [
            {"platform": PLATFORM.BINARY_SENSOR, "type": BINARY_SENSOR_TYPE.DOOR},
            {"platform": PLATFORM.SENSOR, "type": SENSOR_TYPE.RSSI},
            {"platform": PLATFORM.SENSOR, "type": SENSOR_TYPE.BATTERY},
        ]

"""Uiid 7014: Temperature and humidity sensor with display screen."""

from .uiid import PLATFORM, SENSOR_TYPE, Uiid


class Uiid7014(Uiid):
    """Uiid 7014."""

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(uiid=7014)

    @property
    def platform_config(self) -> list:
        """Platform config."""
        return [
            {
                "platform": PLATFORM.SENSOR,
                "type": SENSOR_TYPE.TEMPERATURE,
            },
            {
                "platform": PLATFORM.SENSOR,
                "type": SENSOR_TYPE.HUMIDITY,
            },
            {"platform": PLATFORM.SENSOR, "type": SENSOR_TYPE.RSSI},
            {"platform": PLATFORM.SENSOR, "type": SENSOR_TYPE.BATTERY},
        ]

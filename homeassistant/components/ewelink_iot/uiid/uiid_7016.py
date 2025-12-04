"""Uiid 7016: Temperature and humidity sensor with display screen."""

from .uiid import BINARY_SENSOR_TYPE, PLATFORM, SENSOR_TYPE, Uiid


class Uiid7016(Uiid):
    """Uiid 7016."""

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(uiid=7016)

    @property
    def platform_config(self) -> list:
        """Platform config."""
        return [
            {"platform": PLATFORM.BINARY_SENSOR, "type": BINARY_SENSOR_TYPE.HUMAN},
            {"platform": PLATFORM.SENSOR, "type": SENSOR_TYPE.RSSI},
        ]

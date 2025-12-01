"""UIID 191: single switch device."""

from .uiid import PLATFORM, SENSOR_TYPE, Uiid


class Uiid191(Uiid):
    """For handle uiid 191 data coordinator."""

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(uiid=191)

    @property
    def platform_config(self) -> list:
        """Platform config."""
        return [
            {"platform": PLATFORM.SWITCH},
            {
                "platform": PLATFORM.SENSOR,
                "type": SENSOR_TYPE.RSSI,
            },
        ]

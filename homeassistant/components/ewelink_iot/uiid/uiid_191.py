"""UIID 191: single switch device."""

from .uiid import PLATFORM, SELECT_TYPE, SENSOR_TYPE, STARTUP_OPTONS, Uiid


class Uiid191(Uiid):
    """Uiid 191."""

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(uiid=191)

    @property
    def platform_config(self) -> list:
        """Platform config."""
        return [
            {"platform": PLATFORM.SWITCH},
            {"platform": PLATFORM.SENSOR, "type": SENSOR_TYPE.RSSI},
            {
                "platform": PLATFORM.SELECT,
                "type": SELECT_TYPE.STARTUP,
                "config": {
                    "options": [
                        STARTUP_OPTONS.ON,
                        STARTUP_OPTONS.OFF,
                        STARTUP_OPTONS.STAY,
                    ]
                },
            },
        ]

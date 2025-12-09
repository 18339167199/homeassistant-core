"""Uiid 104: single switch device."""

from homeassistant.components.light import ColorMode

from .uiid import PLATFORM, Uiid
from .utils import deep_get


class Uiid104(Uiid):
    """Uiid 104."""

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(uiid=104)

    @property
    def platform_config(self) -> list:
        """Platform config."""
        return [
            {
                "platform": PLATFORM.LIGHT,
                "config": {
                    "supported_color_modes": [
                        ColorMode.BRIGHTNESS,
                        ColorMode.COLOR_TEMP,
                        ColorMode.RGB,
                    ]
                },
            }
        ]

    def get_ltype(self, device: dict) -> str:
        """Get light ltype."""
        return deep_get(device, ["itemData", "params", "ltype"], "white")

    def get_ha_light_mode(self, device: dict):
        """Return HA ColorMode type."""
        ltype = self.get_ltype(device)
        match ltype:
            case "color":
                return ColorMode.RGB
            case _:
                return ColorMode.COLOR_TEMP

    def get_color_rgb(self, device: dict) -> tuple[int, int, int] | None:
        """Return light color rgb tuple."""
        color = deep_get(device, ["itemData", "params", "color"], {})
        if isinstance(color, dict):
            r = color.get("r")
            g = color.get("g")
            b = color.get("b")
            return (r, g, b)
        return (100, 100, 100)

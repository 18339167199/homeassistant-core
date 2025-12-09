"""Uiid 104: single switch device."""

import numbers

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
        return [{"platform": PLATFORM.LIGHT}]

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Supported color modes."""
        return {ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.RGB}

    @property
    def max_color_temp_kelvin(self) -> int:
        """Get light max color temp."""
        return 6535

    @property
    def min_color_temp_kelvin(self) -> int:
        """Get light min color temp."""
        return 2000

    def get_ltype(self, device: dict) -> str:
        """Get light ltype."""
        return deep_get(device, ["itemData", "params", "ltype"], "white")

    def get_color_mode(self, device: dict):
        """Return HA ColorMode type."""
        ltype = self.get_ltype(device)
        match ltype:
            case "color":
                return ColorMode.RGB
            case _:
                return ColorMode.COLOR_TEMP

    def get_brightess(self, device: dict) -> int | None:
        """Get light brightess."""
        ltype = self.get_ltype(device)
        return deep_get(device, ["itemData", "params", ltype, "br"])

    def get_color_rgb(self, device: dict) -> tuple[int, int, int] | None:
        """Return light color rgb tuple."""
        color = deep_get(device, ["itemData", "params", "color"], {})
        if isinstance(color, dict):
            r = color.get("r")
            g = color.get("g")
            b = color.get("b")
            return (r, g, b)
        return (100, 100, 100)

    def get_color_temp_kelvin(self, device: dict) -> int | None:
        """Get color temp kelvin."""
        ltype = self.get_ltype(device)
        ct = deep_get(device, ["itemData", "params", ltype, "ct"])  # range: 0-255
        if isinstance(ct, numbers.Number):
            if ct <= 0:
                return self.min_color_temp_kelvin
            if ct >= 255:
                return self.max_color_temp_kelvin
            return int(
                (self.max_color_temp_kelvin - self.min_color_temp_kelvin) / 255 * ct
                + self.min_color_temp_kelvin
            )
        return None

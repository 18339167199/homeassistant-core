"""Uiid 104: single switch device."""

import numbers

from homeassistant.components.light import ColorMode

from .uiid import PLATFORM, Uiid
from .utils import deep_get, map_value_general


class Uiid104(Uiid):
    """Uiid 104."""

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(uiid=104)
        self.ewelink_color_temp_range = [0, 255]
        self.ewelink_brightness_range = [1, 100]

    @property
    def platform_config(self) -> list:
        """Platform config."""
        return [{"platform": PLATFORM.LIGHT}]

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Supported color modes."""
        return {ColorMode.COLOR_TEMP, ColorMode.RGB}

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
        try:
            ltype = self.get_ltype(device)
            br: int = deep_get(device, ["itemData", "params", ltype, "br"])
            if isinstance(br, numbers.Number):
                return round(
                    map_value_general(
                        br, self.ewelink_brightness_range, self.ha_brightness_range
                    )
                )
        except ValueError:
            return None
        else:
            return None

    def get_color_rgb(self, device: dict) -> tuple | None:
        """Return light color rgb tuple."""
        color = deep_get(device, ["itemData", "params", "color"], {})
        if isinstance(color, dict):
            r: int | None = color.get("r")
            g: int | None = color.get("g")
            b: int | None = color.get("b")
            if r is not None and g is not None and b is not None:
                return (r, g, b)
        return (100, 100, 100)

    def get_color_temp_kelvin(self, device: dict) -> int | None:
        """Get color temp kelvin."""
        try:
            ltype = self.get_ltype(device)
            ct: int = deep_get(
                device, ["itemData", "params", ltype, "ct"]
            )  # range: 0-255
            if isinstance(ct, numbers.Number):
                return round(
                    map_value_general(
                        ct,
                        self.ewelink_color_temp_range,
                        [self.min_color_temp_kelvin, self.max_color_temp_kelvin],
                    )
                )
        except ValueError:
            return None
        else:
            return None

    def gen_control_color_temp_params(self, device: dict, color_temp_kelvin: int):
        """Gen control color temp params."""
        br = deep_get(device, ["itemData", "params", "white", "br"], 50)
        ct = map_value_general(
            color_temp_kelvin,
            [self.min_color_temp_kelvin, self.max_color_temp_kelvin],
            self.ewelink_color_temp_range,
        )
        return {"ltype": "white", "white": {"br": br, "ct": round(ct)}}

    def gen_control_color_rgb_params(self, device: dict, color_rgb: tuple):
        """Gen control color rgb params."""
        br = deep_get(device, ["itemData", "params", "color", "br"], 50)
        r, g, b = color_rgb
        return {"ltype": "color", "color": {"r": r, "g": g, "b": b, "br": br}}

    def gen_control_brightness_params(self, device: dict, brightness: int):
        """Gen control brightness params."""
        ltype = self.get_ltype(device)
        params: dict = {"ltype": ltype}
        ewelinl_br = round(
            map_value_general(
                brightness, self.ha_brightness_range, self.ewelink_brightness_range
            )
        )
        if ltype == "color":
            ewelink_color = deep_get(device, ["itemData", "params", "color"], {})
            params["color"] = {
                "br": ewelinl_br,
                "r": ewelink_color.get("r", 100),
                "g": ewelink_color.get("g", 100),
                "b": ewelink_color.get("b", 100),
            }
        else:
            params["white"] = {
                "br": ewelinl_br,
                "ct": deep_get(device, ["itemData", "params", "white", "ct"], 100),
            }
        return params

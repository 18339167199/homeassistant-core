"""Uiid 1: single switch device."""

from .uiid import PLATFORM, Uiid


class Uiid1(Uiid):
    """Uiid 1 coordinator."""

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(uiid=1)

    @property
    def platform_config(self) -> list:
        """Platform config."""
        return [{"platform": PLATFORM.SWITCH}]

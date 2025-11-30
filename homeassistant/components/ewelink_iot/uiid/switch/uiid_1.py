"""UIID 1: single switch device."""

from .switch import SwitchCoordinator


class Uiid1SwitchCoordinator(SwitchCoordinator):
    """For handle uiid 1 data coordinator."""

    def __init__(self, *args, **kwargs) -> None:
        """Init uiid 1 switch coordinator."""
        super().__init__(uiid=1)

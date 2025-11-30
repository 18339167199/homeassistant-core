"""UIID 191: single switch device."""

from .switch import SwitchCoordinator


class Uiid191SwitchCoordinator(SwitchCoordinator):
    """For handle uiid 191 data coordinator."""

    def __init__(self, *args, **kwargs) -> None:
        """Init uiid 191 switch coordinator."""
        super().__init__(uiid=191)

"""Switch coodinator."""

from .switch import (
    MULTIPLE_SINGLE_PROTOCOL_UIIDS,
    OFF,
    ON,
    SINGLE_PROTOCOL_UIIDS,
    SWITCH_UIIDS,
)
from .uiid_1 import Uiid1SwitchCoordinator
from .uiid_191 import Uiid191SwitchCoordinator

uiid_switch_coordinator_map = {191: Uiid191SwitchCoordinator, 1: Uiid1SwitchCoordinator}


def get_switch_coordinator_by_uiid(uiid: int):
    """Get switch coordinator."""
    return uiid_switch_coordinator_map.get(uiid)


__all__ = [
    "MULTIPLE_SINGLE_PROTOCOL_UIIDS",
    "OFF",
    "ON",
    "SINGLE_PROTOCOL_UIIDS",
    "SWITCH_UIIDS",
    "SwitchCoordinator",
    "get_switch_coordinator_by_uiid",
]

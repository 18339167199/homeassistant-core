"""EWeLink device uiid."""

from .uiid import (
    MULTIPLE_SINGLE_PROTOCOL_UIIDS,
    PLATFORM,
    SENSOR_TYPE,
    SINGLE_PROTOCOL_UIIDS,
    SWITCH_STATE,
    SWITCH_UIIDS,
    Uiid,
)
from .uiid_1 import Uiid1
from .uiid_191 import Uiid191
from .uiid_7014 import Uiid7014

uiid_dict = {1: Uiid1, 191: Uiid191, 7014: Uiid7014}
uiid_instance_dict = {}


def get_uiid_instance(uiid):
    """Get device coordinator."""
    stored = uiid_instance_dict.get(uiid)
    if stored is not None:
        return stored
    UiidClass = uiid_dict.get(uiid)
    uiid_instance = UiidClass(uiid) if UiidClass is not None else Uiid(uiid)
    uiid_instance_dict[uiid] = uiid_instance
    return uiid_instance


__all__ = [
    "MULTIPLE_SINGLE_PROTOCOL_UIIDS",
    "PLATFORM",
    "SENSOR_TYPE",
    "SINGLE_PROTOCOL_UIIDS",
    "SWITCH_STATE",
    "SWITCH_UIIDS",
    "get_uiid_instance",
]

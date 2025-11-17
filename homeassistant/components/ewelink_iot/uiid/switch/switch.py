"""Common switch data coordinator."""

from ...utils import deep_get, get_device_uiid
from .uiid_191 import UIID_191

ON = "on"
OFF = "off"


class SwitchCoordinator:
    """EWeLink Switch Coordinator."""

    @staticmethod
    def get_switch_state(device: dict) -> str:
        """Get ewelink switch device switch state."""

        uiid = get_device_uiid(device)
        if uiid in SINGLE_PROTOCOL_UIIDS:
            return deep_get(device, ["itemData", "params", "switch"], OFF)
        if uiid in MULTIPLE_SINGLE_PROTOCOL_UIIDS:
            return deep_get(
                device, ["itemData", "params", "switches", 0, "switch"], OFF
            )
        return None

    def single_protocol_ewelink_state_2_ha():
        """Transform eWeLink device state to ha entity state."""
        return True

    def single_protocol_ha_state_2_ewelink():
        """Transfrom ha entity state to ewelink device state."""
        return True


SINGLE_PROTOCOL_UIIDS = []

MULTIPLE_SINGLE_PROTOCOL_UIIDS = [UIID_191]

SWITCH_UIIDS = [
    *SINGLE_PROTOCOL_UIIDS,
    *MULTIPLE_SINGLE_PROTOCOL_UIIDS,
]

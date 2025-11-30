"""Common switch data coordinator."""

from ..utils import deep_get, get_device_uiid

OFF = "off"
ON = "on"
SINGLE_PROTOCOL_UIIDS = [1]
MULTIPLE_SINGLE_PROTOCOL_UIIDS = [191]
SWITCH_UIIDS = [
    *SINGLE_PROTOCOL_UIIDS,
    *MULTIPLE_SINGLE_PROTOCOL_UIIDS,
]


class SwitchCoordinator:
    """EWeLink Switch Coordinator."""

    def __init__(self, uiid) -> None:
        """Init."""
        self.uiid = uiid

    def get_switch_state(self, device: dict):
        """Get ewelink switch device switch state."""
        uiid = get_device_uiid(device)
        if uiid in SINGLE_PROTOCOL_UIIDS:
            return deep_get(device, ["itemData", "params", "switch"], OFF) == ON
        if uiid in MULTIPLE_SINGLE_PROTOCOL_UIIDS:
            return (
                deep_get(device, ["itemData", "params", "switches", 0, "switch"], OFF)
                == ON
            )
        return False

    def gen_control_switch_params(self, is_on: bool):
        "Gen control switch params."
        target = ON if is_on else OFF
        if self.uiid in MULTIPLE_SINGLE_PROTOCOL_UIIDS:
            return {
                "switches": [
                    {"switch": target if i == 0 else OFF, "outlet": i} for i in range(4)
                ]
            }
        return {"switch": target}

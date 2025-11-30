"""EWeLink device uiid."""

from .switch import SWITCH_UIIDS, get_switch_coordinator_by_uiid

device_coordinator_dict = {}


def get_device_coordinator(uiid):
    """Get device coordinator."""
    stored = device_coordinator_dict.get(uiid)

    if stored is not None:
        return stored

    DeviceCoordinator = None
    device_coordinator = None
    if uiid in SWITCH_UIIDS:
        DeviceCoordinator = get_switch_coordinator_by_uiid(uiid)

    if DeviceCoordinator:
        device_coordinator = DeviceCoordinator(uiid)

    device_coordinator_dict[uiid] = device_coordinator
    return device_coordinator

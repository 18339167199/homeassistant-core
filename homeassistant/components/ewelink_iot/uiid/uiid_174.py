"""UIID 174: single switch device."""

from .uiid import EVENT_ENTITY_TYPE, EVNET_TYPE, PLATFORM, Uiid
from .utils import deep_get


event_type_dict = {
    0: EVNET_TYPE.SINGLE_PRESS,
    1: EVNET_TYPE.DOUBLE_PRESS,
    2: EVNET_TYPE.LONG_PRESS,
}


class Uiid174(Uiid):
    """For handle uiid 174 data coordinator."""

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(uiid=174)

    @property
    def event_types(self) -> list:
        """Support event types."""
        return [
            EVNET_TYPE.SINGLE_PRESS,
            EVNET_TYPE.DOUBLE_PRESS,
            EVNET_TYPE.LONG_PRESS,
        ]

    def key_2_event_type(self, key: int):
        """Key to event type."""
        return event_type_dict.get(key)

    @property
    def platform_config(self) -> list:
        """Platform config."""
        return [
            {
                "platform": PLATFORM.EVENT,
                "type": EVENT_ENTITY_TYPE.BUTTON,
                "config": {
                    "outlet": 0,
                },
            },
            {
                "platform": PLATFORM.EVENT,
                "type": EVENT_ENTITY_TYPE.BUTTON,
                "config": {
                    "outlet": 1,
                },
            },
            {
                "platform": PLATFORM.EVENT,
                "type": EVENT_ENTITY_TYPE.BUTTON,
                "config": {
                    "outlet": 2,
                },
            },
            {
                "platform": PLATFORM.EVENT,
                "type": EVENT_ENTITY_TYPE.BUTTON,
                "config": {
                    "outlet": 3,
                },
            },
            {
                "platform": PLATFORM.EVENT,
                "type": EVENT_ENTITY_TYPE.BUTTON,
                "config": {
                    "outlet": 4,
                },
            },
            {
                "platform": PLATFORM.EVENT,
                "type": EVENT_ENTITY_TYPE.BUTTON,
                "config": {
                    "outlet": 5,
                },
            },
        ]

    def get_outlet_state(self, device):
        """Get outlet state."""
        key = deep_get(device, ["itemData", "params", "key"])
        event_type = event_type_dict.get(key) if type(key) is int else None

        return {
            "outlet": deep_get(device, ["itemData", "params", "outlet"]),
            "event_type": event_type,
        }

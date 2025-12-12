"""Common utils."""

import random
import re
import string
import time
from typing import Any

from .const import RE_EMAIL_PATTREN


def is_valid_email(input: str) -> bool:
    """Valid input is email format."""
    return bool(re.fullmatch(RE_EMAIL_PATTREN, input))


def gen_random_str(length=8, charsets: list | None = None) -> str:
    """Randomly generate a string of several characters, which defaults to numbers and lowercase letters and uppercase letters."""
    if length < 0:
        return ""
    default_charsets = string.digits + string.ascii_lowercase + string.ascii_uppercase
    _charsets = charsets if charsets is list and len(charsets) > 0 else default_charsets
    return "".join(random.choice(_charsets) for _ in range(length))


def gen_config_flow_id(account: str) -> str:
    """Gen config flow unique id."""
    return f"ewelink_lot_{account}"


def deep_get(obj: object, path: list[str | int], default=None) -> Any:
    """Deeply get a value from nested structures (dict, list, tuple, object)."""
    current = obj
    key: Any = None
    for key in path:
        try:
            if isinstance(current, (dict, list, tuple)):
                current = current[key]
            else:
                # Try attribute access for objects
                current = getattr(current, key)
        except (KeyError, IndexError, AttributeError, TypeError):
            return default
    return current


def now_timestamp():
    """Get current timestamp."""
    return int(round(time.time() * 1000))


def get_device_uiid(device: dict) -> int:
    """Get device uiid."""
    return deep_get(device, ["itemData", "extra", "uiid"], None)


def merge(origin_dict: dict[Any, Any], source_dict: dict[Any, Any]) -> dict[Any, Any]:
    """Merge source dict to origin dict."""
    for key, value in source_dict.items():
        if key in origin_dict:
            if isinstance(origin_dict[key], dict) and isinstance(value, dict):
                merge(origin_dict[key], value)
            else:
                origin_dict[key] = value
        else:
            origin_dict[key] = value

    return origin_dict


def gen_event_callback_key(device_id: str, outlet: int, component="event"):
    """Gen event callback key."""
    return f"{component}_{device_id}_{outlet}"

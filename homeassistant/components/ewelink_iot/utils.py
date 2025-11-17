"""Common utils."""

import random
import re
import string
import time

from .const import RE_EMAIL_PATTREN


def is_valid_email(input: str) -> bool:
    """Valid input is email format."""
    return bool(re.fullmatch(RE_EMAIL_PATTREN, input))


def gen_random_str(len=8, charsets: None | list = None) -> str:
    """Randomly generate a string of several characters, which defaults to numbers and lowercase letters and uppercase letters."""
    if len < 0:
        return ""

    default_charsets = string.digits + string.ascii_lowercase + string.ascii_uppercase
    _charsets = charsets if charsets is list and len(charsets) > 0 else default_charsets
    return "".join(random.choice(_charsets) for _ in range(len))


def gen_config_flow_id(account: str) -> str:
    """Gen config flow unique id."""
    return f"ewelink_lot_{account}"


def deep_get(obj: object, path: list[str | int], default=None):
    """Deeply get a value from nested structures (dict, list, tuple, object)."""
    current = obj
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
    return deep_get(device, ["itemData", "extra", "uiid"])

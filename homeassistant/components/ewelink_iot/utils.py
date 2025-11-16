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


def deep_get(data: dict, path: list[str], default=None):
    """Deep get a dict property."""
    current = data
    for key in path:
        if not isinstance(current, dict):
            return default
        if key not in current:
            return default
        current = current[key]
    return current


def now_timestamp():
    """Get current timestamp."""
    return int(round(time.time() * 1000))

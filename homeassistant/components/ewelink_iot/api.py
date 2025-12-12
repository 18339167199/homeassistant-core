"""eWeLink IoT API client."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import hmac
import json
import logging
from typing import Any

import aiohttp

from homeassistant.const import CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import CONF_COUNTRY_CODE, DEV_MODE, EWELINK_API_MAP, REGION_CN, REGIONS_MAP
from .utils import deep_get, gen_random_str, is_valid_email, now_timestamp

_LOGGER = logging.getLogger(__name__)


@dataclass
class EWeLinkDevice:
    """Represent an eWeLink device."""

    device: dict

    @property
    def device_name(self) -> str:
        """Get device name."""
        return deep_get(self.device, ["itemData", "name"], "eWeLink device")

    @property
    def model(self) -> str:
        "Get device model."
        return deep_get(self.device, ["itemData", "params", "model"], None)

    @property
    def brand_name(self) -> str:
        "Get device brand name."
        return deep_get(self.device, ["itemData", "brandName"], "eWeLink")

    @property
    def uiid(self) -> str:
        "Get device uiid."
        return deep_get(self.device, ["itemData", "extra", "uiid"], None)

    @property
    def device_id(self) -> str:
        """Get device id."""
        return deep_get(self.device, ["itemData", "deviceid"])

    @property
    def online(self) -> bool:
        """Get device online status."""
        return deep_get(self.device, ["itemData", "online"], False)

    @property
    def manufacturer(self) -> str:
        """Get device manufacturer."""
        return deep_get(self.device, ["itemData", "extra", "manufacturer"], "ewelink")

    @property
    def apikey(self) -> str:
        """Get device apikey."""
        return deep_get(self.device, ["itemData", "apikey"])


class RequestMethod(StrEnum):
    """Request method of http."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class EWeLinkApiError(Exception):
    """Base exception for eWeLink API errors."""


class EWeLinkAuthError(EWeLinkApiError):
    """Exception raised for authentication errors."""


class EWeLinkAccountNotExist(EWeLinkApiError):
    """Exception raised for eWeLink account not exist."""


class EWeLinkConnectionError(EWeLinkApiError):
    """Exception raised for connection errors."""


class EWeLinkApiClient:
    """eWeLink IoT API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        account: str,
        password: str,
        country_code: str,
        app_id: str,
        app_secret: str,
        user_data=None,
    ) -> None:
        """Initialize the API client."""
        self.__session = session
        self.__account = account
        self.__password = password
        self.__app_id = app_id
        self.__country_code = country_code
        self.__app_id = app_id
        self.__app_secret = app_secret
        self.__at_updated_ts = -1
        self.__api_base_url = self.__get_api_base_url()
        self.__access_token = ""
        self.__family_list = []
        self.__device_dict: dict[str, EWeLinkDevice] = {}
        if user_data is not None:
            self.__user_data = user_data
            self.__access_token = deep_get(user_data, ["at"])
        else:
            self.__user_data = {}
        _LOGGER.info("EWeLinkApiClient init api_url: %s", self.__api_base_url)

    def __get_api_base_url(self):
        """Get eWeLink api base url."""
        if DEV_MODE:
            return EWELINK_API_MAP[REGION_CN]

        regions = [
            item["region"]
            for item in REGIONS_MAP
            if item[CONF_COUNTRY_CODE] == self.__country_code
        ]
        return EWELINK_API_MAP[regions[0]] if len(regions) > 0 else None

    def __generate_auth(
        self, request_method: RequestMethod, params: dict[str, Any] | None = None
    ) -> str:
        """Generate signature for API request."""
        if self.__access_token:
            return f"Bearer {self.__access_token}"

        if params is None:
            return ""

        message = ""
        if request_method == RequestMethod.GET:
            sorted_key_list = sorted(params.keys())
            message = "&".join([f"{key}={params[key]}" for key in sorted_key_list])
        else:
            message = json.dumps(params, separators=(",", ":"))

        sha256 = hmac.new(
            self.__app_secret.encode(), message.encode(), digestmod=hashlib.sha256
        ).digest()

        return f"Sign {(base64.b64encode(sha256)).decode()}"

    def __get_headers(
        self, request_method: RequestMethod, params: dict[str, Any] | None = None
    ) -> dict[str, str]:
        """Get headers for API request."""
        return {
            "X-CK-Appid": self.__app_id,
            "X-CK-Nonce": gen_random_str(8),
            "Authorization": self.__generate_auth(request_method, params),
            "Content-Type": "application/json",
        }

    def __common_error_handler(self, response_json: dict):
        error = response_json.get("error", 0)
        msg = response_json.get("msg", "Unknown error")
        error_msg = f"error: {error}; msg: ${msg}"
        if error == 0:
            return
        if error in (401, 403):
            raise ConfigEntryAuthFailed(
                "Access credentials have expired, please log in again."
            )
        raise EWeLinkApiError(error_msg)

    def set_at_updated_ts(self, ts: int):
        """Set at_updated_ts."""
        self.__at_updated_ts = ts
        return ts

    async def login(self) -> dict[str, Any]:
        """Login to eWeLink and get access token."""
        params = {"countryCode": self.__country_code, CONF_PASSWORD: self.__password}
        if is_valid_email(self.__account):
            params["email"] = self.__account
        else:
            params["phoneNumber"] = f"{self.__country_code}{self.__account}"

        headers = self.__get_headers(RequestMethod.POST, params)

        try:
            async with self.__session.post(
                url=f"{self.__api_base_url}/v2/user/login",
                json=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                data = await response.json()
                error = data.get("error")
                if error != 0:
                    error_msg = data.get("msg")
                    if error == 500:
                        raise EWeLinkApiError("No internet connect")
                    if error == 1003:
                        raise EWeLinkAccountNotExist(
                            f"User account not exist, {error_msg}"
                        )
                    if error in [10001, 10014]:
                        raise EWeLinkAuthError(
                            f"Account or password error, {error_msg}"
                        )
                self.__common_error_handler(data)
                # Extract authentication data
                user_data = data.get("data", {}).get("user", {})
                self.__access_token = data.get("data", {}).get("at")
                self.__app_id = user_data.get("apikey")

                _LOGGER.info("Successfully logged in to eWeLink")
                self.__user_data = data.get("data", {})
                self.set_at_updated_ts(now_timestamp())
                return self.__user_data

        except aiohttp.ClientError as err:
            _LOGGER.error("Error happen 1 %s", err)
            raise EWeLinkConnectionError(f"Connection error: {err}") from err
        except TimeoutError as err:
            _LOGGER.error("Error happen 2 %s", err)
            raise EWeLinkConnectionError("Request timeout") from err

    async def get_family(self):
        """Get user family data."""
        try:
            async with self.__session.get(
                url=f"{self.__api_base_url}/v2/family",
                headers=self.__get_headers(RequestMethod.GET),
                timeout=aiohttp.ClientTimeout(10),
            ) as response:
                data: dict = await response.json()
                self.__common_error_handler(data)
                if data["error"] == 0:
                    family_list = deep_get(data, ["data", "familyList"], [])
                    self.__family_list = [
                        family
                        for family in family_list
                        if family.get("familyType") in [1, 2]
                    ]
                return data
        except aiohttp.ClientError as err:
            _LOGGER.error("Get family aiohttp.ClientError happen: %s", err)
        except TimeoutError as err:
            _LOGGER.error("Get family timeout: %s", err)
        except EWeLinkApiError as err:
            _LOGGER.error("Get family error happen: %s", err)

    async def get_family_device(self, family_id: str):
        """Get all device by family id."""
        try:
            async with self.__session.get(
                url=f"{self.__api_base_url}/v2/device/thing",
                params={"familyid": family_id, "num": 0, "beginIndex": -999999},
                headers=self.__get_headers(RequestMethod.GET),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                data = await response.json()
                self.__common_error_handler(data)
                if data.get("error") == 0:
                    thing_list = deep_get(data, ["data", "thingList"], [])
                    device_list = [
                        item for item in thing_list if item.get("itemType") in [1, 2]
                    ]
                    if len(device_list) > 0:
                        for device in device_list:
                            device_id = deep_get(device, ["itemData", "deviceid"])
                            self.__device_dict[device_id] = EWeLinkDevice(device)
                return data
        except TimeoutError as err:
            raise EWeLinkConnectionError("Request timeout") from err

    async def get_all_devices(self) -> dict[str, EWeLinkDevice]:
        """Get all devices from eWeLink account."""
        await self.get_family()
        if len(self.__family_list) == 0:
            _LOGGER.info("Get_all_devices: family len is 0")
            return {}

        try:
            family_ids = [family.get("id") for family in self.__family_list]
            _LOGGER.info("Get_all_devices: family_ids: %s", json.dumps(family_ids))
            tasks = [self.get_family_device(family_id) for family_id in family_ids]
            await asyncio.gather(*tasks, return_exceptions=True)
        except aiohttp.ClientError as err:
            raise EWeLinkConnectionError(f"Connection error: {err}") from err
        except TimeoutError as err:
            raise EWeLinkConnectionError("Request timeout") from err
        else:
            return self.device_dict

    @property
    def session(self):
        """Get aiohttp session object."""
        return self.__session

    @property
    def api_key(self) -> str:
        """Get api key."""
        return deep_get(self.__user_data, ["user", "apikey"])

    @property
    def app_id(self) -> str | None:
        """Get app id."""
        return self.__app_id

    @property
    def at_updated_ts(self) -> int:
        """Get at_updated_at."""
        return self.__at_updated_ts

    @property
    def access_token(self) -> str:
        """Get at."""
        return deep_get(self.__user_data, ["at"])

    @property
    def refresh_token(self) -> str | None:
        """Get rt."""
        return deep_get(self.__user_data, ["rt"])

    @property
    def api_timezone(self) -> dict | None:
        """Get the time zone returned from the api."""
        return deep_get(self.__user_data, ["user", "timezone"])

    @property
    def account(self) -> str | None:
        """Get user account."""
        return self.__account

    @property
    def device_dict(self) -> dict[str, EWeLinkDevice]:
        """Get device dict."""
        return self.__device_dict

    @property
    def country_code(self) -> str:
        """Get country code."""
        return self.__country_code

    @property
    def logged(self) -> bool:
        """Get is logged."""
        now_ts = now_timestamp()
        has_at = isinstance(self.access_token, str) and len(self.access_token) > 0
        is_at_expired = (
            self.at_updated_ts + (15 * 24 * 60 * 60 * 1000) < now_ts
            if isinstance(self.at_updated_ts, int)
            else False
        )
        return has_at and (not is_at_expired)

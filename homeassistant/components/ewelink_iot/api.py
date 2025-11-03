"""eWeLink IoT API client."""

from __future__ import annotations

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

from .const import DEV_MODE, EWELINK_API_MAP, REGION_CN, REGIONS_MAP
from .utils import deep_get, gen_random_str, is_valid_email

_LOGGER = logging.getLogger(__name__)


@dataclass
class EWeLinkDevice:
    """Represent an eWeLink device."""

    device_id: str
    name: str
    brand_name: str
    product_model: str
    device_type: str
    online: bool
    params: dict[str, Any]
    tags: dict[str, Any]


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
    """Exception rasied for eWeLink account not exist."""


class EWeLinkConnectionError(EWeLinkApiError):
    """Exception raised for connection errors."""


class EWeLinkApiClient:
    """eWeLink IoT API client."""

    _instance: EWeLinkApiClient | None = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Singleton for api client."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        session: aiohttp.ClientSession,
        account: str,
        password: str,
        country_code: str,
        app_id: str,
        app_secret: str,
    ) -> None:
        """Initialize the API client."""
        if not self._initialized:
            self.__session = session
            self.__account = account
            self.__password = password
            self.__app_id = app_id
            self.__country_code = country_code
            self.__app_id = app_id
            self.__app_secret = app_secret
            self.__api_base_url = self.__get_api_base_url()
            self.__access_token = ""
            self.__user_data = {}
            self._initialized = True
            _LOGGER.info("EWeLinkApiClient init api_url: %s", self.__api_base_url)

    def __get_api_base_url(self):
        """Get eWeLink api base url."""
        if DEV_MODE:
            return EWELINK_API_MAP[REGION_CN]

        regions = [
            item["region"]
            for item in REGIONS_MAP
            if item["countryCode"] == self.__country_code
        ]
        return EWELINK_API_MAP[regions[0]] if len(regions) > 0 else None

    def __generate_auth(
        self, request_method: RequestMethod, params: dict[str, Any]
    ) -> str:
        """Generate signature for API request."""
        if self.__access_token:
            return f"Bearer {self.__access_token}"

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
        self, request_method: RequestMethod, params: dict[str, Any]
    ) -> dict[str, str]:
        """Get headers for API request."""

        auth = self.__generate_auth(request_method, params)
        _LOGGER.info("Params is %s, auth is %s", json.dumps(params), auth)

        return {
            "X-CK-Appid": self.__app_id,
            "X-CK-Nonce": gen_random_str(8),
            "Authorization": auth,
            "Content-Type": "application/json",
        }

    async def login(self) -> dict[str, Any]:
        """Login to eWeLink and get access token."""
        params = {"countryCode": self.__country_code, CONF_PASSWORD: self.__password}
        if is_valid_email(self.__account):
            params["email"] = self.__account
        else:
            params["phoneNumber"] = f"{self.__country_code}{self.__account}"

        headers = self.__get_headers(RequestMethod.POST, params)
        _LOGGER.info("Header is %s", json.dumps(headers))

        try:
            async with self.__session.post(
                url=f"{self.__api_base_url}/v2/user/login",
                json=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                data = await response.json()
                _LOGGER.info("Logion response json: %s", json.dumps(data))

                error = data.get("error")
                if error != 0:
                    error_msg = data.get("msg", "Unknown error")
                    if error in (400, 401, 403, 10001, 10014):
                        raise EWeLinkAuthError(f"Authentication failed: {error_msg}")
                    if error == 10003:
                        raise EWeLinkAccountNotExist(
                            f"User account not exist: {error_msg}"
                        )
                    raise EWeLinkApiError(f"Login failed: {error_msg}")

                # Extract authentication data
                user_data = data.get("data", {}).get("user", {})
                self.__access_token = data.get("data", {}).get("at")
                self.__app_id = user_data.get("apikey")

                _LOGGER.info("Successfully logged in to eWeLink")
                self.__user_data = data.get("data", {})
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
            if not self.__access_token:
                await self.login()

            async with self.__session.get(
                url=f"{self.__api_base_url}/v2/family"
            ) as response:
                data: dict = await response.json()
                _LOGGER.info("Get family json %s", json.dumps(data))
                return data
        except aiohttp.ClientError as err:
            _LOGGER.error("Get famility aiohttp.ClientError happen %s", err)
        except TimeoutError as err:
            _LOGGER.error("Get famility timeout %s", err)
        except EWeLinkApiError as err:
            _LOGGER.error(err)

    async def get_devices(self) -> list[EWeLinkDevice]:
        """Get all devices from eWeLink account."""
        if not self.__access_token:
            await self.login()

        url = f"{self.__api_base_url}/device/thing"
        headers = self.__get_headers()

        params = {
            "num": 0,  # 0 means get all devices
        }

        try:
            async with self.__session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                data = await response.json()

                if data.get("error") != 0:
                    error_msg = data.get("msg", "Unknown error")
                    if data.get("error") in (401, 403):
                        # Token might be expired, try to re-login
                        await self.login()
                        return await self.get_devices()
                    raise EWeLinkApiError(f"Failed to get devices: {error_msg}")

                # Parse device list
                device_list = data.get("data", {}).get("thingList", [])
                devices = []

                for device_data in device_list:
                    item_data = device_data.get("itemData", {})
                    device = EWeLinkDevice(
                        device_id=item_data.get("deviceid", ""),
                        name=item_data.get("name", "Unknown"),
                        brand_name=item_data.get("brandName", ""),
                        product_model=item_data.get("productModel", ""),
                        device_type=item_data.get("extra", {}).get("uiid", ""),
                        online=item_data.get("online", False),
                        params=item_data.get("params", {}),
                        tags=item_data.get("tags", {}),
                    )
                    devices.append(device)

                _LOGGER.info("Retrieved %d devices from eWeLink", len(devices))

                return devices

        except aiohttp.ClientError as err:
            raise EWeLinkConnectionError(f"Connection error: {err}") from err
        except TimeoutError as err:
            raise EWeLinkConnectionError("Request timeout") from err

    async def set_device_status(
        self, device_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Set device status."""
        if not self.__access_token:
            await self.login()

        url = f"{self.__api_base_url}/device/thing/status"
        headers = self.__get_headers()

        payload = {
            "type": 1,
            "id": device_id,
            "params": params,
        }

        try:
            async with self.__session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                data = await response.json()

                if data.get("error") != 0:
                    error_msg = data.get("msg", "Unknown error")
                    raise EWeLinkApiError(f"Failed to set device status: {error_msg}")

                return data.get("data", {})

        except aiohttp.ClientError as err:
            raise EWeLinkConnectionError(f"Connection error: {err}") from err
        except TimeoutError as err:
            raise EWeLinkConnectionError("Request timeout") from err

    @classmethod
    def get_instance(cls):
        """Get api client instance."""
        return cls._instance

    @property
    def session(self):
        """Get aiohttp seesion object."""
        return self.__session

    @property
    def api_key(self) -> str | None:
        """Get api key."""
        return deep_get(self.__user_data, ["user", "apikey"])

    @property
    def app_id(self) -> str | None:
        """Get app id."""
        return self.__app_id

    @property
    def access_token(self) -> str | None:
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

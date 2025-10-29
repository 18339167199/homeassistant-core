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
from .utils import gen_random_str, is_valid_email

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
        self._session = session
        self._account = account
        self._password = password
        self._app_id = app_id
        self._app_secret = app_secret
        self._country_code = country_code
        self._api_key = app_id
        self._app_secret = app_secret
        self._api_base_url = self.__get_api_base_url()
        self._access_token: str | None = None
        _LOGGER.info("EWeLinkApiClient init api_url: %s", self._api_base_url)

    def __get_api_base_url(self):
        """Get eWeLink api base url."""
        if DEV_MODE:
            return EWELINK_API_MAP[REGION_CN]

        regions = [
            item["region"]
            for item in REGIONS_MAP
            if item["countryCode"] == self._country_code
        ]
        return EWELINK_API_MAP[regions[0]] if len(regions) > 0 else None

    def __generate_sign(
        self, request_method: RequestMethod, params: dict[str, Any]
    ) -> str:
        """Generate signature for API request."""
        message = ""
        if request_method == RequestMethod.GET:
            key_list = sorted(params.keys())
            for key in key_list:
                if message == "":
                    message += params[key]
                else:
                    message += f"&{params[key]}"
        else:
            message = json.dumps(params)

        sha256 = hmac.new(
            self._api_key.encode(), message.encode(), digestmod=hashlib.sha256
        )
        return f"Sign {(base64.b64encode(sha256.digest())).decode()}"

    def __get_headers(
        self, request_method: RequestMethod, params: dict[str, Any]
    ) -> dict[str, str]:
        """Get headers for API request."""

        return {
            "Content-Type": "application/json; charset=utf-8",
            "X-CK-Appid": self._app_id,
            "X-CK-Nonce": gen_random_str(8),
            "Authorization": self.__generate_sign(
                request_method=request_method, params=params
            ),
        }

    async def login(self) -> dict[str, Any]:
        """Login to eWeLink and get access token."""
        params = {"countryCode": self._country_code, CONF_PASSWORD: self._password}
        if is_valid_email(self._account):
            params["email"] = self._account
        else:
            params["phoneNumber"] = f"{self._country_code}{self._account}"

        _LOGGER.info("Login params: %s", json.dumps(params))

        try:
            async with self._session.post(
                url=f"{self._api_base_url}/v2/user/login",
                json=params,
                headers=self.__get_headers(
                    request_method=RequestMethod.POST, params=params
                ),
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
                self._access_token = data.get("data", {}).get("at")
                self._api_key = user_data.get("apikey")

                _LOGGER.info("Successfully logged in to eWeLink")

                return data.get("data", {})

        except aiohttp.ClientError as err:
            _LOGGER.error("Error happen 1 %s", err)
            raise EWeLinkConnectionError(f"Connection error: {err}") from err
        except TimeoutError as err:
            _LOGGER.error("Error happen 2 %s", err)
            raise EWeLinkConnectionError("Request timeout") from err

    async def get_devices(self) -> list[EWeLinkDevice]:
        """Get all devices from eWeLink account."""
        if not self._access_token:
            await self.login()

        url = f"{self._api_base_url}/device/thing"
        headers = self.__get_headers()

        params = {
            "num": 0,  # 0 means get all devices
        }

        try:
            async with self._session.get(
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
        if not self._access_token:
            await self.login()

        url = f"{self._api_base_url}/device/thing/status"
        headers = self.__get_headers()

        payload = {
            "type": 1,
            "id": device_id,
            "params": params,
        }

        try:
            async with self._session.post(
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

"""eWeLink IoT API client."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import aiohttp

from .const import API_BASE_URL

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


class EWeLinkApiError(Exception):
    """Base exception for eWeLink API errors."""


class EWeLinkAuthError(EWeLinkApiError):
    """Exception raised for authentication errors."""


class EWeLinkConnectionError(EWeLinkApiError):
    """Exception raised for connection errors."""


class EWeLinkApiClient:
    """eWeLink IoT API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        app_id: str,
        app_secret: str,
        region: str = "cn",
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._email = email
        self._password = password
        self._app_id = app_id
        self._app_secret = app_secret
        self._region = region
        self._access_token: str | None = None
        self._user_id: str | None = None
        self._api_key: str | None = None

    def _generate_sign(self, params: dict[str, Any]) -> str:
        """Generate signature for API request."""
        # Sort parameters and create signature string
        sorted_params = sorted(params.items())
        sign_str = ""
        for key, value in sorted_params:
            sign_str += f"{key}={value}&"
        sign_str = sign_str.rstrip("&")

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self._app_secret.encode(),
            sign_str.encode(),
            hashlib.sha256,
        ).hexdigest()

        return signature

    def _get_headers(self, with_auth: bool = True) -> dict[str, str]:
        """Get headers for API request."""
        headers = {
            "Content-Type": "application/json",
            "X-CK-Appid": self._app_id,
        }

        if with_auth and self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        return headers

    async def login(self) -> dict[str, Any]:
        """Login to eWeLink and get access token."""
        url = f"{API_BASE_URL}/user/login"

        # Prepare request parameters
        timestamp = int(time.time() * 1000)
        params = {
            "email": self._email,
            "password": self._password,
            "countryCode": "+86" if self._region == "cn" else "+1",
        }

        headers = self._get_headers(with_auth=False)

        try:
            async with self._session.post(
                url,
                json=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                data = await response.json()

                if data.get("error") != 0:
                    error_msg = data.get("msg", "Unknown error")
                    if data.get("error") in (400, 401, 403):
                        raise EWeLinkAuthError(f"Authentication failed: {error_msg}")
                    raise EWeLinkApiError(f"Login failed: {error_msg}")

                # Extract authentication data
                user_data = data.get("data", {}).get("user", {})
                self._access_token = data.get("data", {}).get("at")
                self._user_id = user_data.get("apikey")
                self._api_key = user_data.get("apikey")

                _LOGGER.debug("Successfully logged in to eWeLink")

                return data.get("data", {})

        except aiohttp.ClientError as err:
            raise EWeLinkConnectionError(f"Connection error: {err}") from err
        except asyncio.TimeoutError as err:
            raise EWeLinkConnectionError("Request timeout") from err

    async def get_devices(self) -> list[EWeLinkDevice]:
        """Get all devices from eWeLink account."""
        if not self._access_token:
            await self.login()

        url = f"{API_BASE_URL}/device/thing"
        headers = self._get_headers()

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

                _LOGGER.debug("Retrieved %d devices from eWeLink", len(devices))

                return devices

        except aiohttp.ClientError as err:
            raise EWeLinkConnectionError(f"Connection error: {err}") from err
        except asyncio.TimeoutError as err:
            raise EWeLinkConnectionError("Request timeout") from err

    async def set_device_status(
        self, device_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Set device status."""
        if not self._access_token:
            await self.login()

        url = f"{API_BASE_URL}/device/thing/status"
        headers = self._get_headers()

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
        except asyncio.TimeoutError as err:
            raise EWeLinkConnectionError("Request timeout") from err

    @property
    def user_id(self) -> str | None:
        """Return user ID."""
        return self._user_id

    @property
    def api_key(self) -> str | None:
        """Return API key."""
        return self._api_key

    @property
    def access_token(self) -> str | None:
        """Return access token."""
        return self._access_token

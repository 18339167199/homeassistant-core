"""eWeLink IoT WebSocket client."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
import json
import logging
from typing import Any
import time

import aiohttp

from .api import EWeLinkApiError
from .const import EWELINK_WS_RESOURCE_CN
from .utils import gen_random_str, now_timestamp

_LOGGER = logging.getLogger(__name__)


class EWeLinkWebSocketClient:
    """eWeLink IoT WebSocket client for real-time updates."""

    _instance: EWeLinkWebSocketClient | None = None

    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Singleton for websocket client."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        app_id: str,
        access_token: str,
        country_code: str,
    ) -> None:
        """Initialize the WebSocket client."""
        if not self._initialized:
            self.__session = session
            self.__api_key = api_key
            self.__app_id = app_id
            self.__access_token = access_token
            self.__country_code = country_code
            self.__ws_base_url = self.__get_ws_base_url()

            self.__ws: aiohttp.ClientWebSocketResponse | None = None
            self.__callbacks: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
            self.__listen_task: asyncio.Task | None = None
            self.__reconnect_task: asyncio.Task | None = None
            self.__is_connected = False
            self.__should_reconnect = True
            self._initialized = True

    def __get_ws_base_url(self):
        """Get ws base url."""
        return EWELINK_WS_RESOURCE_CN

    async def __get_ws_address(self):
        """Get ws connect address."""
        server_url = f"{self.__ws_base_url}/dispatch/app"
        async with self.__session.get(
            url=server_url, timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            data = await response.json()
            error = data.get("error")
            if error != 0:
                raise EWeLinkApiError("Can not get ws connect address")
            return f"wss://{data.get('domain')}/api/ws"

    async def __send_handshake(self) -> None:
        """Send handshake message to authenticate WebSocket connection."""
        handshake_msg = {
            "action": "userOnline",
            "apikey": self.__api_key,
            "appid": self.__app_id,
            "at": self.__access_token,
            "nonce": gen_random_str(),
            "sequence": now_timestamp(),
            "ts": int(round(time.time())),
            "userAgen": "pc_ewelink",
            "version": 8,
        }

        if self.__ws:
            await self.__ws.send_json(handshake_msg)
            _LOGGER.debug("Sent handshake message")

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        if self.__is_connected:
            return

        try:
            _LOGGER.debug("Connecting to eWeLink WebSocket")

            ws_addres = await self.__get_ws_address()
            _LOGGER.info("WS ADDRESS: %s", ws_addres)

            self.__ws = await self.__session.ws_connect(
                url=ws_addres,
                timeout=aiohttp.ClientTimeout(total=60),
            )

            # Send handshake message
            await self.__send_handshake()

            self.__is_connected = True

            # Start listening for messages
            if self.__listen_task is None or self.__listen_task.done():
                self.__listen_task = asyncio.create_task(self.__listen())

            _LOGGER.info("Connected to eWeLink WebSocket")

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Failed to connect to WebSocket: %s", err)
            self.__is_connected = False
            # Schedule reconnection
            if self.__should_reconnect:
                self._schedule_reconnect()

    async def __listen(self) -> None:
        """Listen for WebSocket messages."""
        if not self.__ws:
            return

        try:
            async for msg in self.__ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    _LOGGER.warning("WebSocket connection closed")
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error")
                    break

        except asyncio.CancelledError:
            _LOGGER.debug("WebSocket listen task cancelled")
        except Exception:
            _LOGGER.exception("Error in WebSocket listen")
        finally:
            self.__is_connected = False
            if self.__should_reconnect:
                self._schedule_reconnect()

    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            _LOGGER.debug("Received WebSocket message: %s", data)

            action = data.get("action")

            if action == "update":
                # Device update message
                device_id = data.get("deviceid")
                params = data.get("params", {})

                if device_id and device_id in self.__callbacks:
                    for callback in self.__callbacks[device_id]:
                        callback(params)

        except json.JSONDecodeError:
            _LOGGER.error("Failed to decode WebSocket message: %s", message)
        except Exception:
            _LOGGER.exception("Error handling WebSocket message")

    def register_callback(
        self, device_id: str, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Register a callback for device updates."""
        if device_id not in self.__callbacks:
            self.__callbacks[device_id] = []

        self.__callbacks[device_id].append(callback)
        _LOGGER.debug("Registered callback for device %s", device_id)

    def unregister_callback(
        self, device_id: str, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Unregister a callback for device updates."""
        if device_id in self.__callbacks:
            try:
                self.__callbacks[device_id].remove(callback)
                _LOGGER.debug("Unregistered callback for device %s", device_id)
            except ValueError:
                pass

    def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt."""
        if self.__reconnect_task and not self.__reconnect_task.done():
            return

        async def reconnect() -> None:
            """Reconnect after delay."""
            await asyncio.sleep(10)
            if self.__should_reconnect:
                _LOGGER.info("Attempting to reconnect to WebSocket")
                await self.connect()

        self.__reconnect_task = asyncio.create_task(reconnect())

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        self.__should_reconnect = False
        if self.__listen_task and not self.__listen_task.done():
            self.__listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.__listen_task

        if self.__reconnect_task and not self.__reconnect_task.done():
            self.__reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.__reconnect_task

        if self.__ws and not self.__ws.closed:
            await self.__ws.close()

        self.__is_connected = False
        _LOGGER.info("Disconnected from eWeLink WebSocket")

    @classmethod
    def get_instance(cls):
        """Get websocket client instance."""
        return cls._instance

    @property
    def is_connected(self) -> bool:
        """Return whether WebSocket is connected."""
        return self.__is_connected

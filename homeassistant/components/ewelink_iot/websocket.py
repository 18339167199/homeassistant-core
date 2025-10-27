"""eWeLink IoT WebSocket client."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
import logging
from typing import Any

import aiohttp

from .const import WS_BASE_URL

_LOGGER = logging.getLogger(__name__)


class EWeLinkWebSocketClient:
    """eWeLink IoT WebSocket client for real-time updates."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        access_token: str,
        user_id: str,
    ) -> None:
        """Initialize the WebSocket client."""
        self._session = session
        self._api_key = api_key
        self._access_token = access_token
        self._user_id = user_id
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._callbacks: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self._listen_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._is_connected = False
        self._should_reconnect = True

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        if self._is_connected:
            return

        try:
            _LOGGER.debug("Connecting to eWeLink WebSocket")

            self._ws = await self._session.ws_connect(
                WS_BASE_URL,
                timeout=aiohttp.ClientTimeout(total=30),
            )

            # Send handshake message
            await self._send_handshake()

            self._is_connected = True

            # Start listening for messages
            if self._listen_task is None or self._listen_task.done():
                self._listen_task = asyncio.create_task(self._listen())

            _LOGGER.info("Connected to eWeLink WebSocket")

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to connect to WebSocket: %s", err)
            self._is_connected = False
            # Schedule reconnection
            if self._should_reconnect:
                self._schedule_reconnect()

    async def _send_handshake(self) -> None:
        """Send handshake message to authenticate WebSocket connection."""
        handshake_msg = {
            "action": "userOnline",
            "at": self._access_token,
            "apikey": self._api_key,
            "userAgent": "app",
            "version": 8,
            "nonce": "123456789",
            "sequence": str(int(asyncio.get_event_loop().time() * 1000)),
        }

        if self._ws:
            await self._ws.send_json(handshake_msg)
            _LOGGER.debug("Sent handshake message")

    async def _listen(self) -> None:
        """Listen for WebSocket messages."""
        if not self._ws:
            return

        try:
            async for msg in self._ws:
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
        except Exception as err:
            _LOGGER.exception("Error in WebSocket listen: %s", err)
        finally:
            self._is_connected = False
            if self._should_reconnect:
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

                if device_id and device_id in self._callbacks:
                    for callback in self._callbacks[device_id]:
                        callback(params)

        except json.JSONDecodeError:
            _LOGGER.error("Failed to decode WebSocket message: %s", message)
        except Exception as err:
            _LOGGER.exception("Error handling WebSocket message: %s", err)

    def register_callback(
        self, device_id: str, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Register a callback for device updates."""
        if device_id not in self._callbacks:
            self._callbacks[device_id] = []

        self._callbacks[device_id].append(callback)
        _LOGGER.debug("Registered callback for device %s", device_id)

    def unregister_callback(
        self, device_id: str, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Unregister a callback for device updates."""
        if device_id in self._callbacks:
            try:
                self._callbacks[device_id].remove(callback)
                _LOGGER.debug("Unregistered callback for device %s", device_id)
            except ValueError:
                pass

    def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt."""
        if self._reconnect_task and not self._reconnect_task.done():
            return

        async def reconnect() -> None:
            """Reconnect after delay."""
            await asyncio.sleep(10)
            if self._should_reconnect:
                _LOGGER.info("Attempting to reconnect to WebSocket")
                await self.connect()

        self._reconnect_task = asyncio.create_task(reconnect())

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        self._should_reconnect = False

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self._ws and not self._ws.closed:
            await self._ws.close()

        self._is_connected = False
        _LOGGER.info("Disconnected from eWeLink WebSocket")

    @property
    def is_connected(self) -> bool:
        """Return whether WebSocket is connected."""
        return self._is_connected

"""eWeLink IoT WebSocket client."""

from __future__ import annotations

import asyncio
import json
import logging
import time

import aiohttp

from homeassistant.core import HomeAssistant

from .api import EWeLinkApiError, EWeLinkDevice
from .const import EWELINK_WS_RESOURCE_CN
from .utils import gen_random_str, now_timestamp

_LOGGER = logging.getLogger(__name__)


class EWeLinkWebSocketClient:
    """eWeLink IoT WebSocket client for real-time updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        api_key: str,
        app_id: str,
        access_token: str,
        country_code: str,
    ) -> None:
        """Initialize the WebSocket client."""
        self.__hass = hass
        self.__session = session
        self.__api_key = api_key
        self.__app_id = app_id
        self.__access_token = access_token
        self.__country_code = country_code
        self.__ws_base_url = self.__get_ws_base_url()
        self.__ws = None
        self.__is_connected = False
        self.__reconnect_delay_time = 5
        self.__hass_task = None  # asyncio.Task
        self.__stop_event = asyncio.Event()

        self.__coordinator_handler = {}

    def __get_ws_base_url(self):
        """Get ws base url."""
        return EWELINK_WS_RESOURCE_CN

    def __handle_ws_message(self, ws_message):
        try:
            ws_message_json: dict = json.loads(ws_message)
            action = ws_message_json.get("action")
            if action == "update":
                deviceid = ws_message_json.get("deviceid")
                params = ws_message_json.get("params")
                if (
                    deviceid is not None
                    and params is not None
                    and self.__coordinator_handler is not None
                ):
                    update_entity_state = self.__coordinator_handler.get(
                        "update_entity_state"
                    )
                    if update_entity_state is not None:
                        update_entity_state(deviceid, params)
        except json.JSONDecodeError as err:
            _LOGGER.error(err, "[EWeLink websocket] handle_ws_message error happen")

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

    async def connect_and_reconnect(self) -> None:
        """Connect to WebSocket server."""

        self.__reconnect_delay_time = 5

        while not self.__stop_event.is_set():
            self.__is_connected = False

            try:
                ws_address = await self.__get_ws_address()
                _LOGGER.info("[EWeLink websocket] ws_address: %s", ws_address)

                async with self.__session.ws_connect(
                    ws_address, timeout=aiohttp.ClientTimeout(60), heartbeat=5
                ) as ws:
                    _LOGGER.info("[EWeLink websocket] connect success!")
                    self.__is_connected = True
                    self.__ws = ws
                    await ws.send_json(
                        {
                            "action": "userOnline",
                            "apikey": self.__api_key,
                            "appid": self.__app_id,
                            "at": self.__access_token,
                            "nonce": gen_random_str(8),
                            "sequence": now_timestamp(),
                            "ts": int(round(time.time())),
                            "userAgent": "pc_ewelink",
                            "version": 8,
                        }
                    )

                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            _LOGGER.info(
                                "[EWeLink websocket] message: %s", message.data
                            )
                            self.__handle_ws_message(message.data)

                        elif message.type == aiohttp.WSMsgType.CLOSED:
                            _LOGGER.info("[EWeLink websocket] closed!")
                            break

                        elif message.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.error(
                                ws.exception(), "[EWeLink websocket] error happen"
                            )
                            break

                self.__is_connected = False

            except (aiohttp.WSServerHandshakeError, ConnectionRefusedError) as err:
                _LOGGER.error(err, "[EWeLink websocket] handshake failed")
            except (TimeoutError, aiohttp.ClientError) as err:
                _LOGGER.error(err, "[EWeLink websocket] connect timeout")
            except Exception as err:
                _LOGGER.error(err, "[EWeLink websocket] other error happen")

            if self.__stop_event.is_set():
                _LOGGER.info("[EWeLink websocket] stop event is set")
                break

            _LOGGER.info(
                "[EWeLink websocket] connect lose, will reconnect after %d second",
                self.__reconnect_delay_time,
            )
            await asyncio.sleep(self.__reconnect_delay_time)
            self.__reconnect_delay_time = min(60, self.__reconnect_delay_time + 5)

    async def start(self):
        """Start websocket connect task."""
        self.__hass_task = self.__hass.async_create_background_task(
            self.connect_and_reconnect(), name="ewelink_lot_ws_client"
        )
        return True

    async def stop(self):
        """Stop websocket task."""
        self.__stop_event.set()

        try:
            if self.__hass_task:
                self.__hass_task.cancel()
                await self.__hass_task
        except asyncio.CancelledError:
            pass

        if self.__session:
            await self.__session.close()
            self.__session = None

        return True

    def set_coordinator_handler(self, handler_dict: dict):
        """Set coordinator handler."""
        self.__coordinator_handler = handler_dict

    async def control_device(self, ewelink_device: EWeLinkDevice, params: dict):
        """Control EWeLink device."""
        if (not self.__is_connected) or (ewelink_device is None):
            return

        await self.__ws.send_json(
            {
                "action": "update",
                "apikey": ewelink_device.apikey,
                "deviceid": ewelink_device.device_id,
                "params": params,
                "selfApikey": "",
                "sequence": now_timestamp(),
                "userAgent": "pc_ewelink",
            }
        )

    @property
    def is_connected(self) -> bool:
        """Return whether WebSocket is connected."""
        return self.__is_connected

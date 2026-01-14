"""eWeLink IoT WebSocket client."""

from __future__ import annotations

import asyncio
import json
import logging
import time

import aiohttp

from homeassistant.core import HomeAssistant

from .api import EWeLinkApiError, EWeLinkDevice
from .const import (
    CC,
    CN,
    CONF_COUNTRY_CODE,
    CONF_REGION,
    EWELINK_WS_RESOURCE_CN,
    REGION_CN,
    REGIONS_MAP,
    WS_MSG_ACTION,
    WS_MSG_ACTION_SYSMSG,
    WS_MSG_ACTION_UPDATE,
    WS_MSG_ACTION_USER_ONLINE,
    WS_USER_AGENT,
)
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
        self.__session: aiohttp.ClientSession = session
        self.__api_key = api_key
        self.__app_id = app_id
        self.__access_token = access_token
        self.__country_code = country_code
        self.__ws_base_url = self.__get_ws_base_url()
        self.__ws = None
        self.__is_connected = False
        self.__reconnect_delay_time = 5
        self.__hass_task = None
        self.__stop_event = asyncio.Event()
        self.__coordinator_handler = {}
        self.__pending_responses: dict[str, asyncio.Future] = {}

    def __get_ws_base_url(self):
        """Get ws base url."""
        match_region = [
            x[CONF_REGION]
            for x in REGIONS_MAP
            if x[CONF_COUNTRY_CODE] == self.__country_code
        ]
        if len(match_region) > 0:
            region = match_region[0]
            top_domain = CN if region == REGION_CN else CC
            return f"https://{region}-dispa.coolkit.{top_domain}"
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

    def __handle_ws_message(self, ws_message):
        try:
            ws_message_json: dict = json.loads(ws_message)

            sequence = str(ws_message_json.get("sequence"))
            if sequence and sequence in self.__pending_responses:
                future = self.__pending_responses.pop(sequence)
                if not future.done():
                    future.set_result(ws_message_json)

            action = ws_message_json.get(WS_MSG_ACTION)
            if action == WS_MSG_ACTION_UPDATE:
                deviceid = ws_message_json.get("deviceid")
                params = ws_message_json.get("params")
                if deviceid is not None and params is not None:
                    update_entity_state = self.__coordinator_handler.get(
                        "update_entity_state"
                    )
                    if update_entity_state is not None:
                        update_entity_state(deviceid, params)
            elif action == WS_MSG_ACTION_SYSMSG:
                deviceid = ws_message_json.get("deviceid")
                params = ws_message_json.get("params")
                if deviceid is None or params is None:
                    return
                if "online" in params:
                    update_entity_available = self.__coordinator_handler.get(
                        "update_entity_available"
                    )
                    if update_entity_available is not None:
                        update_entity_available(deviceid, params.get("online"))

        except json.JSONDecodeError as err:
            _LOGGER.error(err, "[EWeLink websocket] handle_ws_message error happen")

    async def connect_and_reconnect(self) -> None:
        """Connect to WebSocket server."""

        self.__reconnect_delay_time = 5

        while not self.__stop_event.is_set():
            self.__is_connected = False

            try:
                ws_address = await self.__get_ws_address()
                _LOGGER.info("[EWeLink websocket] ws_address: %s", ws_address)

                async with self.__session.ws_connect(ws_address, heartbeat=5) as ws:
                    _LOGGER.info("[EWeLink websocket] connect success!")
                    self.__is_connected = True
                    self.__ws = ws
                    await ws.send_json(
                        {
                            "action": WS_MSG_ACTION_USER_ONLINE,
                            "apikey": self.__api_key,
                            "appid": self.__app_id,
                            "at": self.__access_token,
                            "nonce": gen_random_str(8),
                            "sequence": f"{now_timestamp()}",
                            "ts": int(round(time.time())),
                            "userAgent": WS_USER_AGENT,
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

        # if self.__session:
        #     await self.__session.close()

        return True

    def set_coordinator_handler(self, handler_dict: dict):
        """Set coordinator handler."""
        self.__coordinator_handler = handler_dict

    async def control_device(self, ewelink_device: EWeLinkDevice, params: dict):
        """Control EWeLink device."""
        if (not self.__is_connected) or (ewelink_device is None):
            return {"error": -1, "msg": "ws not connect or device is not exist."}

        sequence = f"{now_timestamp()}"
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.__pending_responses[sequence] = future

        command = {
            "action": WS_MSG_ACTION_UPDATE,
            "apikey": ewelink_device.apikey,
            "deviceid": ewelink_device.device_id,
            "params": params,
            "selfApikey": self.__api_key,
            "sequence": sequence,
            "userAgent": WS_USER_AGENT,
        }

        try:
            _LOGGER.info(
                "[EWeLink websocket] control device send: %s", json.dumps(command)
            )
            if self.__ws is not None:
                await self.__ws.send_json(command)
                return await asyncio.wait_for(future, timeout=10)
        except TimeoutError:
            _LOGGER.error(
                "[EWeLink websocket] control device timeout. sequence: %s; deviceid: %s; params: %s",
                sequence,
                ewelink_device.device_id,
                json.dumps(params),
            )
            if sequence in self.__pending_responses:
                self.__pending_responses.pop(sequence)
            return {"error": 408, "sequence": sequence, "msg": "Request Timeout"}
        else:
            return None

    @property
    def is_connected(self) -> bool:
        """Return whether WebSocket is connected."""
        return self.__is_connected

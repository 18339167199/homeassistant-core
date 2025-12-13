"""Data coordinator for eWeLink IoT integration."""

from __future__ import annotations

from datetime import timedelta
import logging
import numbers
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EWeLinkApiClient, EWeLinkApiError, EWeLinkDevice
from .uiid import get_uiid_instance
from .utils import deep_get, gen_event_callback_key, get_device_uiid, merge
from .websocket import EWeLinkWebSocketClient

_LOGGER = logging.getLogger(__name__)


class EWeLinkDataCoordinator(DataUpdateCoordinator[dict[str, EWeLinkDevice]]):
    """Class to manage fetching eWeLink data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: EWeLinkApiClient,
        config_entry: ConfigEntry,
        ws_client: EWeLinkWebSocketClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="eWeLink IoT",
            update_interval=timedelta(minutes=15),
            config_entry=config_entry,
        )
        self.api_client = api_client
        self.ws_client = ws_client
        self.data = {}
        self.event_handler_map: dict[str, Callable] = {}

    def add_event_handler(self, key, handler):
        """Add event entity handler."""
        self.event_handler_map[key] = handler

    def remove_event_handler(self, key):
        """Remove event entity handler."""
        if key in self.event_handler_map:
            self.event_handler_map.pop(key)

    async def _async_update_data(self) -> dict[str, EWeLinkDevice]:
        """Fetch data from API."""
        try:
            self.data = await self.api_client.get_all_devices()
        except EWeLinkApiError as err:
            raise UpdateFailed(f"Error communicating with eWeLink API: {err}") from err
        else:
            return self.data

    async def async_setup(self) -> None:
        """Set up the coordinator, do initial data fetch."""
        await self.async_config_entry_first_refresh()
        self.ws_client.set_coordinator_handler(
            {
                "update_entity_state": self.update_entity_state,
                "update_entity_available": self.update_entity_available,
            }
        )

    def update_entity_state(self, device_id, params):
        """Update entity state."""
        ewelink_device = self.data.get(device_id)
        if ewelink_device is None:
            return

        uiid = get_device_uiid(ewelink_device.device)
        if uiid is None:
            return

        uiid_instance: Any = get_uiid_instance(uiid)
        if (
            uiid_instance
            and hasattr(uiid_instance, "event_types")
            and isinstance(uiid_instance.event_types, list)
            and len(uiid_instance.event_types) > 0
        ):
            outlet: int = deep_get(params, ["outlet"], 0)
            key = deep_get(params, ["key"])
            if isinstance(outlet, numbers.Number) and isinstance(key, numbers.Number):
                handler_key = gen_event_callback_key(device_id, outlet)
                event_handler = self.event_handler_map[handler_key]
                if event_handler is not None:
                    event_handler(outlet, key)

        merge(ewelink_device.device, {"itemData": {"params": params}})
        self.async_set_updated_data(self.data)

    def update_entity_available(self, device_id, online):
        """Update entity available."""
        ewelink_device = self.data.get(device_id)
        if ewelink_device is None:
            return
        merge(ewelink_device.device, {"itemData": {"online": bool(online)}})
        self.async_set_updated_data(self.data)

    async def control_device(self, ewelink_device: EWeLinkDevice, params: dict):
        """Control EWeLink device."""
        result = await self.ws_client.control_device(
            ewelink_device=ewelink_device, params=params
        )
        if result is not None and result.get("error") == 0:
            self.update_entity_state(ewelink_device.device_id, params)
        return result

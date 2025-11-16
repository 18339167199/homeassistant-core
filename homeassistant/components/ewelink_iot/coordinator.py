"""Data coordinator for eWeLink IoT integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EWeLinkApiClient, EWeLinkApiError, EWeLinkDevice
from .websocket import EWeLinkWebSocketClient

_LOGGER = logging.getLogger(__name__)


class EWeLinkDataCoordinator(DataUpdateCoordinator[dict[str, EWeLinkDevice]]):
    """Class to manage fetching eWeLink data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: EWeLinkApiClient,
        ws_client: EWeLinkWebSocketClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="eWeLink IoT",
            update_interval=timedelta(minutes=5),
            config_entry=config_entry,
        )
        self.api_client = api_client
        self.ws_client = ws_client
        self.data = {}
        self._device_callbacks: dict[str, list] = {}

    async def _async_update_data(self) -> dict[str, EWeLinkDevice]:
        """Fetch data from API."""
        try:
            self.data = await self.api_client.get_all_devices()
        except EWeLinkApiError as err:
            raise UpdateFailed(f"Error communicating with eWeLink API: {err}") from err
        else:
            return self.data

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Do initial data fetch
        await self.async_config_entry_first_refresh()

        # Connect to WebSocket for real-time updates
        await self.ws_client.connect()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        # Disconnect WebSocket
        await self.ws_client.disconnect()

    def register_device_callback(self, device_id: str, callback) -> None:
        """Register callback for device updates via WebSocket."""

        def ws_callback(params: dict[str, Any]) -> None:
            """Handle WebSocket update."""
            # Update device data in coordinator
            if device_id in self.data:
                device = self.data[device_id]
                # Update device params
                device.params.update(params)

                # Trigger entity update
                callback()

        self.ws_client.register_callback(device_id, ws_callback)

        # Store for cleanup
        if device_id not in self._device_callbacks:
            self._device_callbacks[device_id] = []
        self._device_callbacks[device_id].append(ws_callback)

    def unregister_device_callback(self, device_id: str) -> None:
        """Unregister callbacks for device."""
        if device_id in self._device_callbacks:
            for callback in self._device_callbacks[device_id]:
                self.ws_client.unregister_callback(device_id, callback)
            del self._device_callbacks[device_id]

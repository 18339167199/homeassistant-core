"""Data coordinator for eWeLink IoT integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EWeLinkApiClient, EWeLinkApiError, EWeLinkDevice

_LOGGER = logging.getLogger(__name__)


class EWeLinkDataCoordinator(DataUpdateCoordinator[dict[str, EWeLinkDevice]]):
    """Class to manage fetching eWeLink data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: EWeLinkApiClient,
        config_entry: ConfigEntry,
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

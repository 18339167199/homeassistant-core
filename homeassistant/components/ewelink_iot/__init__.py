"""The eWeLink IoT integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import EWeLinkApiClient
from .coordinator import EWeLinkDataCoordinator
from .websocket import EWeLinkWebSocketClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]

type EWeLinkConfigEntry = ConfigEntry[EWeLinkDataCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EWeLinkConfigEntry) -> bool:
    """Set up eWeLink IoT from a config entry."""
    api_client = EWeLinkApiClient.get_instance()
    _LOGGER.info(api_client)

    if api_client is None:
        pass

    # Create WebSocket client
    ws_client = EWeLinkWebSocketClient(
        session=api_client.session,
        api_key=api_client.api_key or "",
        access_token=api_client.access_token or "",
        user_id=api_client.account or "",
    )

    # # Create coordinator
    coordinator = EWeLinkDataCoordinator(hass, api_client, ws_client, entry)

    # # Store coordinator in runtime data
    entry.runtime_data = coordinator

    # # Setup coordinator
    await coordinator.async_setup()

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EWeLinkConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Shutdown coordinator
        await entry.runtime_data.async_shutdown()

    return unload_ok

"""The eWeLink IoT integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EWeLinkApiClient, EWeLinkAuthError, EWeLinkConnectionError
from .const import CONF_APP_ID, CONF_APP_SECRET, CONF_REGION, DOMAIN
from .coordinator import EWeLinkDataCoordinator
from .websocket import EWeLinkWebSocketClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]

type EWeLinkConfigEntry = ConfigEntry[EWeLinkDataCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EWeLinkConfigEntry) -> bool:
    """Set up eWeLink IoT from a config entry."""
    session = async_get_clientsession(hass)

    # Create API client
    api_client = EWeLinkApiClient(
        session=session,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        app_id=entry.data[CONF_APP_ID],
        app_secret=entry.data[CONF_APP_SECRET],
        region=entry.data[CONF_REGION],
    )

    # Login to get access token
    try:
        await api_client.login()
    except EWeLinkAuthError as err:
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except EWeLinkConnectionError as err:
        raise ConfigEntryNotReady(f"Connection failed: {err}") from err

    # Create WebSocket client
    ws_client = EWeLinkWebSocketClient(
        session=session,
        api_key=api_client.api_key or "",
        access_token=api_client.access_token or "",
        user_id=api_client.user_id or "",
    )

    # Create coordinator
    coordinator = EWeLinkDataCoordinator(hass, api_client, ws_client, entry)

    # Store coordinator in runtime data
    entry.runtime_data = coordinator

    # Setup coordinator
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

"""The eWeLink IoT integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EWeLinkApiClient
from .const import APP_ID, APP_SECRET, CONF_ACCOUNT, REGION_DEFAULT
from .coordinator import EWeLinkDataCoordinator
from .websocket import EWeLinkWebSocketClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]

type EWeLinkConfigEntry = ConfigEntry[EWeLinkDataCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EWeLinkConfigEntry) -> bool:
    """Set up eWeLink IoT from a config entry."""
    if EWeLinkApiClient.get_instance() is None:
        account = entry.data.get("user_input", {}).get(CONF_ACCOUNT)
        password = entry.data.get("user_input", {}).get(CONF_PASSWORD)
        country_code = entry.data.get("user_input", {}).get(
            "CONF_REGION", REGION_DEFAULT
        )
        user_data = entry.data.get("user_data", None)

        if (not account) or (not password) or (not country_code):
            raise ConfigEntryAuthFailed("Missing credentials, please reconfigure")

        EWeLinkApiClient(
            session=async_get_clientsession(hass),
            account=account,
            password=password,
            country_code=country_code,
            app_id=APP_ID,
            app_secret=APP_SECRET,
            user_data=user_data,
        )

    api_client = EWeLinkApiClient.get_instance()

    # Create WebSocket client
    ws_client = EWeLinkWebSocketClient(
        session=api_client.session,
        api_key=api_client.api_key,
        app_id=APP_ID,
        access_token=api_client.access_token,
        country_code=api_client.country_code,
    )

    # # Create coordinator
    coordinator = EWeLinkDataCoordinator(
        hass=hass, api_client=api_client, ws_client=ws_client, config_entry=entry
    )

    # # Store coordinator in runtime data
    entry.runtime_data = coordinator

    # # Setup coordinator
    await coordinator.async_setup()

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EWeLinkConfigEntry) -> bool:
    """Unload a config entry."""

    # Unload platforms (entities)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = entry.runtime_data

        # Shutdown coordinator (stops polling and cleans up)
        await coordinator.async_shutdown()

        # Close WebSocket connection
        if coordinator.ws_client:
            await coordinator.ws_client.disconnect()

        # Close API client session (if not shared)
        api_client = EWeLinkApiClient.get_instance()
        if api_client and hasattr(api_client, "close"):
            await api_client.close()

        _LOGGER.debug("Successfully unloaded eWeLink IoT integration")

    return unload_ok

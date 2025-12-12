"""The eWeLink IoT integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EWeLinkApiClient
from .const import (
    API_CLIENT,
    APP_ID,
    APP_SECRET,
    CONF_ACCOUNT,
    COORDINATOR,
    DOMAIN,
    EWELINK_API_AT_EXPIRED_TS,
    PLATFORMS,
    REGION_DEFAULT,
    WS_CLIENT,
)
from .coordinator import EWeLinkDataCoordinator
from .utils import now_timestamp
from .websocket import EWeLinkWebSocketClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eWeLink IoT from a config entry."""
    account = entry.data.get("user_input", {}).get(CONF_ACCOUNT)
    password = entry.data.get("user_input", {}).get(CONF_PASSWORD)
    country_code = entry.data.get("user_input", {}).get("CONF_REGION", REGION_DEFAULT)
    user_data = entry.data.get("user_data", None)
    at_updated_ts = entry.data.get("at_updated_ts")
    now_ts = now_timestamp()
    is_at_expired = (
        at_updated_ts + EWELINK_API_AT_EXPIRED_TS < now_ts
        if isinstance(at_updated_ts, int)
        else False
    )

    if (not account) or (not password) or (not country_code) or is_at_expired:
        raise ConfigEntryAuthFailed("Missing credentials, please reconfigure")

    # Create api client
    api_client = EWeLinkApiClient(
        session=async_get_clientsession(hass),
        account=account,
        password=password,
        country_code=country_code,
        app_id=APP_ID,
        app_secret=APP_SECRET,
        user_data=user_data,
    )

    # Create WebSocket client
    ws_client = EWeLinkWebSocketClient(
        hass=hass,
        session=api_client.session,
        api_key=api_client.api_key,
        app_id=APP_ID,
        access_token=api_client.access_token,
        country_code=api_client.country_code,
    )
    await ws_client.start()
    entry.async_on_unload(ws_client.stop)  # type: ignore  # noqa: PGH003

    # Create coordinator
    coordinator = EWeLinkDataCoordinator(
        hass=hass, api_client=api_client, config_entry=entry, ws_client=ws_client
    )

    runtime_data = {
        WS_CLIENT: ws_client,
        API_CLIENT: api_client,
        COORDINATOR: coordinator,
    }

    # Setup coordinator
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime_data

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("EWeLink lot integration load over ===================>")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Unload platforms (entities)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        runtime_data = hass.data[DOMAIN].pop(entry.entry_id)
        # Shutdown coordinator (stops polling and cleans up)
        if COORDINATOR in runtime_data:
            await runtime_data[COORDINATOR].async_shutdown()
        if WS_CLIENT in runtime_data:
            await runtime_data[WS_CLIENT].stop()

        _LOGGER.debug("Successfully unloaded eWeLink IoT integration")

    return unload_ok

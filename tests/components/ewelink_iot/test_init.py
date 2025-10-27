"""Tests for eWeLink IoT init."""

from unittest.mock import AsyncMock

from homeassistant.components.ewelink_iot.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_setup_unload(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client,
    mock_ws_client,
) -> None:
    """Test setup and unload."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert DOMAIN in hass.data

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED

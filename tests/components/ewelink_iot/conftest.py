"""Tests for eWeLink IoT integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.ewelink_iot.const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="test@example.com",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
            "app_id": "test_app_id",
            "app_secret": "test_app_secret",
            "region": "cn",
        },
        unique_id="test@example.com",
    )


@pytest.fixture
def mock_api_client():
    """Return a mocked API client."""
    with patch(
        "homeassistant.components.ewelink_iot.api.EWeLinkApiClient", autospec=True
    ) as mock_client:
        client = mock_client.return_value
        client.login = AsyncMock(return_value={"user": {"apikey": "test_key"}})
        client.get_devices = AsyncMock(return_value=[])
        client.user_id = "test_user_id"
        client.api_key = "test_api_key"
        client.access_token = "test_access_token"
        yield client


@pytest.fixture
def mock_ws_client():
    """Return a mocked WebSocket client."""
    with patch(
        "homeassistant.components.ewelink_iot.websocket.EWeLinkWebSocketClient",
        autospec=True,
    ) as mock_ws:
        ws = mock_ws.return_value
        ws.connect = AsyncMock()
        ws.disconnect = AsyncMock()
        ws.is_connected = True
        yield ws

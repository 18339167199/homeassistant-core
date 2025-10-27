"""Config flow for eWeLink IoT integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EWeLinkApiClient, EWeLinkAuthError, EWeLinkConnectionError
from .const import (
    CONF_APP_ID,
    CONF_APP_SECRET,
    CONF_REGION,
    DEFAULT_APP_ID,
    DEFAULT_APP_SECRET,
    DEFAULT_REGION,
    DOMAIN,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)


class EWeLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for eWeLink IoT."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Create API client and test login
                session = async_get_clientsession(self.hass)
                api_client = EWeLinkApiClient(
                    session=session,
                    email=user_input[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                    app_id=user_input.get(CONF_APP_ID, DEFAULT_APP_ID),
                    app_secret=user_input.get(CONF_APP_SECRET, DEFAULT_APP_SECRET),
                    region=user_input.get(CONF_REGION, DEFAULT_REGION),
                )

                # Attempt to login
                user_data = await api_client.login()

                # Use user email as unique ID
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()

                # Create config entry
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_APP_ID: user_input.get(CONF_APP_ID, DEFAULT_APP_ID),
                        CONF_APP_SECRET: user_input.get(
                            CONF_APP_SECRET, DEFAULT_APP_SECRET
                        ),
                        CONF_REGION: user_input.get(CONF_REGION, DEFAULT_REGION),
                    },
                )

            except EWeLinkAuthError:
                errors["base"] = "invalid_auth"
            except EWeLinkConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_REGION, default=DEFAULT_REGION): vol.In(REGIONS),
                vol.Optional(CONF_APP_ID, default=DEFAULT_APP_ID): str,
                vol.Optional(CONF_APP_SECRET, default=DEFAULT_APP_SECRET): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauth flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                # Test new credentials
                session = async_get_clientsession(self.hass)
                api_client = EWeLinkApiClient(
                    session=session,
                    email=reauth_entry.data[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                    app_id=reauth_entry.data.get(CONF_APP_ID, DEFAULT_APP_ID),
                    app_secret=reauth_entry.data.get(
                        CONF_APP_SECRET, DEFAULT_APP_SECRET
                    ),
                    region=reauth_entry.data.get(CONF_REGION, DEFAULT_REGION),
                )

                await api_client.login()

                # Update config entry
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )

            except EWeLinkAuthError:
                errors["base"] = "invalid_auth"
            except EWeLinkConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"email": reauth_entry.data[CONF_EMAIL]},
        )

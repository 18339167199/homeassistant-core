"""Config flow for eWeLink IoT integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    EWeLinkAccountNotExist,
    EWeLinkApiClient,
    EWeLinkAuthError,
    EWeLinkConnectionError,
)
from .const import (
    APP_ID,
    APP_SECRET,
    CONF_ACCOUNT,
    CONF_COUNTRY_CODE,
    CONF_REGION,
    DEV_MODE,
    DOMAIN,
    REGION_DEFAULT,
    REGIONS_MAP,
)
from .utils import gen_config_flow_id, now_timestamp

_LOGGER = logging.getLogger(__name__)


class EWeLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for eWeLink IoT."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        _LOGGER.info("DEV_MODE: %s", DEV_MODE)

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Create API client and test login
                session = async_get_clientsession(self.hass)

                api_client = EWeLinkApiClient(
                    session=session,
                    account=user_input[CONF_ACCOUNT],
                    password=user_input[CONF_PASSWORD],
                    country_code=user_input[CONF_REGION],
                    app_id=APP_ID,
                    app_secret=APP_SECRET,
                )

                # Attempt to login
                user_data = await api_client.login()

                # Use user account as unique ID
                await self.async_set_unique_id(
                    gen_config_flow_id(user_input[CONF_ACCOUNT].lower())
                )

                # If the unique ID has been configured, the current config flow is discarded to prevent configuration reset.
                self._abort_if_unique_id_configured()

                api_client = None

                # Create config entry
                return self.async_create_entry(
                    title=user_input[CONF_ACCOUNT],
                    data={
                        "user_input": user_input,
                        "user_data": user_data,
                        "at_updated_ts": now_timestamp(),
                    },
                )

            except EWeLinkAccountNotExist:
                errors["base"] = "user_not_exist"
            except EWeLinkAuthError:
                errors["base"] = "invalid_auth"
            except EWeLinkConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"

        # format region map to options
        regions_options = {
            item[CONF_COUNTRY_CODE]: item[CONF_COUNTRY_CODE] for item in REGIONS_MAP
        }

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_REGION, default=REGION_DEFAULT): vol.In(
                    regions_options.keys()
                ),
                vol.Required(CONF_ACCOUNT): str,
                vol.Required(CONF_PASSWORD): str,
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
                session = async_get_clientsession(self.hass)
                account = reauth_entry.data.get("user_input", {}).get(CONF_ACCOUNT)
                country_code = reauth_entry.data.get("user_input", {}).get(
                    CONF_REGION, REGION_DEFAULT
                )
                api_client = EWeLinkApiClient(
                    session=session,
                    account=account,
                    password=user_input[CONF_PASSWORD],
                    country_code=country_code,
                    app_id=APP_ID,
                    app_secret=APP_SECRET,
                )

                # re login with user account
                user_data = await api_client.login()

                old_user_input: dict[str, Any] = reauth_entry.data.get("user_input", {})
                new_user_input = {
                    CONF_ACCOUNT: old_user_input.get(CONF_ACCOUNT),
                    CONF_REGION: old_user_input.get(CONF_REGION),
                    CONF_PASSWORD: user_input.get(CONF_PASSWORD),
                }
                # Update config entry
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        "user_input": new_user_input,
                        "user_data": user_data,
                        "at_updated_ts": now_timestamp(),
                    },
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
            description_placeholders={
                "account": reauth_entry.data.get("user_input", {}).get(CONF_ACCOUNT)
            },
        )

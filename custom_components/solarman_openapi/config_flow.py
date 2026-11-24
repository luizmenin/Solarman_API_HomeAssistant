"""Config flow for SOLARMAN OpenAPI."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolarmanAuthError, SolarmanClient, SolarmanError, hash_password
from .const import (
    CONF_APP_ID,
    CONF_APP_SECRET,
    CONF_DEVICE_SN,
    CONF_EMAIL,
    CONF_ORG_ID,
    CONF_PASSWORD_HASH,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_REGION, default=defaults.get(CONF_REGION, DEFAULT_REGION)): vol.In(list(REGIONS)),
            vol.Required(CONF_APP_ID, default=defaults.get(CONF_APP_ID, "")): str,
            vol.Required(CONF_APP_SECRET, default=defaults.get(CONF_APP_SECRET, "")): str,
            vol.Required(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): str,
            vol.Required("password"): str,
            vol.Required(CONF_DEVICE_SN, default=defaults.get(CONF_DEVICE_SN, "")): str,
            vol.Optional(CONF_ORG_ID): vol.Coerce(int),
        }
    )


class SolarmanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SolarmanOptionsFlow()

    async def _validate(self, user_input: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        data = {
            CONF_REGION: user_input[CONF_REGION],
            CONF_APP_ID: user_input[CONF_APP_ID].strip(),
            CONF_APP_SECRET: user_input[CONF_APP_SECRET].strip(),
            CONF_EMAIL: user_input[CONF_EMAIL].strip(),
            CONF_PASSWORD_HASH: hash_password(user_input["password"]),
            CONF_DEVICE_SN: user_input[CONF_DEVICE_SN].strip(),
        }
        if user_input.get(CONF_ORG_ID):
            data[CONF_ORG_ID] = user_input[CONF_ORG_ID]
        client = SolarmanClient(
            async_get_clientsession(self.hass),
            REGIONS[data[CONF_REGION]],
            data[CONF_APP_ID],
            data[CONF_APP_SECRET],
            data[CONF_EMAIL],
            data[CONF_PASSWORD_HASH],
            data.get(CONF_ORG_ID),
        )
        try:
            points = await client.async_get_current_data(data[CONF_DEVICE_SN])
        except SolarmanAuthError:
            return data, "invalid_auth"
        except SolarmanError:
            return data, "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error")
            return data, "unknown"
        if not points:
            return data, "no_data"
        return data, None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_SN].strip())
            self._abort_if_unique_id_configured()
            data, error = await self._validate(user_input)
            if error is None:
                return self.async_create_entry(title=f"SOLARMAN {data[CONF_DEVICE_SN]}", data=data)
            errors["base"] = error
        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input or {}), errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._reauth_entry
        if user_input is not None:
            merged = {**entry.data, CONF_APP_SECRET: user_input[CONF_APP_SECRET], "password": user_input["password"]}
            data, error = await self._validate(merged)
            if error is None:
                return self.async_update_reload_and_abort(entry, data={**entry.data, **data})
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_APP_SECRET): str, vol.Required("password"): str}
            ),
            errors=errors,
        )


class SolarmanOptionsFlow(OptionsFlow):
    """Polling interval option."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=60))}
            ),
        )

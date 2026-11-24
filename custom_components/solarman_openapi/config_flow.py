"""Config flow for SOLARMAN OpenAPI (one entry per logger)."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import SolarmanAuthError, SolarmanClient, SolarmanError, hash_password
from .const import (
    CONF_APP_ID,
    CONF_APP_SECRET,
    CONF_DAILY_KEY,
    CONF_EMAIL,
    CONF_INVERTER_SNS,
    CONF_INVERTERS,
    CONF_LOGGER_SN,
    CONF_ORG_ID,
    CONF_PASSWORD_HASH,
    CONF_POWER_KEY,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_SELECTED,
    CONF_TOTAL_KEY,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHARE,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    REGIONS,
)
from .helpers import parse_sns

_LOGGER = logging.getLogger(__name__)

HELP_URL = "https://helpcenter.solarmanpv.com"


def _select_schema_field(sns: list[str]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=sns, multiple=True, mode=SelectSelectorMode.LIST)
    )


def _shares_schema(sns: list[str], current: dict[str, float]) -> vol.Schema:
    """One 0-100 % field per inverter, keyed by the inverter SN."""
    selector = NumberSelector(
        NumberSelectorConfig(
            min=0, max=100, step=1, unit_of_measurement="%", mode=NumberSelectorMode.BOX
        )
    )
    return vol.Schema(
        {vol.Required(sn, default=current.get(sn, DEFAULT_SHARE)): selector for sn in sns}
    )


class SolarmanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._client: SolarmanClient | None = None
        self._candidates: list[str] = []
        self._selected: list[str] = []
        self._reauth_entry = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SolarmanOptionsFlow()

    def _make_client(self) -> SolarmanClient:
        d = self._data
        return SolarmanClient(
            async_get_clientsession(self.hass),
            REGIONS[d[CONF_REGION]],
            d[CONF_APP_ID],
            d[CONF_APP_SECRET],
            d[CONF_EMAIL],
            d[CONF_PASSWORD_HASH],
            d.get(CONF_ORG_ID),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            logger_sn = user_input[CONF_LOGGER_SN].strip()
            await self.async_set_unique_id(logger_sn)
            self._abort_if_unique_id_configured()
            self._data = {
                CONF_REGION: user_input[CONF_REGION],
                CONF_APP_ID: user_input[CONF_APP_ID].strip(),
                CONF_APP_SECRET: user_input[CONF_APP_SECRET].strip(),
                CONF_EMAIL: user_input[CONF_EMAIL].strip(),
                CONF_PASSWORD_HASH: hash_password(user_input["password"]),
                CONF_LOGGER_SN: logger_sn,
            }
            if user_input.get(CONF_ORG_ID):
                self._data[CONF_ORG_ID] = user_input[CONF_ORG_ID]
            self._client = self._make_client()
            try:
                await self._client.async_authenticate()
            except SolarmanAuthError:
                errors["base"] = "invalid_auth"
            except SolarmanError:
                errors["base"] = "cannot_connect"
            else:
                self._candidates = parse_sns(user_input.get(CONF_INVERTER_SNS))
                if not self._candidates:
                    self._candidates = await self._client.async_discover_inverters(logger_sn)
                if self._candidates:
                    return await self.async_step_select()
                errors["base"] = "no_inverters"

        d = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(CONF_REGION, default=d.get(CONF_REGION, DEFAULT_REGION)): vol.In(list(REGIONS)),
                vol.Required(CONF_APP_ID, default=d.get(CONF_APP_ID, "")): str,
                vol.Required(CONF_APP_SECRET, default=d.get(CONF_APP_SECRET, "")): str,
                vol.Required(CONF_EMAIL, default=d.get(CONF_EMAIL, "")): str,
                vol.Required("password"): str,
                vol.Required(CONF_LOGGER_SN, default=d.get(CONF_LOGGER_SN, "")): str,
                vol.Optional(CONF_INVERTER_SNS, default=d.get(CONF_INVERTER_SNS, "")): str,
                vol.Optional(CONF_ORG_ID): vol.Coerce(int),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"help_url": HELP_URL},
        )

    async def async_step_select(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose which inverters of the logger to import."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_SELECTED]:
                self._selected = user_input[CONF_SELECTED]
                return await self.async_step_shares()
            errors["base"] = "none_selected"
        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema(
                {vol.Required(CONF_SELECTED, default=self._candidates): _select_schema_field(self._candidates)}
            ),
            errors=errors,
        )

    async def async_step_shares(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Set the participation percentage of each selected inverter."""
        errors: dict[str, str] = {}
        if user_input is not None:
            assert self._client
            for sn in self._selected:
                try:
                    points = await self._client.async_get_current_data(sn)
                except SolarmanAuthError:
                    errors["base"] = "invalid_auth"
                    break
                except SolarmanError:
                    points = {}
                if not points:
                    errors["base"] = "no_data"
                    break
            if not errors:
                shares = {sn: float(user_input[sn]) for sn in self._selected}
                return self.async_create_entry(
                    title=f"SOLARMAN {self._data[CONF_LOGGER_SN]}",
                    data=self._data,
                    options={CONF_INVERTERS: shares},
                )
        return self.async_show_form(
            step_id="shares",
            data_schema=_shares_schema(self._selected, {}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._reauth_entry
        if user_input is not None:
            self._data = {
                **entry.data,
                CONF_APP_SECRET: user_input[CONF_APP_SECRET].strip(),
                CONF_PASSWORD_HASH: hash_password(user_input["password"]),
            }
            try:
                await self._make_client().async_authenticate()
            except SolarmanAuthError:
                errors["base"] = "invalid_auth"
            except SolarmanError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(entry, data=self._data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_APP_SECRET): str, vol.Required("password"): str}
            ),
            errors=errors,
        )


class SolarmanOptionsFlow(OptionsFlow):
    """Change inverters, participation % and aggregate keys after setup."""

    def __init__(self) -> None:
        self._pending: dict[str, Any] = {}
        self._selected: list[str] = []

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        opts = self.config_entry.options
        current: dict[str, float] = opts.get(CONF_INVERTERS, {})
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = list(dict.fromkeys(user_input[CONF_SELECTED] + parse_sns(user_input.get(CONF_INVERTER_SNS))))
            if selected:
                self._selected = selected
                self._pending = {
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_POWER_KEY: user_input.get(CONF_POWER_KEY, "").strip(),
                    CONF_DAILY_KEY: user_input.get(CONF_DAILY_KEY, "").strip(),
                    CONF_TOTAL_KEY: user_input.get(CONF_TOTAL_KEY, "").strip(),
                }
                return await self.async_step_shares()
            errors["base"] = "none_selected"

        known = list(current)
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=60)
                ),
                vol.Required(CONF_SELECTED, default=known): _select_schema_field(known),
                vol.Optional(CONF_INVERTER_SNS, default=""): str,
                vol.Optional(CONF_POWER_KEY, default=opts.get(CONF_POWER_KEY, "")): str,
                vol.Optional(CONF_DAILY_KEY, default=opts.get(CONF_DAILY_KEY, "")): str,
                vol.Optional(CONF_TOTAL_KEY, default=opts.get(CONF_TOTAL_KEY, "")): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def async_step_shares(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            shares = {sn: float(user_input[sn]) for sn in self._selected}
            return self.async_create_entry(data={**self._pending, CONF_INVERTERS: shares})
        return self.async_show_form(
            step_id="shares",
            data_schema=_shares_schema(self._selected, self.config_entry.options.get(CONF_INVERTERS, {})),
        )

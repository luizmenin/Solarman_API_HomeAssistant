"""Data update coordinator for one logger and its selected inverters."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SolarmanAuthError, SolarmanClient, SolarmanError
from .const import (
    CONF_INVERTERS,
    CONF_LOGGER_SN,
    CONF_SCAN_INTERVAL,
    DEFAULT_KEYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    KIND_POWER,
    OPTION_FOR_KIND,
)
from .helpers import to_number

_LOGGER = logging.getLogger(__name__)

# {inverter_sn: {data_key: item}}; None when that inverter failed this cycle.
type InverterData = dict[str, dict[str, dict[str, Any]] | None]


class SolarmanCoordinator(DataUpdateCoordinator[InverterData]):
    """Poll real-time data for every selected inverter of a logger."""

    def __init__(self, hass, entry: ConfigEntry, client: SolarmanClient) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.data[CONF_LOGGER_SN]}",
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.logger_sn: str = entry.data[CONF_LOGGER_SN]
        self.options = entry.options
        # participation percentage per inverter
        self.shares: dict[str, float] = {
            sn: float(pct)
            for sn, pct in (entry.options.get(CONF_INVERTERS) or {}).items()
        }

    async def _async_update_data(self) -> InverterData:
        results = await asyncio.gather(
            *(self.client.async_get_current_data(sn) for sn in self.shares),
            return_exceptions=True,
        )
        data: InverterData = {}
        for sn, result in zip(self.shares, results, strict=True):
            if isinstance(result, SolarmanAuthError):
                raise ConfigEntryAuthFailed(str(result)) from result
            if isinstance(result, BaseException):
                _LOGGER.warning("Inverter %s update failed: %s", sn, result)
                data[sn] = None
            else:
                data[sn] = result
        if self.shares and all(v is None for v in data.values()):
            raise UpdateFailed("No inverter returned data")
        return data

    def resolve_key(self, sn: str, kind: str) -> str | None:
        """Pick the data key used for an aggregate kind on one inverter."""
        points = (self.data or {}).get(sn) or {}
        configured = self.options.get(OPTION_FOR_KIND[kind])
        for key in [configured] if configured else DEFAULT_KEYS[kind]:
            if key in points:
                return key
        return None

    def weighted_total(self, kind: str) -> tuple[float | None, dict[str, float]]:
        """Sum of (value * participation%) over the selected inverters.

        Returns (total, per-inverter contribution). The total is None unless
        every selected inverter reported a value, so a partial outage cannot
        make an energy counter drop (which HA would read as a meter reset).
        """
        total = 0.0
        contributions: dict[str, float] = {}
        for sn, pct in self.shares.items():
            points = (self.data or {}).get(sn)
            key = self.resolve_key(sn, kind)
            if not points or key is None:
                return None, {}
            item = points[key]
            value = to_number(item.get("value"))
            if value is None:
                return None, {}
            unit = item.get("unit")
            if kind == KIND_POWER and unit == "kW":
                value *= 1000
            elif kind != KIND_POWER and unit == "Wh":
                value /= 1000
            contribution = value * pct / 100
            contributions[sn] = round(contribution, 3)
            total += contribution
        return round(total, 3), contributions

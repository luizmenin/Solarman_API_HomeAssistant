"""Data update coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SolarmanAuthError, SolarmanClient, SolarmanError
from .const import CONF_DEVICE_SN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SolarmanCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll real-time data for one device."""

    def __init__(
        self, hass, entry: ConfigEntry, client: SolarmanClient
    ) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.data[CONF_DEVICE_SN]}",
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.device_sn: str = entry.data[CONF_DEVICE_SN]

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_current_data(self.device_sn)
        except SolarmanAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SolarmanError as err:
            raise UpdateFailed(str(err)) from err

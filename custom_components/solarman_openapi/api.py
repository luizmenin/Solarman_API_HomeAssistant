"""Minimal async client for the SOLARMAN OpenAPI."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Margin before token expiry at which we fetch a new one.
_TOKEN_MARGIN = 300


class SolarmanError(Exception):
    """Generic API error."""


class SolarmanAuthError(SolarmanError):
    """Authentication failed."""


def hash_password(password: str) -> str:
    """Return the lowercase SHA-256 hex digest the API expects."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class SolarmanClient:
    """Client for token handling and real-time device data."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        app_id: str,
        app_secret: str,
        email: str,
        password_hash: str,
        org_id: int | None = None,
    ) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._app_id = app_id
        self._app_secret = app_secret
        self._email = email
        self._password_hash = password_hash
        self._org_id = org_id
        self._token: str | None = None
        self._token_expires = 0.0
        self._lock = asyncio.Lock()

    async def _post(
        self,
        path: str,
        params: dict[str, str],
        body: dict[str, Any],
        token: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            async with self._session.post(
                f"{self._base}{path}",
                params=params,
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json(content_type=None)
                if resp.status in (401, 403):
                    raise SolarmanAuthError(f"HTTP {resp.status}")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SolarmanError(f"Communication error: {err}") from err
        if not isinstance(data, dict):
            raise SolarmanError("Unexpected response from API")
        return data

    async def async_authenticate(self) -> None:
        """Fetch a new access token."""
        body: dict[str, Any] = {
            "appSecret": self._app_secret,
            "email": self._email,
            "password": self._password_hash,
        }
        if self._org_id:
            body["orgId"] = self._org_id
        data = await self._post(
            "/account/v1.0/token",
            {"appId": self._app_id, "language": "en"},
            body,
        )
        token = data.get("access_token")
        if not data.get("success") or not token:
            raise SolarmanAuthError(data.get("msg") or "Token request rejected")
        self._token = token
        self._token_expires = time.monotonic() + int(data.get("expires_in", 3600))

    async def _ensure_token(self) -> str:
        async with self._lock:
            if not self._token or time.monotonic() > self._token_expires - _TOKEN_MARGIN:
                await self.async_authenticate()
            assert self._token
            return self._token

    async def async_discover_inverters(self, logger_sn: str) -> list[str]:
        """Best-effort: list inverter SNs of the account, filtered by logger.

        Uses /station/v1.0/list and /station/v1.0/device. The response shape is
        not covered by the public docs we could verify, so any failure simply
        returns an empty list and the user types the inverter SNs manually.
        """
        found: dict[str, bool] = {}  # sn -> matches the logger
        any_collector_field = False
        try:
            token = await self._ensure_token()
            stations = await self._post(
                "/station/v1.0/list", {"language": "en"}, {"page": 1, "size": 50}, token
            )
            for station in stations.get("stationList") or []:
                devices = await self._post(
                    "/station/v1.0/device",
                    {"language": "en"},
                    {"stationId": station.get("id"), "page": 1, "size": 100},
                    token,
                )
                items = devices.get("deviceListItems") or devices.get("deviceList") or []
                for item in items:
                    if str(item.get("deviceType", "")).upper() != "INVERTER":
                        continue
                    sn = item.get("deviceSn")
                    if not sn:
                        continue
                    collector = item.get("collectorSn")
                    any_collector_field |= collector is not None
                    found[sn] = collector is None or str(collector) == logger_sn
        except SolarmanError as err:
            _LOGGER.debug("Inverter discovery failed: %s", err)
            return []
        if any_collector_field:
            matched = [sn for sn, ok in found.items() if ok]
            if matched:
                return matched
        return list(found)

    async def _current_data(self, device_sn: str, key: str) -> dict[str, Any]:
        return await self._post(
            "/device/v1.0/currentData",
            {"language": "en"},
            {key: device_sn},
            await self._ensure_token(),
        )

    async def async_get_current_data(self, device_sn: str) -> dict[str, Any]:
        """Return {data key: item} for the device's real-time data points."""
        try:
            data = await self._current_data(device_sn, "deviceSn")
            # Docs are inconsistent about the parameter spelling.
            if str(data.get("code")) == "2101006":
                data = await self._current_data(device_sn, "deviceSN")
        except SolarmanAuthError:
            self._token = None
            data = await self._current_data(device_sn, "deviceSn")

        if not data.get("success", False) and not data.get("dataList"):
            msg = data.get("msg") or f"code {data.get('code')}"
            if "token" in str(msg).lower() or "auth" in str(msg).lower():
                self._token = None
                raise SolarmanAuthError(msg)
            raise SolarmanError(msg)

        return {
            item["key"]: item
            for item in data.get("dataList", [])
            if isinstance(item, dict) and item.get("key")
        }

"""FreshTomato HTTP API client.

FreshTomato uses HTTP Basic Auth and a session-based `_http_id` token.
Data is retrieved via two endpoints:

  /update.cgi?exec=netdev&_http_id=<id>
      Returns a JavaScript-style object with per-interface TX/RX counters.

  /update.cgi?exec=wldev&_http_id=<id>
      Returns a JavaScript-style list of connected wireless clients.

  /status-data.jsx
      Returns a JSONP-like blob with general router status (uptime, WAN IP,
      CPU load, memory, firmware version, etc.).

All responses use HTTP Basic Authentication (username / password).
The _http_id value is a random token embedded in the router UI source; the
user must look it up once in the router admin page source (search for
http_id) and enter it during integration setup.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aiohttp

from .const import (
    DEFAULT_VERIFY_SSL,
    ENDPOINT_STATUS,
    ENDPOINT_UPDATE,
    EXEC_NETDEV,
    EXEC_WLDEV,
)

_LOGGER = logging.getLogger(__name__)

# Regex to parse Tomato's JS-style "var foo = {...};" or "var foo = [...];"
_VAR_RE = re.compile(r"var\s+(\w+)\s*=\s*([\s\S]*?);", re.MULTILINE)


class FreshTomatoApiError(Exception):
    """Raised when the router returns an unexpected response."""


class FreshTomatoAuthError(FreshTomatoApiError):
    """Raised when credentials are rejected (HTTP 401 / 403)."""


class FreshTomatoConnectionError(FreshTomatoApiError):
    """Raised when the router is unreachable."""


class FreshTomatoClient:
    """Async HTTP client for a FreshTomato router."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        http_id: str,
        verify_ssl: bool = DEFAULT_VERIFY_SSL,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._http_id = http_id
        self._verify_ssl = verify_ssl
        self._session = session
        self._owns_session = session is None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_init(self) -> None:
        """Create an aiohttp session if we don't own one."""
        if self._owns_session:
            connector = aiohttp.TCPConnector(ssl=self._verify_ssl)
            self._session = aiohttp.ClientSession(connector=connector)

    async def async_close(self) -> None:
        """Close the owned session."""
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def _base_url(self) -> str:
        scheme = "https" if self._port == 443 else "http"
        if (scheme == "http" and self._port == 80) or (
            scheme == "https" and self._port == 443
        ):
            return f"{scheme}://{self._host}"
        return f"{scheme}://{self._host}:{self._port}"

    @property
    def _auth(self) -> aiohttp.BasicAuth:
        return aiohttp.BasicAuth(self._username, self._password)

    # ------------------------------------------------------------------
    # Low-level fetch
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, str] | None = None) -> str:
        """Perform a GET request and return the raw text body."""
        if self._session is None:
            raise FreshTomatoApiError("Client not initialised; call async_init() first")
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(
                url,
                params=params,
                auth=self._auth,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (401, 403):
                    raise FreshTomatoAuthError(
                        f"Authentication failed (HTTP {resp.status})"
                    )
                if resp.status != 200:
                    raise FreshTomatoApiError(
                        f"Unexpected HTTP status {resp.status} from {url}"
                    )
                return await resp.text()
        except aiohttp.ClientConnectorError as exc:
            raise FreshTomatoConnectionError(
                f"Cannot connect to router at {self._base_url}: {exc}"
            ) from exc
        except asyncio.TimeoutError as exc:
            raise FreshTomatoConnectionError(
                f"Timeout connecting to router at {self._base_url}"
            ) from exc

    # ------------------------------------------------------------------
    # Data parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_netdev(raw: str) -> dict[str, dict[str, int]]:
        """Parse netdev response into {iface: {rx: N, tx: N, rxp: N, txp: N}}.

        The router returns something like:
            netdev = { 'eth0':{ rx:123456, tx:654321, ... }, ... }
        We sanitise with regex to make it valid JSON.
        """
        # Extract the value of `netdev = ...`
        match = re.search(r"netdev\s*=\s*(\{[\s\S]*?\});", raw)
        if not match:
            _LOGGER.debug("netdev raw response: %s", raw[:200])
            raise FreshTomatoApiError("Could not parse netdev response")

        raw_obj = match.group(1)

        # Convert JS-style unquoted keys → quoted keys for json.loads
        # e.g.  { 'eth0':{ rx:123 } }  →  { "eth0":{ "rx":123 } }
        cleaned = re.sub(r"'([^']+)'", r'"\1"', raw_obj)
        cleaned = re.sub(r"(\b\w+\b)\s*:", r'"\1":', cleaned)
        # Fix double-quoted keys produced by the two passes above
        cleaned = re.sub(r'"(".*?")"', r"\1", cleaned)

        import json  # local import to avoid circular at module level

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            _LOGGER.debug("Cleaned netdev: %s", cleaned[:400])
            # Fallback: manual regex extraction
            return _parse_netdev_fallback(raw_obj)

    @staticmethod
    def _parse_wldev(raw: str) -> list[dict[str, Any]]:
        """Parse wldev response into a list of wireless client dicts.

        Response looks like:
            wldev = [{ mac:'AA:BB:CC:DD:EE:FF', rssi:-65, ... }, ...]
        """
        match = re.search(r"wldev\s*=\s*(\[[\s\S]*?\]);", raw)
        if not match:
            return []

        raw_arr = match.group(1)
        cleaned = re.sub(r"'([^']+)'", r'"\1"', raw_arr)
        cleaned = re.sub(r"(\b\w+\b)\s*:", r'"\1":', cleaned)
        cleaned = re.sub(r'"(".*?")"', r"\1", cleaned)

        import json

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            _LOGGER.debug("Could not parse wldev: %s", cleaned[:400])
            return []

    @staticmethod
    def _parse_status(raw: str) -> dict[str, Any]:
        """Parse status-data.jsx into a flat dict of router state values.

        The page sets JS vars; we capture them all.
        """
        result: dict[str, Any] = {}
        for m in _VAR_RE.finditer(raw):
            key = m.group(1)
            value_str = m.group(2).strip().strip("'\"")
            # Try numeric conversion
            try:
                if "." in value_str:
                    result[key] = float(value_str)
                else:
                    result[key] = int(value_str)
            except ValueError:
                result[key] = value_str
        return result

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def async_get_netdev(self) -> dict[str, dict[str, int]]:
        """Fetch per-interface bandwidth counters."""
        raw = await self._get(
            ENDPOINT_UPDATE,
            params={"exec": EXEC_NETDEV, "_http_id": self._http_id},
        )
        return self._parse_netdev(raw)

    async def async_get_wldev(self) -> list[dict[str, Any]]:
        """Fetch list of connected wireless clients."""
        raw = await self._get(
            ENDPOINT_UPDATE,
            params={"exec": EXEC_WLDEV, "_http_id": self._http_id},
        )
        return self._parse_wldev(raw)

    async def async_get_status(self) -> dict[str, Any]:
        """Fetch general router status (uptime, WAN IP, memory, etc.)."""
        raw = await self._get(ENDPOINT_STATUS)
        return self._parse_status(raw)

    async def async_fetch_all(self) -> dict[str, Any]:
        """Fetch netdev, wldev, and status in parallel."""
        netdev, wldev, status = await asyncio.gather(
            self.async_get_netdev(),
            self.async_get_wldev(),
            self.async_get_status(),
            return_exceptions=True,
        )

        result: dict[str, Any] = {}

        if isinstance(netdev, Exception):
            _LOGGER.warning("netdev fetch failed: %s", netdev)
            result["netdev"] = {}
        else:
            result["netdev"] = netdev

        if isinstance(wldev, Exception):
            _LOGGER.warning("wldev fetch failed: %s", wldev)
            result["wldev"] = []
        else:
            result["wldev"] = wldev

        if isinstance(status, Exception):
            _LOGGER.warning("status fetch failed: %s", status)
            result["status"] = {}
        else:
            result["status"] = status

        return result

    async def async_test_connection(self) -> bool:
        """Return True if we can authenticate and reach update.cgi."""
        try:
            await self.async_get_netdev()
            return True
        except FreshTomatoAuthError:
            raise
        except FreshTomatoApiError:
            return False


# ---------------------------------------------------------------------------
# Fallback parser (used when JSON clean-up fails)
# ---------------------------------------------------------------------------

def _parse_netdev_fallback(raw_obj: str) -> dict[str, dict[str, int]]:
    """Extract interface RX/TX pairs with plain regex as a last resort."""
    result: dict[str, dict[str, int]] = {}
    iface_re = re.compile(r"['\"]?([\w.]+)['\"]?\s*:\s*\{([^}]+)\}", re.DOTALL)
    field_re = re.compile(r"(\w+)\s*:\s*(-?\d+)")
    for iface_m in iface_re.finditer(raw_obj):
        iface = iface_m.group(1)
        fields = {k: int(v) for k, v in field_re.findall(iface_m.group(2))}
        if fields:
            result[iface] = fields
    return result

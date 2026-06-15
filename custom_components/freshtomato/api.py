"""FreshTomato router API client."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Tomato's update.cgi returns JavaScript variable assignments like:
#   devlist = [...];
#   netdev = {...};
#   sysinfo = {...};
_JS_VAR_RE = re.compile(r"^(\w+)\s*=\s*(.*?);?\s*$", re.MULTILINE | re.DOTALL)


@dataclass
class RouterStats:
    """All data fetched from the router in a single poll cycle."""

    # Connected devices – list of dicts with mac, ip, name, iface
    devices: list[dict[str, str]] = field(default_factory=list)

    # Bandwidth in bytes (cumulative counters from the router)
    net_rx: dict[str, int] = field(default_factory=dict)
    net_tx: dict[str, int] = field(default_factory=dict)

    # System info
    uptime: int = 0          # seconds
    load_1: float = 0.0
    load_5: float = 0.0
    load_15: float = 0.0
    mem_total: int = 0       # kB
    mem_free: int = 0        # kB


class FreshTomatoApiError(Exception):
    """Raised when the API returns an unexpected response."""


class FreshTomatoAuthError(FreshTomatoApiError):
    """Raised when authentication fails."""


class FreshTomatoApi:
    """Async client for the FreshTomato (Tomato firmware) HTTP API."""

    def __init__(
        self,
        host: str,
        http_id: str,
        username: str,
        password: str,
        port: int = 80,
        ssl: bool = False,
        verify_ssl: bool = True,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._host = host
        self._http_id = http_id
        self._username = username
        self._password = password
        self._port = port
        self._ssl = ssl
        self._verify_ssl = verify_ssl
        self._session = session
        self._own_session = session is None

    @property
    def _base_url(self) -> str:
        scheme = "https" if self._ssl else "http"
        return f"{scheme}://{self._host}:{self._port}"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self._verify_ssl if self._ssl else False)
            self._session = aiohttp.ClientSession(connector=connector)
            self._own_session = True
        return self._session

    async def close(self) -> None:
        """Close the underlying aiohttp session if we own it."""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    async def _post(self, exec_target: str) -> str:
        """POST to update.cgi and return the raw response text."""
        session = await self._get_session()
        url = f"{self._base_url}/update.cgi"
        data = {"_http_id": self._http_id, "exec": exec_target}
        auth = aiohttp.BasicAuth(self._username, self._password)

        try:
            async with session.post(
                url,
                data=data,
                auth=auth,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise FreshTomatoAuthError(
                        f"Authentication failed (HTTP 401) for {self._host}"
                    )
                if resp.status != 200:
                    raise FreshTomatoApiError(
                        f"Unexpected HTTP {resp.status} from {self._host}"
                    )
                return await resp.text()
        except aiohttp.ClientConnectorError as err:
            raise FreshTomatoApiError(f"Cannot connect to {self._host}: {err}") from err
        except aiohttp.ServerTimeoutError as err:
            raise FreshTomatoApiError(f"Timeout connecting to {self._host}") from err

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_js_response(text: str) -> dict[str, Any]:
        """
        Tomato's update.cgi returns bare JavaScript variable assignments, e.g.:

            devlist = [['00:11:22:33:44:55','192.168.1.10','MyPC','br0',0],...];
            netdev = {
              'vlan2': {'rx': {'bytes': 12345, ...}, 'tx': {'bytes': 67890, ...}},
              ...
            };

        We eval-free parse by extracting each top-level var and then use
        Python's ast.literal_eval after light sanitisation.
        """
        import ast

        result: dict[str, Any] = {}
        for match in _JS_VAR_RE.finditer(text):
            name, value = match.group(1).strip(), match.group(2).strip()
            # Convert JS single-quotes to double-quotes for ast
            py_value = value.replace("'", '"')
            try:
                result[name] = ast.literal_eval(py_value)
            except (ValueError, SyntaxError):
                _LOGGER.debug("Could not parse JS var %s; skipping", name)
        return result

    @staticmethod
    def _parse_devlist(raw: list) -> list[dict[str, str]]:
        """
        devlist entries: [mac, ip, name, iface, ...]
        """
        devices = []
        for entry in raw:
            if not isinstance(entry, (list, tuple)) or len(entry) < 4:
                continue
            devices.append(
                {
                    "mac": str(entry[0]),
                    "ip": str(entry[1]),
                    "name": str(entry[2]) if entry[2] else str(entry[1]),
                    "interface": str(entry[3]),
                }
            )
        return devices

    @staticmethod
    def _parse_netdev(raw: dict) -> tuple[dict[str, int], dict[str, int]]:
        """
        netdev format:
          { 'iface': {'rx': {'bytes': N, ...}, 'tx': {'bytes': N, ...}}, ... }
        Returns (rx_map, tx_map) keyed by interface name.
        """
        rx: dict[str, int] = {}
        tx: dict[str, int] = {}
        for iface, counters in raw.items():
            if isinstance(counters, dict):
                rx[iface] = int(counters.get("rx", {}).get("bytes", 0))
                tx[iface] = int(counters.get("tx", {}).get("bytes", 0))
        return rx, tx

    @staticmethod
    def _parse_sysinfo(raw: dict) -> tuple[int, float, float, float, int, int]:
        """
        sysinfo format:
          { 'uptime': N, 'load': [1m_int, 5m_int, 15m_int],
            'memory': {'total': N, 'free': N, ...} }
        Load averages are stored as integers × 65536.
        Returns (uptime_s, load1, load5, load15, mem_total_kb, mem_free_kb).
        """
        uptime = int(raw.get("uptime", 0))
        load_raw = raw.get("load", [0, 0, 0])
        load_1 = round(load_raw[0] / 65536.0, 2) if len(load_raw) > 0 else 0.0
        load_5 = round(load_raw[1] / 65536.0, 2) if len(load_raw) > 1 else 0.0
        load_15 = round(load_raw[2] / 65536.0, 2) if len(load_raw) > 2 else 0.0
        mem = raw.get("memory", {})
        mem_total = int(mem.get("total", 0))
        mem_free = int(mem.get("free", 0))
        return uptime, load_1, load_5, load_15, mem_total, mem_free

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def async_get_stats(self) -> RouterStats:
        """Fetch all router statistics in one coordinated call."""
        stats = RouterStats()

        # Fetch devlist
        try:
            text = await self._post(EXEC_DEVLIST)
            parsed = self._parse_js_response(text)
            raw_devlist = parsed.get("devlist", [])
            stats.devices = self._parse_devlist(raw_devlist)
        except FreshTomatoApiError:
            raise
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Failed to parse devlist: %s", err)

        # Fetch netdev
        try:
            text = await self._post(EXEC_NETDEV)
            parsed = self._parse_js_response(text)
            raw_netdev = parsed.get("netdev", {})
            stats.net_rx, stats.net_tx = self._parse_netdev(raw_netdev)
        except FreshTomatoApiError:
            raise
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Failed to parse netdev: %s", err)

        # Fetch sysinfo
        try:
            text = await self._post(EXEC_SYSINFO)
            parsed = self._parse_js_response(text)
            raw_sysinfo = parsed.get("sysinfo", {})
            (
                stats.uptime,
                stats.load_1,
                stats.load_5,
                stats.load_15,
                stats.mem_total,
                stats.mem_free,
            ) = self._parse_sysinfo(raw_sysinfo)
        except FreshTomatoApiError:
            raise
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Failed to parse sysinfo: %s", err)

        return stats

    async def async_test_connection(self) -> bool:
        """
        Test credentials by fetching sysinfo.
        Raises FreshTomatoAuthError if credentials are wrong.
        Raises FreshTomatoApiError for other connection problems.
        Returns True on success.
        """
        await self._post(EXEC_SYSINFO)
        return True


# Convenience import alias used in other modules
EXEC_DEVLIST = "devlist"
EXEC_NETDEV = "netdev"
EXEC_SYSINFO = "sysinfo"

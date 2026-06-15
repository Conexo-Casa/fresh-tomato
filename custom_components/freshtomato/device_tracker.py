"""Device tracker platform for FreshTomato.

Creates a tracked device entity for every wireless client reported by
the router's wldev endpoint.  Wired-only clients are not visible through
the Tomato HTTP API (same limitation as the built-in Tomato integration).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import (
    ScannerEntity,
    SourceType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import FreshTomatoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FreshTomato device tracker."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: FreshTomatoCoordinator = data["coordinator"]
    host = entry.data[CONF_HOST]

    tracked: set[str] = set()

    @callback
    def _async_update_from_coordinator() -> None:
        """Add new wireless clients as they appear."""
        new_entities = []
        clients: list[dict[str, Any]] = (coordinator.data or {}).get("wldev", [])
        for client in clients:
            mac = (client.get("mac") or "").upper()
            if not mac or mac in tracked:
                continue
            tracked.add(mac)
            new_entities.append(
                FreshTomatoDeviceTracker(coordinator, entry, host, mac, client)
            )
        if new_entities:
            async_add_entities(new_entities)

    coordinator.async_add_listener(_async_update_from_coordinator)
    _async_update_from_coordinator()


class FreshTomatoDeviceTracker(
    CoordinatorEntity[FreshTomatoCoordinator], ScannerEntity
):
    """Represents a wireless client seen by the router."""

    _attr_source_type = SourceType.ROUTER
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FreshTomatoCoordinator,
        entry: ConfigEntry,
        host: str,
        mac: str,
        initial_data: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{entry.entry_id}_tracker_{mac.lower().replace(':', '')}"
        self._attr_name = initial_data.get("hostname") or mac
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FreshTomato Router ({host})",
            manufacturer=MANUFACTURER,
            model="FreshTomato",
            configuration_url=f"http://{host}",
        )

    @property
    def is_connected(self) -> bool:
        """Return True if the MAC is still in the wldev list."""
        clients: list[dict[str, Any]] = (self.coordinator.data or {}).get("wldev", [])
        return any(
            (c.get("mac") or "").upper() == self._mac for c in clients
        )

    @property
    def ip_address(self) -> str | None:
        """Return the client's IP if available."""
        clients: list[dict[str, Any]] = (self.coordinator.data or {}).get("wldev", [])
        for c in clients:
            if (c.get("mac") or "").upper() == self._mac:
                return c.get("ip")
        return None

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def hostname(self) -> str | None:
        clients: list[dict[str, Any]] = (self.coordinator.data or {}).get("wldev", [])
        for c in clients:
            if (c.get("mac") or "").upper() == self._mac:
                return c.get("hostname")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        clients: list[dict[str, Any]] = (self.coordinator.data or {}).get("wldev", [])
        for c in clients:
            if (c.get("mac") or "").upper() == self._mac:
                return {k: v for k, v in c.items() if k not in ("mac",)}
        return {}

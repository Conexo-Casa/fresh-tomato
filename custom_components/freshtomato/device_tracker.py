"""Device tracker platform for FreshTomato router."""
from __future__ import annotations

import logging

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FreshTomatoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker entities for FreshTomato."""
    coordinator: FreshTomatoCoordinator = hass.data[DOMAIN][entry.entry_id]
    host = entry.data[CONF_HOST]

    tracked: set[str] = set()

    @callback
    def _add_new_devices() -> None:
        """Add tracker entities for newly discovered devices."""
        if coordinator.data is None:
            return
        new_entities = []
        for device in coordinator.data.devices:
            mac = device["mac"].lower()
            if mac not in tracked:
                tracked.add(mac)
                new_entities.append(
                    FreshTomatoDeviceTracker(coordinator, device, host, entry.entry_id)
                )
        if new_entities:
            async_add_entities(new_entities)

    # Track when coordinator updates to pick up new devices
    entry.async_on_unload(coordinator.async_add_listener(_add_new_devices))

    # Add devices already present at startup
    _add_new_devices()


class FreshTomatoDeviceTracker(
    CoordinatorEntity[FreshTomatoCoordinator], ScannerEntity
):
    """Track a single device connected to the FreshTomato router."""

    _attr_has_entity_name = True
    _attr_source_type = SourceType.ROUTER

    def __init__(
        self,
        coordinator: FreshTomatoCoordinator,
        device: dict[str, str],
        host: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._mac = device["mac"].lower()
        self._initial_name = device.get("name") or self._mac
        self._host = host
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_tracker_{self._mac.replace(':', '_')}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"FreshTomato ({host})",
            manufacturer="FreshTomato",
            model="Broadcom Router",
            configuration_url=f"http://{host}",
        )

    @property
    def name(self) -> str:
        return self._current_device.get("name") or self._initial_name if self._current_device else self._initial_name

    @property
    def _current_device(self) -> dict[str, str] | None:
        if self.coordinator.data is None:
            return None
        for dev in self.coordinator.data.devices:
            if dev["mac"].lower() == self._mac:
                return dev
        return None

    @property
    def is_connected(self) -> bool:
        return self._current_device is not None

    @property
    def ip_address(self) -> str | None:
        if dev := self._current_device:
            return dev.get("ip")
        return None

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def hostname(self) -> str | None:
        if dev := self._current_device:
            return dev.get("name")
        return None

    @property
    def extra_state_attributes(self) -> dict:
        if dev := self._current_device:
            return {"interface": dev.get("interface", "")}
        return {}

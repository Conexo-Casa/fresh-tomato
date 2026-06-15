"""Sensor platform for FreshTomato integration.

Sensors provided:
  - WAN IP address
  - WAN uptime (seconds)
  - CPU load (1-min average)
  - Free memory (bytes)
  - Total memory (bytes)
  - Firmware version
  - Connected wireless clients (count)
  - Per-interface RX bytes  (vlan1, eth0, br0, …)
  - Per-interface TX bytes
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import FreshTomatoCoordinator

_LOGGER = logging.getLogger(__name__)

# WAN interfaces to track bandwidth for (most common on Tomato routers)
_TRACKED_INTERFACES = ("vlan1", "vlan2", "eth0", "eth1", "br0", "ppp0")


@dataclass(frozen=True, kw_only=True)
class FreshTomatoSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with a value extractor."""

    value_fn: Callable[[dict[str, Any]], Any]


# ---------------------------------------------------------------------------
# Static sensors (from status-data.jsx)
# ---------------------------------------------------------------------------

STATIC_SENSORS: tuple[FreshTomatoSensorDescription, ...] = (
    FreshTomatoSensorDescription(
        key="wan_ip",
        name="WAN IP Address",
        icon="mdi:ip-network",
        value_fn=lambda d: d.get("status", {}).get("wanip") or d.get("status", {}).get("wan_ip"),
    ),
    FreshTomatoSensorDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:clock-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("status", {}).get("uptime"),
    ),
    FreshTomatoSensorDescription(
        key="cpu_load",
        name="CPU Load (1 min)",
        icon="mdi:cpu-64-bit",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _cpu_load(d),
    ),
    FreshTomatoSensorDescription(
        key="mem_free",
        name="Free Memory",
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("status", {}).get("memfree"),
    ),
    FreshTomatoSensorDescription(
        key="mem_total",
        name="Total Memory",
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("status", {}).get("memtotal"),
    ),
    FreshTomatoSensorDescription(
        key="firmware",
        name="Firmware Version",
        icon="mdi:router-wireless",
        value_fn=lambda d: d.get("status", {}).get("version") or d.get("status", {}).get("firmware"),
    ),
    FreshTomatoSensorDescription(
        key="wl_clients",
        name="Wireless Clients",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: len(d.get("wldev", [])),
    ),
)


def _cpu_load(data: dict[str, Any]) -> float | None:
    """Return the 1-minute CPU load average as a percentage (0-100)."""
    status = data.get("status", {})
    # Status page may expose cpu_load as "0.12 0.08 0.05" (1/5/15 min)
    raw = status.get("cpu_load") or status.get("cpuload")
    if raw is None:
        return None
    try:
        one_min = str(raw).split()[0]
        return round(float(one_min) * 100, 1)
    except (IndexError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FreshTomato sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: FreshTomatoCoordinator = data["coordinator"]
    host = entry.data[CONF_HOST]

    entities: list[SensorEntity] = []

    # Static sensors
    for desc in STATIC_SENSORS:
        entities.append(FreshTomatoSensor(coordinator, entry, host, desc))

    # Per-interface bandwidth sensors (RX + TX) — discovered dynamically
    netdev: dict[str, Any] = coordinator.data.get("netdev", {}) if coordinator.data else {}
    for iface in netdev:
        for direction in ("rx", "tx"):
            entities.append(
                FreshTomatoBandwidthSensor(coordinator, entry, host, iface, direction)
            )

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Entity classes
# ---------------------------------------------------------------------------

def _device_info(entry: ConfigEntry, host: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"FreshTomato Router ({host})",
        manufacturer=MANUFACTURER,
        model="FreshTomato",
        configuration_url=f"http://{host}",
    )


class FreshTomatoSensor(CoordinatorEntity[FreshTomatoCoordinator], SensorEntity):
    """A single static sensor."""

    entity_description: FreshTomatoSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FreshTomatoCoordinator,
        entry: ConfigEntry,
        host: str,
        description: FreshTomatoSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry, host)

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class FreshTomatoBandwidthSensor(CoordinatorEntity[FreshTomatoCoordinator], SensorEntity):
    """RX or TX byte counter for a network interface."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:network"

    def __init__(
        self,
        coordinator: FreshTomatoCoordinator,
        entry: ConfigEntry,
        host: str,
        iface: str,
        direction: str,  # "rx" or "tx"
    ) -> None:
        super().__init__(coordinator)
        self._iface = iface
        self._direction = direction
        self._attr_name = f"{iface.upper()} {direction.upper()} Bytes"
        self._attr_unique_id = f"{entry.entry_id}_netdev_{iface}_{direction}"
        self._attr_device_info = _device_info(entry, host)

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        iface_data = self.coordinator.data.get("netdev", {}).get(self._iface, {})
        return iface_data.get(self._direction)
